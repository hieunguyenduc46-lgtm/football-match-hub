"""
Minimal Alertmanager webhook receiver: prints every notification it gets.
In a real team this would be Slack, email or PagerDuty; here `docker logs` shows the notifications.
"""
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        for alert in payload.get("alerts", []):
            labels, notes = alert.get("labels", {}), alert.get("annotations", {})
            print(f"{datetime.now():%Y-%m-%d %H:%M:%S} [{alert.get('status', '?').upper()}] "
                  f"{labels.get('alertname')} severity={labels.get('severity')} "
                  f"env={labels.get('environment')} - {notes.get('summary')}")
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):  # silence the default access log
        pass


print("alert-receiver listening on :5001")
HTTPServer(("0.0.0.0", 5001), Handler).serve_forever()
