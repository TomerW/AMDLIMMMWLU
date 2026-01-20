import http.server
import socketserver
import time
import json
import os

PORT = 8000
OUT_DIR = "received_json"
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

    def log_message(self, format, *args):
        # suppress default HTTP request logging to keep console clean
        return

if __name__ == "__main__":
    print(f"Starting test server at http://localhost:{PORT}/upload")
    try:
        with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("Server stopped by KeyboardInterrupt.")
    except Exception as e:
        print(f"Server failed to start: {e}")