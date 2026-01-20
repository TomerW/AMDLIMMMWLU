import http.server
import socketserver
import time
import json
import os

PORT = 8000
# store received files inside the RandomTarget package folder for easier testing
BASE_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE_DIR, "received_json")
os.makedirs(OUT_DIR, exist_ok=True)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length > 0 else b""
        ts = int(time.time() * 1000)
        fname = os.path.join(OUT_DIR, f"recv_{ts}.json")
        try:
            parsed = json.loads(body.decode('utf-8'))
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            print(f"Saved POST to {fname} (len={len(body)})")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            rawname = fname + ".raw"
            with open(rawname, "wb") as f:
                f.write(body)
            print(f"Failed to parse JSON, saved raw to {rawname}: {e}")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"BAD REQUEST")

    def do_GET(self):
        """Provide a tiny status page so opening the endpoint in a browser works."""
        try:
            # show recent received files and, if path is '/upload', include the live targets snapshot
            files = []
            if os.path.exists(OUT_DIR):
                files = sorted(os.listdir(OUT_DIR))[-50:]

            body = ["<html><head><title>Test Server</title></head><body>"]
            body.append(f"<h2>Test server running on port {PORT}</h2>")
            body.append(f"<p>Saved files in: {OUT_DIR}</p>")

            # If the request is to /upload, attempt to read the current JSON snapshot from likely locations
            if self.path.startswith("/upload"):
                cur_json = None
                # candidate locations (relative to package and parent folder)
                candidates = []
                # repo-root Random_test/live_targets.json (one level up)
                parent = os.path.dirname(BASE_DIR)
                candidates.append(os.path.join(parent, "Random_test", "live_targets.json"))
                # repo-root live_targets.json
                candidates.append(os.path.join(parent, "live_targets.json"))
                # working directory live_targets.json
                candidates.append(os.path.join(os.getcwd(), "live_targets.json"))

                for c in candidates:
                    try:
                        if c and os.path.exists(c):
                            with open(c, "r", encoding="utf-8") as f:
                                cur_json = f.read()
                            cand_used = c
                            break
                    except Exception:
                        continue

                if cur_json is not None:
                    body.append("<h3>Live targets (from snapshot)</h3>")
                    # try pretty print JSON
                    try:
                        parsed = json.loads(cur_json)
                        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                        body.append("<pre style='white-space:pre-wrap; background:#f6f6f6; padding:8px;'>")
                        body.append(pretty)
                        body.append("</pre>")
                        body.append(f"<p>Source: {cand_used}</p>")
                    except Exception:
                        body.append("<p>Unable to parse JSON snapshot, raw content below:</p>")
                        body.append("<pre>")
                        body.append(cur_json)
                        body.append("</pre>")
                else:
                    body.append("<p>No live snapshot found in expected locations.</p>")

            body.append("<h3>Recent received files</h3>")
            body.append("<ul>")
            for fn in files:
                body.append(f"<li>{fn}</li>")
            body.append("</ul>")
            body.append("</body></html>")
            html = "\n".join(body).encode("utf-8")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"ERROR")

    def do_HEAD(self):
        # respond to HEAD like GET but without body
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
        except Exception:
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        # suppress default HTTP request logging to keep console clean
        return

if __name__ == "__main__":
    print(f"Starting test server at http://localhost:{PORT}/upload")
    print(f"Saving received files to: {OUT_DIR}")
    try:
        with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("Server stopped by KeyboardInterrupt.")
    except Exception as e:
        print(f"Server failed to start: {e}")
