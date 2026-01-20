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
                # store as floats for smoother updates
                self.north = float(random.uniform(-500, 500))
                self.east = float(random.uniform(-500, 500))
                self.down = float(random.uniform(0, 500))
                # Random constant velocity in NED (m/s)
                self.vn = float(random.uniform(-20, 20))  # north velocity
                self.ve = float(random.uniform(-20, 20))  # east velocity
                self.vd = float(random.uniform(-5, 5))    # down velocity
                self.creation_time = time.time()

        def update_position(self, dt):
                """Update NED position using velocities and dt seconds."""
                # keep float precision for smooth animation
                self.north = self.north + (self.vn * dt)
                self.east = self.east + (self.ve * dt)
                self.down = self.down + (self.vd * dt)

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


def kill_all_targets():
    """Remove all active targets immediately.

    Returns the number of targets removed.
    """
    removed = 0
    with config.targets_lock:
        removed = len(config.active_targets)
        config.active_targets.clear()
    return removed