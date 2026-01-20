import os
import sys
import socket
import subprocess
import tkinter as tk
from urllib.parse import urlparse

from RandomTarget.ui import TargetGeneratorUI
from RandomTarget import config

def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def maybe_start_local_server():
    """
    If the configured ENDPOINT is a localhost URL and nothing listens on its port,
    start server_local.py as a subprocess and return the Popen object.
    Otherwise return None.
    """
    url = config.ENDPOINT_URL or ""
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (80 if parsed.scheme == "http" else 443)
    if host not in ("localhost", "127.0.0.1"):
        return None

    if is_port_open(host, port):
        print(f"Local endpoint {host}:{port} already listening, not starting server_local.py")
        return None

    server_path = os.path.join(os.path.dirname(__file__), "server_local.py")
    if not os.path.exists(server_path):
        print(f"server_local.py not found at {server_path}, cannot auto-start local server")
        return None

    # Start server_local.py as a child process. Keep handle so we can terminate on exit.
    try:
        # On Windows, creationflags could be used to hide console, but keep default for simplicity.
        proc = subprocess.Popen([sys.executable, server_path],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Started local test server (pid={proc.pid}) for endpoint {host}:{port}")
        return proc
    except Exception as e:
        print(f"Failed to start local server: {e}")
        return None

if __name__ == "__main__":
    # If endpoint is local and not listening, start test server automatically
    server_proc = maybe_start_local_server()

    root = tk.Tk()
    app = TargetGeneratorUI(root)

    # attach server process so UI can terminate it on close
    app.server_process = server_proc

    def on_closing_wrapper():
        # first run UI cleanup
        app.on_closing()
        # then terminate auto-started server if exists
        proc = getattr(app, "server_process", None)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
                print(f"Stopped local test server (pid={proc.pid})")
            except Exception:
                pass

    root.protocol("WM_DELETE_WINDOW", on_closing_wrapper)
    root.mainloop()
