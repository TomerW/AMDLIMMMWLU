import time
import random
import threading
from . import config

class Target:
    """Holds the data and logic for a single target in 3D space."""
    def __init__(self, target_id):
        self.target_id = target_id
        self.x = round(random.uniform(-500, 500), 2)
        self.y = round(random.uniform(-500, 500), 2)
        self.z = round(random.uniform(0, 500), 2)
        # Random constant velocity
        self.vx = round(random.uniform(-20, 20), 2)
        self.vy = round(random.uniform(-20, 20), 2)
        self.vz = round(random.uniform(-5, 5), 2)
        self.creation_time = time.time()

    def update_position(self, dt):
        self.x = round(self.x + (self.vx * dt), 2)
        self.y = round(self.y + (self.vy * dt), 2)
        self.z = round(self.z + (self.vz * dt), 2)

    def to_dict(self):
        return {
            "id": self.target_id,
            "timestamp": time.time(),
            "position": {"x": self.x, "y": self.y, "z": self.z},
            "velocity": {"vx": self.vx, "vy": self.vy, "vz": self.vz}
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