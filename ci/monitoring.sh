#!/bin/bash
# Monitoring stage: start/refresh the monitoring stack, then PROVE production is being monitored:
#   - Prometheus, Alertmanager and Grafana are up
#   - the production backend target is being scraped (up == 1)
#   - the alert rules are loaded
COMPOSE="docker compose -p fmh-monitoring -f monitoring/docker-compose.yml"
PROM="http://localhost:9090"

wait_for() {
    for _ in $(seq 1 30); do
        curl -fs --max-time 3 "$1" > /dev/null && return 0
        sleep 2
    done
    echo "FAIL: $1 is not ready"
    exit 1
}

$COMPOSE up -d --remove-orphans || exit 1
wait_for "$PROM/-/ready"
wait_for "http://localhost:9093/-/ready"
wait_for "http://localhost:3000/api/health"

# Containers may already be running from an earlier build: reload so config changes apply.
curl -fsS -X POST "$PROM/-/reload" && curl -fsS -X POST "http://localhost:9093/-/reload" || exit 1

query() {  # print the value of a single-series PromQL query, or "none"
    curl -fsSG "$PROM/api/v1/query" --data-urlencode "query=$1" | python3 -c \
        'import sys, json; r = json.load(sys.stdin)["data"]["result"]; print(r[0]["value"][1] if r else "none")'
}

echo "Waiting for Prometheus to scrape the production backend..."
STATE="none"
for _ in $(seq 1 20); do
    STATE=$(query 'up{job="fmh-backend",environment="production"}')
    [ "$STATE" = "1" ] && break
    sleep 5
done
if [ "$STATE" != "1" ]; then
    echo "FAIL: Prometheus cannot scrape the production backend (up=$STATE)"
    exit 1
fi

echo "---------------- Scrape targets ----------------"
curl -fsS "$PROM/api/v1/targets" | python3 -c "
import sys, json
for t in json.load(sys.stdin)['data']['activeTargets']:
    env = t['labels'].get('environment', t['labels']['job'])
    print('  %-12s %-45s %s' % (env, t['scrapeUrl'], t['health']))"

echo "---------------- Alert rules -------------------"
RULES=$(curl -fsS "$PROM/api/v1/rules" | python3 -c "
import sys, json
rules = [r for g in json.load(sys.stdin)['data']['groups'] for r in g['rules']]
for r in rules:
    sys.stderr.write('  %-18s state=%s\\n' % (r['name'], r.get('state', '-')))
print(len(rules))")
if [ "${RULES:-0}" -lt 4 ]; then
    echo "FAIL: expected 4 alert rules, found ${RULES:-0}"
    exit 1
fi

echo "---------------- Production right now ----------"
echo "  requests served : $(query 'sum(http_requests_total{environment="production"})')"
echo "  firing alerts   : $(query 'count(ALERTS{alertstate="firing"}) or vector(0)')"
echo ""
echo "MONITORING OK"
echo "  Grafana dashboard : http://localhost:3000"
echo "  Prometheus        : http://localhost:9090/alerts"
echo "  Alertmanager      : http://localhost:9093"
echo "  Alert notifications: docker logs -f fmh-monitoring-alert-receiver-1"
