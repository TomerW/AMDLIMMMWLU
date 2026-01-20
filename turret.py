import json
import os
import threading
import time
import urllib.request
from flask import Flask, jsonify, request

# --- Configuration ---
UPDATE_DT = 1  # 1Hz update frequency
HOST_IP = os.getenv("HOST_IP", "0.0.0.0")  # Bind to all interfaces by default
PORT = 5000  # Listening port for API access
# Where to push azimuth updates; defaults to port 4000
PUSH_STATUS_URL = "http://172.20.10.2:4000/turret/azimuth-status"
turret = None
lock = threading.Lock()
shutdown_event = threading.Event()
app = Flask(__name__)

class TurretController:
    def __init__(self, initial_azimuth=0.0, rotation_speed=10.0):
        self.current_azimuth = initial_azimuth % 360
        self.target_azimuth = initial_azimuth % 360
        self.rotation_speed = abs(rotation_speed)
        self.at_target = True

    def set_target(self, target_angle):
        """Update the target azimuth directly (Thread Safe via caller)."""
        self.target_azimuth = float(target_angle) % 360

    def set_speed(self, speed):
        """Update the internal rotation speed."""
        self.rotation_speed = abs(float(speed))

    def update_position(self, dt):
        """Calculates movement for the elapsed time 'dt'."""
        if self.current_azimuth == self.target_azimuth:
            self.at_target = True
            return

        # Calculate shortest path (-180 to 180 degrees)
        diff = (self.target_azimuth - self.current_azimuth + 180) % 360 - 180
        step_distance = self.rotation_speed * dt

        if abs(diff) <= step_distance:
            self.current_azimuth = self.target_azimuth
            self.at_target = True
        else:
            direction = 1 if diff > 0 else -1
            self.current_azimuth = (self.current_azimuth + direction * step_distance) % 360
            self.at_target = False

    def get_status(self):
        """Returns current state as a dictionary."""
        return {
            "current_azimuth": round(self.current_azimuth, 2),
            "target_azimuth": round(self.target_azimuth, 2),
            "at_target": self.at_target,
            "speed": self.rotation_speed
        }

def _run_movement_loop():
    """Independent thread handling the physics/movement."""
    last_pushed_azimuth = None
    while not shutdown_event.is_set():
        with lock:
            if turret:
                turret.update_position(UPDATE_DT)
                current_az = int(round(turret.current_azimuth)) % 360
        
        time.sleep(UPDATE_DT)

        # Push updates if azimuth changed
        if PUSH_STATUS_URL and current_az != last_pushed_azimuth:
            try:
                print(f"Pushing {current_az}° to {PUSH_STATUS_URL}")
                payload = json.dumps({"current_azimuth": current_az}).encode("utf-8")
                req = urllib.request.Request(PUSH_STATUS_URL, data=payload, 
                                            headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=1)
                last_pushed_azimuth = current_az
            except Exception as exc:
                print(f"Push failed: {exc}")
        

# --- API Routes ---

def _require_turret_ready():
    if turret is None:
        return jsonify({"error": "Turret not initialized"}), 503
    return None

@app.route("/turret/azimuth-status", methods=["GET", "POST"])
def http_get_status():
    """Expose current azimuth (legacy + MMC schema)."""
    not_ready = _require_turret_ready()
    if not_ready:
        return not_ready

    with lock:
        # MMC schema expects only current_azimuth (int 0-359)
        current = int(round(turret.current_azimuth)) % 360
        return jsonify({"current_azimuth": current})

def _set_target_from_payload(payload: dict):
    """Validate and apply azimuth command per MMC schema."""
    not_ready = _require_turret_ready()
    if not_ready:
        return not_ready

    key = "azimuth_command" if "azimuth_command" in payload else "target_azimuth"
    if key not in payload:
        return jsonify({"error": "Missing azimuth_command/target_azimuth"}), 400

    try:
        raw_val = float(payload[key])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid azimuth value"}), 400

    # MMC schema: integer 0-359. Allow numeric strings but enforce integer range.
    if not raw_val.is_integer():
        return jsonify({"error": "Azimuth must be integer"}), 400
    azimuth_int = int(raw_val) % 360

    # Log the incoming command for visibility
    print(f"Received azimuth command: {payload}")

    with lock:
        turret.set_target(azimuth_int)

    # MMC Ack schema
    return jsonify({"status": "OK"})

@app.route("/turret/azimuth-command", methods=["GET", "POST"])
def http_set_target():
    payload = request.get_json(silent=True) or {}
    return _set_target_from_payload(payload)

if __name__ == "__main__":
    # Initialize the global turret instance
    turret = TurretController(initial_azimuth=0.0, rotation_speed=25.0)

    # Start the background physics thread
    move_thread = threading.Thread(target=_run_movement_loop, daemon=True)
    move_thread.start()

    print("Turret Server Online.")
    print(f"MMC Cmd:   http://{HOST_IP}:{PORT}/turret/azimuth-command (POST)")
    print(f"MMC Stat:  http://{HOST_IP}:{PORT}/turret/azimuth-status (GET)")
    print(f"Auto-Push: {PUSH_STATUS_URL} (POST on change)")

    try:
        # threaded=True allows Flask to handle multiple API requests simultaneously
        app.run(host=HOST_IP, port=PORT, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        shutdown_event.set()
        move_thread.join(timeout=1)