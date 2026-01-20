import time
import random
import threading
from . import config

class Target:
    """Holds the data and logic for a single target in North-East-Down (NED) coords.

    Attributes:
      north: float (meters)
      east:  float (meters)
      down:  float (meters, positive down)
      vn, ve, vd: velocities in m/s (north, east, down)
    """
    def __init__(self, target_id):
        self.target_id = target_id
        # NED coordinates
        self.north = round(random.uniform(-500, 500), 2)
        self.east = round(random.uniform(-500, 500), 2)
        self.down = round(random.uniform(0, 500), 2)
        # Random constant velocity in NED (m/s)
        self.vn = round(random.uniform(-20, 20), 2)  # north velocity
        self.ve = round(random.uniform(-20, 20), 2)  # east velocity
        self.vd = round(random.uniform(-5, 5), 2)    # down velocity
        self.creation_time = time.time()

    def update_position(self, dt):
        """Update NED position using velocities and dt seconds."""
        self.north = round(self.north + (self.vn * dt), 2)
        self.east = round(self.east + (self.ve * dt), 2)
        self.down = round(self.down + (self.vd * dt), 2)

    def to_dict(self):
        return {
            "id": self.target_id,
            "timestamp": time.time(),
            "position": {"north": self.north, "east": self.east, "down": self.down},
            "velocity": {"vn": self.vn, "ve": self.ve, "vd": self.vd}
        }

def target_thread_task(target_obj: Target):
    """Per-target thread: update position and remove after lifetime."""
    print(f"Thread started for Target ID: {target_obj.target_id}")
    last_time = time.time()
    while not config.stop_threads_event.is_set():
        now = time.time()
        dt = now - last_time
        last_time = now

        target_obj.update_position(dt)

        age = now - target_obj.creation_time
        if age >= config.TARGET_LIFETIME:
            with config.targets_lock:
                try:
                    config.active_targets.remove(target_obj)
                except ValueError:
                    pass
            print(f"Target {target_obj.target_id} expired after {config.TARGET_LIFETIME} seconds.")
            break

        time.sleep(config.TARGET_UPDATE_RATE)
    print(f"Thread stopped for Target ID: {target_obj.target_id}")