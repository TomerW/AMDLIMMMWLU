from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any, Dict

import httpx

DEFAULT_STATE: Dict[str, Any] = {
	"target": {
		"target_id": 1,
		"position_north": 1000.0,
		"position_east": 0.0,
		"position_down": 0.0,
		"velocity_north": 0.0,
		"velocity_east": 0.0,
		"velocity_down": 0.0,
	},
	"fire_command": {
		"fire_command": "NO",
		"target_id": 1,
	},
	"status": {
		"is_missile_lock": False,
	},
}


def _load_state(path: str) -> Dict[str, Any]:
	if not os.path.exists(path):
		return deepcopy(DEFAULT_STATE)
	with open(path, "r", encoding="utf-8") as handle:
		return json.load(handle)


def _save_state(path: str, state: Dict[str, Any]) -> None:
	with open(path, "w", encoding="utf-8") as handle:
		json.dump(state, handle, indent=2)
		handle.write("\n")


def _prompt(prompt: str) -> str:
	return input(prompt).strip()


def _parse_value(raw: str) -> Any:
	try:
		return json.loads(raw)
	except json.JSONDecodeError:
		return raw


def _edit_message(state: Dict[str, Any], message_key: str) -> None:
	message = state.get(message_key, {})
	print(f"Current {message_key}: {json.dumps(message, indent=2)}")
	field = _prompt("Field to edit (empty to cancel): ")
	if not field:
		return
	value_raw = _prompt("New value (JSON): ")
	value = _parse_value(value_raw)
	message[field] = value
	state[message_key] = message
	print(f"Updated {message_key}: {json.dumps(message, indent=2)}")


def _send_message(client: httpx.Client, base_url: str, path: str, payload: Dict[str, Any]) -> None:
	response = client.post(f"{base_url}{path}", json=payload)
	print(f"POST {path} -> {response.status_code}")
	try:
		print(json.dumps(response.json(), indent=2))
	except ValueError:
		print(response.text)


def main() -> None:
	base_url = os.getenv("MMC_BASE_URL", "http://127.0.0.1:4000")
	state_path = os.getenv("BMC_SIM_STATE", "bmc_sim_state.json")
	state = _load_state(state_path)

	print("BMC Simulator")
	print(f"MMC base URL: {base_url}")
	print("Commands: show, edit target|fire_command|status, send target|fire_command|status, save, quit")

	with httpx.Client(timeout=5.0) as client:
		while True:
			command = _prompt("> ")
			if not command:
				continue
			if command in {"quit", "exit"}:
				break
			if command == "show":
				print(json.dumps(state, indent=2))
				continue
			if command == "save":
				_save_state(state_path, state)
				print(f"Saved to {state_path}")
				continue
			parts = command.split()
			if len(parts) == 2 and parts[0] == "edit":
				_edit_message(state, parts[1])
				continue
			if len(parts) == 2 and parts[0] == "send":
				key = parts[1]
				payload = state.get(key)
				if payload is None:
					print("Unknown message key.")
					continue
				if key == "target":
					_send_message(client, base_url, "/bmc/target", payload)
				elif key == "fire_command":
					_send_message(client, base_url, "/bmc/fire-command", payload)
				elif key == "status":
					_send_message(client, base_url, "/bmc/status", payload)
				else:
					print("Unknown message key.")
				continue
			print("Unknown command.")

	_save_state(state_path, state)
	print(f"Session saved to {state_path}")


if __name__ == "__main__":
	main()
