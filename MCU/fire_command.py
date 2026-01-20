"""
Simple FireCommand and handler for MCU.
Processes a Fire command and returns a LOCK ACK immediately.
Sends optional callbacks to MMC callback URL (fire-and-forget).
"""

import time
import threading
import json
import urllib.request
from . import config


def _post_json(url, payload, timeout=1.0):
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
        return True
    except Exception:
        return False


class FireCommand:
    def __init__(self, command_id, target_id, weapon_type, azimuth, elevation, range_m):
        self.command_id = command_id
        self.target_id = target_id
        self.weapon_type = weapon_type
        self.azimuth = azimuth
        self.elevation = elevation
        self.range_m = range_m
        self.state = config.FIRE_STATE_IDLE
        self.created_time = time.time()
        self.started_time = None
        self.completed_time = None

    def to_dict(self):
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
        }

    def execute(self):
        try:
            self.state = config.FIRE_STATE_FIRING
            self.started_time = time.time()
            # simulate
            time.sleep(0.25)
            self.state = config.FIRE_STATE_COMPLETED
            self.completed_time = time.time()
            return True
        except Exception:
            self.state = config.FIRE_STATE_ERROR
            return False


class FireCommandHandler:
    def __init__(self, event_callback=None):
        self.commands = {}
        self.lock = threading.Lock()
        self.event_callback = event_callback

    def process_fire_command(self, cmd_json):
        try:
            cmd_id = cmd_json.get('command_id')
            target_id = cmd_json.get('target_id')
            if not cmd_id or not target_id:
                return config.ACK_INVALID_COMMAND, {"error": "missing command_id or target_id"}

            with self.lock:
                if cmd_id in self.commands:
                    return config.ACK_BUSY, {"error": "already processing"}

                cmd = FireCommand(cmd_id, target_id, cmd_json.get('weapon_type','CANNON'), float(cmd_json.get('azimuth',0.0)), float(cmd_json.get('elevation',0.0)), float(cmd_json.get('range_m',0.0)))
                cmd.state = config.FIRE_STATE_LOCKED
                self.commands[cmd_id] = cmd

                # notify event buffer
                if self.event_callback:
                    try:
                        self.event_callback({"type":"accepted","command_id":cmd_id,"payload":cmd.to_dict(),"timestamp":time.time()})
                    except Exception:
                        pass

                # send lock callback to MMC (fire-and-forget)
                try:
                    if config.MMC_CALLBACK_URL:
                        _post_json(config.MMC_CALLBACK_URL, {"command_id": cmd_id, "status": "LOCKED", "timestamp": time.time()})
                except Exception:
                    pass

            # run execution in background, keep status briefly
            def _run():
                ok = cmd.execute()
                # notify completion
                if self.event_callback:
                    try:
                        self.event_callback({"type":"completed","command_id":cmd_id,"success":ok,"state":cmd.state,"timestamp":time.time()})
                    except Exception:
                        pass
                # send completion callback
                try:
                    if config.MMC_CALLBACK_URL:
                        _post_json(config.MMC_CALLBACK_URL, {"command_id":cmd_id,"status":cmd.state,"success":ok,"timestamp":time.time()})
                except Exception:
                    pass
                # cleanup after short delay
                time.sleep(1.0)
                with self.lock:
                    self.commands.pop(cmd_id, None)

            t = threading.Thread(target=_run, daemon=True)
            t.start()

            return config.ACK_SUCCESS, {"ack_code": config.ACK_SUCCESS, "command_id": cmd_id, "state": config.FIRE_STATE_LOCKED, "message": f"{cmd_id} locked"}

        except Exception as e:
            return config.ACK_ERROR, {"error": str(e)}

    def get_command_status(self, command_id):
        with self.lock:
            c = self.commands.get(command_id)
            if c:
                return {"command_id": command_id, "state": c.state, "data": c.to_dict()}
            return {"error": "not found"}
