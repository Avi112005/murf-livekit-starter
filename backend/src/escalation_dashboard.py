"""Local read-only API for the Day 7 human-help dashboard."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agent import _open_memory_db


class EscalationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/escalations":
            self.send_error(404)
            return

        with _open_memory_db() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS escalations (
                    reference_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    situation TEXT NOT NULL,
                    checked TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    language TEXT NOT NULL,
                    follow_up TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL
                )
                """
            )
            rows = connection.execute(
                """
                SELECT reference_id, name, situation, checked, urgency,
                       language, follow_up, status, created_at
                FROM escalations
                ORDER BY created_at DESC
                """
            ).fetchall()

        payload = json.dumps({"escalations": [dict(row) for row in rows]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), EscalationHandler)
    print("Escalation dashboard API: http://127.0.0.1:8765/escalations")
    server.serve_forever()
