import json
import threading
import time
from flask import Flask, request, jsonify

# --- Configuration ---
UPDATE_DT = 0.1  # 10Hz update frequency
HOST_IP = "172.20.10.2"  # Bind to this LAN interface
PORT = 5000  # Listening port for API access
turret = None
lock = threading.Lock()
shutdown_event = threading.Event()
app = Flask(__name__)

class TurretController:
    def __init__(self, initial_azimuth=0.0, rotation_speed=30.0):
        self.current_azimuth = initial_azimuth % 360
        self.target_azimuth = initial_azimuth % 360
        self.rotation_speed = abs(rotation_speed)
        self.at_target = True

    def set_target(self, target_angle):
        """Update the target azimuth directly (Thread Safe via caller)."""
        self.target_azimuth = float(target_angle) % 360
        self.at_target = (self.current_azimuth == self.target_azimuth)

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

# --- Background Worker ---

def _run_movement_loop():
    """Independent thread handling the physics/movement."""
    while not shutdown_event.is_set():
        with lock:
            if turret:
                turret.update_position(UPDATE_DT)
        time.sleep(UPDATE_DT)

# --- API Routes ---

@app.route("/azimuth_status", methods=["GET"])
def http_get_status():
    with lock:
        return jsonify(turret.get_status())

@app.route("/azimuth_command", methods=["POST"])
def http_set_target():
    data = request.get_json(silent=True) or {}
    
    if "target_azimuth" not in data:
        return jsonify({"error": "Missing target_azimuth"}), 400
    
    try:
        new_target = float(data["target_azimuth"])
        with lock:
            turret.set_target(new_target)
            # Optional: Allow speed update in same request
            if "speed" in data:
                turret.set_speed(data["speed"])
                
            return jsonify(turret.get_status())
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical values"}), 400

# --- Main Entry Point ---

if __name__ == "__main__":
    # Initialize the global turret instance
    turret = TurretController(initial_azimuth=0.0, rotation_speed=25.0)

    # Start the background physics thread
    move_thread = threading.Thread(target=_run_movement_loop, daemon=True)
    move_thread.start()

    print(f"Turret Server Online.")
    print(f"Targeting: http://{HOST_IP}:{PORT}/azimuth_command (POST)")
    print(f"Status:    http://{HOST_IP}:{PORT}/azimuth_status (GET)")

    try:
        # threaded=True allows Flask to handle multiple API requests simultaneously
        app.run(host=HOST_IP, port=PORT, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        shutdown_event.set()
        move_thread.join(timeout=1)