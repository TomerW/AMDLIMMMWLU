import json
import threading
import time
from flask import Flask, request, jsonify


UPDATE_DT = 0.1  # seconds between updates
turret = None
lock = threading.Lock()
shutdown_event = threading.Event()
app = Flask(__name__)

class TurretController:
    def __init__(self, initial_azimuth=0.0, rotation_speed=30.0):
        """
        :param initial_azimuth: Starting angle (0-360).
        :param rotation_speed: Fixed internal speed in degrees/second.
        """
        self.current_azimuth = initial_azimuth % 360
        self.target_azimuth = initial_azimuth % 360
        self.rotation_speed = rotation_speed
        self.at_target = False

    def set_internal_speed(self, new_speed):
        """Allows updating the internal speed property."""
        self.rotation_speed = abs(new_speed)

    def process_input(self, json_input):
        """
        Parses incoming JSON command.
        Expected format: {"target_azimuth": 123.4}
        """
        try:
            data = json.loads(json_input)
            if "target_azimuth" in data:
                self.target_azimuth = data["target_azimuth"] % 360
                self.at_target = (self.current_azimuth == self.target_azimuth)
        except json.JSONDecodeError:
            print("Error: Invalid JSON received")

    def update_position(self, dt):
        """
        Calculates movement for the elapsed time 'dt'.
        """
        if self.current_azimuth == self.target_azimuth:
            self.at_target = True
            return

        # Calculate shortest path (-180 to 180 degrees)
        diff = (self.target_azimuth - self.current_azimuth + 180) % 360 - 180
        
        step_distance = self.rotation_speed * dt

        if abs(diff) <= step_distance:
            # Reached/Snapped to target
            self.current_azimuth = self.target_azimuth
            self.at_target = True
        else:
            # Move towards target
            direction = 1 if diff > 0 else -1
            self.current_azimuth = (self.current_azimuth + direction * step_distance) % 360
            self.at_target = False

    def get_status_json(self):
        """
        Returns the current state as a JSON string.
        """
        return json.dumps(self.get_status())

    def get_status(self):
        """Returns the current state as a dict."""
        return {
            "current_azimuth": round(self.current_azimuth, 2),
            "at_target": self.at_target,
            "internal_speed": self.rotation_speed,
            "target_azimuth": round(self.target_azimuth, 2),
        }

def doinit():
    """Initialize and prime the turret controller."""
    global turret
    turret = TurretController(initial_azimuth=0.0, rotation_speed=30.0)
    incoming_json = '{"target_azimuth": 90.0}'
    turret.process_input(incoming_json)
    return turret


def docycle(turret, dt=0.1):
    """Run one update cycle at the given timestep."""
    with lock:
        turret.update_position(dt)
        status = turret.get_status()
    return status


def _run_loop(dt=UPDATE_DT):
    """Background loop to keep the turret moving."""
    while not shutdown_event.is_set():
        docycle(turret, dt=dt)
        time.sleep(dt)


@app.route("/status", methods=["GET"])
def http_status():
    if turret is None:
        return jsonify({"error": "turret not initialized"}), 503
    with lock:
        status = turret.get_status()
    return jsonify(status)


@app.route("/target", methods=["POST"])
def http_set_target():
    if turret is None:
        return jsonify({"error": "turret not initialized"}), 503

    payload = request.get_json(silent=True) or {}
    if "target_azimuth" not in payload:
        return jsonify({"error": "target_azimuth required"}), 400

    try:
        target_value = float(payload["target_azimuth"])
    except (TypeError, ValueError):
        return jsonify({"error": "target_azimuth must be a number"}), 400

    with lock:
        turret.process_input(json.dumps({"target_azimuth": target_value}))
        status = turret.get_status()

    return jsonify(status)


if __name__ == "__main__":
    turret = doinit()
    print("Starting movement loop and REST server on http://0.0.0.0:5000")
    loop_thread = threading.Thread(target=_run_loop, kwargs={"dt": UPDATE_DT}, daemon=True)
    loop_thread.start()
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Stopping")
    finally:
        shutdown_event.set()
        loop_thread.join(timeout=2)