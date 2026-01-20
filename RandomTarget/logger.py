import json
import os
import time
from . import config

# try to use requests if installed, otherwise fallback to urllib
try:
    import requests  # type: ignore
    HAS_REQUESTS = True
except Exception:
    import urllib.request as _urllib_request  # type: ignore
    import urllib.error as _urllib_error  # type: ignore
    HAS_REQUESTS = False

def json_logger_task():
    """Collect snapshots of all targets and write JSON periodically (no TMP files)."""
    print("JSON Logger thread started.")
    while not config.stop_threads_event.is_set():
        current_data_snapshot = []

        with config.targets_lock:
            for target in config.active_targets:
                current_data_snapshot.append({
                    "id": target.target_id,
                    "timestamp": time.time(),
                    "position": {"north": target.north, "east": target.east, "down": target.down},
                    "velocity": {"vn": target.vn, "ve": target.ve, "vd": target.vd}
                })

        # write directly (no temp file). flush+fsync to reduce partial-write window.
        try:
            with open(config.JSON_FILENAME, "w", encoding="utf-8") as f:
                json.dump(current_data_snapshot, f, indent=2, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception as e:
            print(f"Error writing JSON: {e}")

        # optionally POST the JSON to the configured endpoint (REST API)
        if config.SEND_TO_ENDPOINT and config.ENDPOINT_URL:
            try:
                headers = {"Content-Type": "application/json"}
                if config.ENDPOINT_API_KEY:
                    headers["Authorization"] = f"Bearer {config.ENDPOINT_API_KEY}"

                if HAS_REQUESTS:
                    resp = requests.post(config.ENDPOINT_URL, json=current_data_snapshot, headers=headers, timeout=5.0)
                    if resp.status_code >= 400:
                        print(f"Endpoint POST failed: {resp.status_code} {resp.text}")
                else:
                    data_bytes = json.dumps(current_data_snapshot).encode("utf-8")
                    req = _urllib_request.Request(config.ENDPOINT_URL, data=data_bytes, headers=headers, method="POST")
                    with _urllib_request.urlopen(req, timeout=5.0) as resp:
                        _ = resp.read()
            except Exception as e:
                print(f"Error POSTing to endpoint: {e}")

        # sleep using the (mutable) config value
        sleep_time = max(0.01, config.JSON_WRITE_RATE)
        time.sleep(sleep_time)
    print("JSON Logger thread stopped.")