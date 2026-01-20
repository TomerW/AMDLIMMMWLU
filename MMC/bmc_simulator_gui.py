from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from copy import deepcopy
from typing import Any, Dict

import httpx
import tkinter as tk
from tkinter import messagebox, ttk

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


def _dump_json(widget: tk.Text, data: Dict[str, Any]) -> None:
	widget.delete("1.0", tk.END)
	widget.insert(tk.END, json.dumps(data, indent=2))


def _parse_json(widget: tk.Text) -> Dict[str, Any]:
	text = widget.get("1.0", tk.END).strip()
	if not text:
		return {}
	return json.loads(text)


class BmcSimulatorGUI:
	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("BMC Simulator")
		self.base_url_var = tk.StringVar(value=os.getenv("MMC_BASE_URL", "http://127.0.0.1:4000"))
		self.state_path = os.getenv("BMC_SIM_STATE", "bmc_sim_state.json")
		self.state = _load_state(self.state_path)
		self.mmc_process: subprocess.Popen[str] | None = None
		self.last_turret_status: Dict[str, Any] | None = None
		self.last_turret_command: Dict[str, Any] | None = None
		self._polling_command = False
		self._polling_status = False

		self._build_ui()
		self._load_into_widgets()
		self._start_mmc()
		self._schedule_poll_turret_command()
		self._schedule_poll_turret_status()
		self.root.protocol("WM_DELETE_WINDOW", self._on_close)

	def _start_mmc(self) -> None:
		main_path = os.path.join(os.path.dirname(__file__), "main")
		if not os.path.exists(main_path):
			self._log("MMC main file not found; skipping auto-start.")
			return
		env = os.environ.copy()
		env.setdefault("TURRET_BASE_URL", "http://172.20.10.4:5000")
		self.mmc_process = subprocess.Popen(
			[sys.executable, main_path],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
			env=env,
		)
		self._log("Started MMC server.")

	def _on_close(self) -> None:
		if self.mmc_process and self.mmc_process.poll() is None:
			self.mmc_process.terminate()
		self.root.destroy()

	def _build_ui(self) -> None:
		top = ttk.Frame(self.root, padding=8)
		top.pack(fill=tk.BOTH, expand=True)

		url_frame = ttk.Frame(top)
		url_frame.pack(fill=tk.X, pady=(0, 8))
		ttk.Label(url_frame, text="MMC Base URL:").pack(side=tk.LEFT)
		ttk.Entry(url_frame, textvariable=self.base_url_var, width=40).pack(side=tk.LEFT, padx=(8, 0))

		notebook = ttk.Notebook(top)
		notebook.pack(fill=tk.BOTH, expand=True)

		self.target_text = tk.Text(notebook, width=60, height=16)
		self.fire_text = tk.Text(notebook, width=60, height=10)
		self.status_text = tk.Text(notebook, width=60, height=8)

		notebook.add(self.target_text, text="Target")
		notebook.add(self.fire_text, text="Fire Command")
		notebook.add(self.status_text, text="Status")

		button_frame = ttk.Frame(top)
		button_frame.pack(fill=tk.X, pady=(8, 0))

		ttk.Button(button_frame, text="Send Target", command=self.send_target).pack(side=tk.LEFT)
		ttk.Button(button_frame, text="Send Fire", command=self.send_fire).pack(side=tk.LEFT, padx=6)
		ttk.Button(button_frame, text="Send Status", command=self.send_status).pack(side=tk.LEFT)
		ttk.Button(button_frame, text="Save", command=self.save_state).pack(side=tk.RIGHT)

		self.output = tk.Text(top, height=6)
		self.output.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
		self.output.configure(state=tk.DISABLED)

	def _load_into_widgets(self) -> None:
		_dump_json(self.target_text, self.state.get("target", {}))
		_dump_json(self.fire_text, self.state.get("fire_command", {}))
		_dump_json(self.status_text, self.state.get("status", {}))

	def _log(self, message: str) -> None:
		self.output.configure(state=tk.NORMAL)
		self.output.insert(tk.END, message + "\n")
		self.output.see(tk.END)
		self.output.configure(state=tk.DISABLED)

	def _schedule_poll_turret_command(self) -> None:
		self.root.after(200, self._poll_turret_command)

	def _poll_turret_command(self) -> None:
		if self._polling_command:
			self.root.after(1000, self._poll_turret_command)
			return
		self._polling_command = True
		threading.Thread(target=self._fetch_turret_command, daemon=True).start()
		self.root.after(1000, self._poll_turret_command)

	def _fetch_turret_command(self) -> None:
		base_url = self.base_url_var.get().strip()
		if not base_url:
			self._polling_command = False
			return
		try:
			with httpx.Client(timeout=2.0) as client:
				response = client.get(f"{base_url}/turret/azimuth-command")
				if response.status_code == 200:
					payload = response.json()
					if payload != self.last_turret_command:
						self.last_turret_command = payload
						self.root.after(0, lambda: self._log(f"MMC -> Turret: azimuth_command {payload}"))
		except httpx.HTTPError:
			pass
		finally:
			self._polling_command = False

	def _schedule_poll_turret_status(self) -> None:
		self.root.after(200, self._poll_turret_status)

	def _poll_turret_status(self) -> None:
		if self._polling_status:
			self.root.after(1000, self._poll_turret_status)
			return
		self._polling_status = True
		threading.Thread(target=self._fetch_turret_status, daemon=True).start()
		self.root.after(1000, self._poll_turret_status)

	def _fetch_turret_status(self) -> None:
		base_url = self.base_url_var.get().strip()
		if not base_url:
			self._polling_status = False
			return
		try:
			with httpx.Client(timeout=2.0) as client:
				response = client.get(f"{base_url}/turret/azimuth-status")
				if response.status_code == 200:
					payload = response.json()
					if payload != self.last_turret_status:
						self.last_turret_status = payload
						self.root.after(0, lambda: self._log(f"Turret -> MMC: azimuth_status {payload}"))
		except httpx.HTTPError:
			pass
		finally:
			self._polling_status = False

	def _send(self, path: str, payload: Dict[str, Any]) -> None:
		base_url = self.base_url_var.get().strip()
		if not base_url:
			messagebox.showerror("Error", "MMC base URL is empty.")
			return
		try:
			with httpx.Client(timeout=5.0) as client:
				response = client.post(f"{base_url}{path}", json=payload)
				self._log(f"POST {path} -> {response.status_code}")
				try:
					self._log(json.dumps(response.json(), indent=2))
				except ValueError:
					self._log(response.text)
		except httpx.HTTPError as exc:
			messagebox.showerror("HTTP Error", str(exc))

	def send_target(self) -> None:
		try:
			payload = _parse_json(self.target_text)
			self.state["target"] = payload
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		self._send("/bmc/target", payload)

	def send_fire(self) -> None:
		try:
			payload = _parse_json(self.fire_text)
			self.state["fire_command"] = payload
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		self._send("/bmc/fire-command", payload)

	def send_status(self) -> None:
		try:
			payload = _parse_json(self.status_text)
			self.state["status"] = payload
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		self._send("/bmc/status", payload)

	def save_state(self) -> None:
		try:
			self.state["target"] = _parse_json(self.target_text)
			self.state["fire_command"] = _parse_json(self.fire_text)
			self.state["status"] = _parse_json(self.status_text)
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		_save_state(self.state_path, self.state)
		self._log(f"Saved to {self.state_path}")


if __name__ == "__main__":
	root = tk.Tk()
	app = BmcSimulatorGUI(root)
	root.mainloop()
