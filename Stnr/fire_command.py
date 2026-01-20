"""
Fire command model and handler for Stnr (Starboard).
Processes Fire commands from MMC and manages state transitions.
"""

import time
import threading
import json
from . import config


class FireCommand:
    """Represents a Fire command from MMC."""

    def __init__(self, command_id, target_id, weapon_type, azimuth, elevation, range_m):
        self.command_id = command_id
        self.target_id = target_id
        self.weapon_type = weapon_type
        self.azimuth = azimuth  # degrees
        self.elevation = elevation  # degrees
        self.range_m = range_m  # meters
        self.state = config.FIRE_STATE_IDLE
        self.created_time = time.time()
        self.started_time = None
        self.completed_time = None
        self.error_msg = None

    def to_dict(self):
        """Serialize to dictionary for JSON response."""
        return {
            "command_id": self.command_id,
            "target_id": self.target_id,
            "weapon_type": self.weapon_type,
            "azimuth": self.azimuth,
            "elevation": self.elevation,
            "range_m": self.range_m,
            "state": self.state,
            "created_time": self.created_time,
            "started_time": self.started_time,
            "completed_time": self.completed_time,
            "error_msg": self.error_msg,
        }

    def execute(self):
        """Simulate fire execution (move through ARMED -> FIRING -> COMPLETED)."""
        try:
            self.state = config.FIRE_STATE_ARMED
            print(f"[FIRE] Command {self.command_id} ARMED (target={self.target_id}, weapon={self.weapon_type})")

            self.state = config.FIRE_STATE_FIRING
            self.started_time = time.time()
            print(f"[FIRE] Command {self.command_id} FIRING (azimuth={self.azimuth}°, elevation={self.elevation}°, range={self.range_m}m)")

            # Simulate firing delay (250 ms)
            time.sleep(0.25)

            self.state = config.FIRE_STATE_COMPLETED
            self.completed_time = time.time()
            print(f"[FIRE] Command {self.command_id} COMPLETED in {self.completed_time - self.started_time:.3f}s")
            return True
        except Exception as e:
            self.state = config.FIRE_STATE_ERROR
            self.error_msg = str(e)
            print(f"[FIRE] Command {self.command_id} ERROR: {e}")
            return False


class FireCommandHandler:
    """Manages active fire commands and state."""

    def __init__(self):
        self.commands = {}  # command_id -> FireCommand
        self.lock = threading.Lock()
        self.current_state = config.FIRE_STATE_IDLE

    def process_fire_command(self, command_json):
        """
        Process a Fire command from MMC REST API.
        
        Expected JSON:
        {
            "command_id": "FIRE_001",
            "target_id": "T-1",
            "weapon_type": "CANNON",
            "azimuth": 45.0,
            "elevation": 10.0,
            "range_m": 2500.0
        }
        
        Returns: (ack_code, response_dict)
        """
        try:
            cmd_id = command_json.get("command_id")
            target_id = command_json.get("target_id")
            weapon_type = command_json.get("weapon_type", "CANNON")
            azimuth = float(command_json.get("azimuth", 0.0))
            elevation = float(command_json.get("elevation", 0.0))
            range_m = float(command_json.get("range_m", 0.0))

            if not cmd_id or not target_id:
                return config.ACK_INVALID_COMMAND, {"error": "Missing command_id or target_id"}

            with self.lock:
                if cmd_id in self.commands:
                    return config.ACK_BUSY, {"error": f"Command {cmd_id} already processing"}

                # Create and store the fire command
                fire_cmd = FireCommand(cmd_id, target_id, weapon_type, azimuth, elevation, range_m)
                self.commands[cmd_id] = fire_cmd

            # Execute fire command in a background thread
            def execute_async():
                fire_cmd.execute()
                # Optionally cleanup after delay
                time.sleep(1.0)
                with self.lock:
                    self.commands.pop(cmd_id, None)

            thread = threading.Thread(target=execute_async, daemon=True)
            thread.start()

            return config.ACK_SUCCESS, {
                "ack_code": config.ACK_SUCCESS,
                "command_id": cmd_id,
                "state": config.FIRE_STATE_ARMED,
                "message": f"Fire command {cmd_id} accepted and executing"
            }

        except Exception as e:
            print(f"[ERROR] process_fire_command: {e}")
            return config.ACK_ERROR, {"error": str(e)}

    def get_command_status(self, command_id):
        """Get current status of a fire command."""
        with self.lock:
            cmd = self.commands.get(command_id)
            if cmd:
                return {
                    "command_id": command_id,
                    "state": cmd.state,
                    "data": cmd.to_dict()
                }
            return {"error": f"Command {command_id} not found"}
