"""
Prometheus metrics (used by the Monitoring stage).

GET /metrics returns, in Prometheus text format:
  - http_requests_total{method, route, status}       requests handled by the API
  - http_request_duration_seconds{method, route}     latency histogram (for p95 latency)
  - upstream_api_requests_total{outcome}             calls to API-Football: ok / error
  - cache_lookups_total{result}                      response cache: hit / miss

The route TEMPLATE (e.g. /api/teams/{team_id}) is used as the label instead of the raw URL,
so the number of time series stays small no matter how many ids are requested.
"""
import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response

REQUESTS = Counter(
    "http_requests_total", "HTTP requests handled by the backend", ["method", "route", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["method", "route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
UPSTREAM = Counter("upstream_api_requests_total", "Requests sent to API-Football", ["outcome"])
CACHE = Counter("cache_lookups_total", "Response cache lookups", ["result"])


async def metrics_middleware(request: Request, call_next):
    """Time every request and count it by route template and status code."""
    start = time.perf_counter()
    status = 500  # if the handler raises, the request is counted as a server error
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = getattr(request.scope.get("route"), "path", "unmatched")
        if route != "/metrics":  # do not count Prometheus' own scrapes
            REQUESTS.labels(request.method, route, str(status)).inc()
            LATENCY.labels(request.method, route).observe(time.perf_counter() - start)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
