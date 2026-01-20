import json
import time

class TurretController:
    def __init__(self, initial_azimuth=0.0, rotation_speed=30.0):
        """
        :param initial_azimuth: Starting angle (0-360).
        :param rotation_speed: Fixed internal speed in degrees/second.
        """
        self.current_azimuth = initial_azimuth % 360
        self.target_azimuth = initial_azimuth % 360
        self.rotation_speed = rotation_speed
        self.at_target = True

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
        status = {
            "current_azimuth": round(self.current_azimuth, 2),
            "at_target": self.at_target,
            "internal_speed": self.rotation_speed
        }
        return json.dumps(status)

# --- Simulation of a Continuous Loop ---

# Initialize turret with 30 deg/sec speed
turret = TurretController(initial_azimuth=0.0, rotation_speed=30.0)

# Simulate receiving a target command via JSON
incoming_json = '{"target_azimuth": 90.0}'
turret.process_input(incoming_json)

dt = 0.1  # Simulate a 10Hz update frequency (0.1 seconds)

print("Starting Movement...")
for _ in range(35):  # Run for a few seconds
    turret.update_position(dt)
    
    # Get current status to return to sender
    output_status = turret.get_status_json()
    print(f"OUT: {output_status}")
    
    time.sleep(dt)