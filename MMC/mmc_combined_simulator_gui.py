from __future__ import annotations

import json
import os
import queue
import threading
import subprocess
import sys
from copy import deepcopy
from typing import Any, Dict

import httpx
import tkinter as tk
from tkinter import messagebox, ttk
import uvicorn
from fastapi import FastAPI, Request

DEFAULT_BMC_STATE: Dict[str, Any] = {
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

DEFAULT_TURRET_STATUS: Dict[str, Any] = {
	"current_azimuth": 0,
}


def _load_state(path: str) -> Dict[str, Any]:
	if not os.path.exists(path):
		return deepcopy(DEFAULT_BMC_STATE)
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


class TurretServer:
	def __init__(self, host: str, port: int, message_queue: "queue.Queue[Dict[str, Any]]") -> None:
		self.host = host
		self.port = port
		self.message_queue = message_queue
		self._thread: threading.Thread | None = None
		self._server: uvicorn.Server | None = None
		self._app = FastAPI(title="Turret Simulator")
		self._setup_routes()

	def _setup_routes(self) -> None:
		@self._app.post("/turret/azimuth-command")
		async def receive_command(request: Request) -> Dict[str, str]:
			payload = await request.json()
			self.message_queue.put(payload)
			return {"status": "OK"}

	def start(self) -> None:
		if self._thread and self._thread.is_alive():
			return
		config = uvicorn.Config(self._app, host=self.host, port=self.port, log_level="warning")
		self._server = uvicorn.Server(config)
		self._thread = threading.Thread(target=self._server.run, daemon=True)
		self._thread.start()

	def stop(self) -> None:
		if self._server:
			self._server.should_exit = True


class CombinedSimulatorGUI:
	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("MMC Combined Simulator")

		self.mmc_base_url_var = tk.StringVar(value=os.getenv("MMC_BASE_URL", "http://127.0.0.1:4000"))
		self.state_path = os.getenv("BMC_SIM_STATE", "bmc_sim_state.json")
		self.bmc_state = _load_state(self.state_path)
		self.turret_status = DEFAULT_TURRET_STATUS.copy()

		self.mmc_process: subprocess.Popen[str] | None = None

		self.message_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
		self.turret_port = int(os.getenv("TURRET_SIM_PORT", "5000"))
		self.server = TurretServer("127.0.0.1", self.turret_port, self.message_queue)

		self._build_ui()
		self._load_into_widgets()
		self._start_mmc()
		self.server.start()
		self._log(f"Turret server started on port {self.turret_port}.")
		self._poll_queue()
		self.root.protocol("WM_DELETE_WINDOW", self._on_close)

	def _start_mmc(self) -> None:
		main_path = os.path.join(os.path.dirname(__file__), "main")
		if not os.path.exists(main_path):
			self._log("MMC main file not found; skipping auto-start.")
			return
		self.mmc_process = subprocess.Popen(
			[sys.executable, main_path],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
		)
		self._log("Started MMC server.")

	def _build_ui(self) -> None:
		top = ttk.Frame(self.root, padding=8)
		top.pack(fill=tk.BOTH, expand=True)

		url_frame = ttk.Frame(top)
		url_frame.pack(fill=tk.X, pady=(0, 8))
		ttk.Label(url_frame, text="MMC Base URL:").pack(side=tk.LEFT)
		ttk.Entry(url_frame, textvariable=self.mmc_base_url_var, width=40).pack(side=tk.LEFT, padx=(8, 0))

		notebook = ttk.Notebook(top)
		notebook.pack(fill=tk.BOTH, expand=True)

		bmc_frame = ttk.Frame(notebook, padding=8)
		turret_frame = ttk.Frame(notebook, padding=8)

		notebook.add(bmc_frame, text="BMC")
		notebook.add(turret_frame, text="Turret")

		self.target_text = tk.Text(bmc_frame, width=60, height=16)
		self.fire_text = tk.Text(bmc_frame, width=60, height=10)
		self.bmc_status_text = tk.Text(bmc_frame, width=60, height=8)

		self.target_text.pack(fill=tk.BOTH, expand=False)
		self.fire_text.pack(fill=tk.BOTH, expand=False, pady=(6, 0))
		self.bmc_status_text.pack(fill=tk.BOTH, expand=False, pady=(6, 0))

		bmc_button_frame = ttk.Frame(bmc_frame)
		bmc_button_frame.pack(fill=tk.X, pady=(8, 0))
		ttk.Button(bmc_button_frame, text="Send Target", command=self.send_target).pack(side=tk.LEFT)
		ttk.Button(bmc_button_frame, text="Send Fire", command=self.send_fire).pack(side=tk.LEFT, padx=6)
		ttk.Button(bmc_button_frame, text="Send Status", command=self.send_bmc_status).pack(side=tk.LEFT)
		ttk.Button(bmc_button_frame, text="Save", command=self.save_state).pack(side=tk.RIGHT)

		self.turret_status_text = tk.Text(turret_frame, width=60, height=8)
		self.turret_status_text.pack(fill=tk.BOTH, expand=False)

		turret_button_frame = ttk.Frame(turret_frame)
		turret_button_frame.pack(fill=tk.X, pady=(8, 0))
		ttk.Button(turret_button_frame, text="Send Azimuth Status", command=self.send_turret_status).pack(side=tk.LEFT)

		self.last_command_var = tk.StringVar(value="No command received yet")
		last_frame = ttk.Frame(turret_frame)
		last_frame.pack(fill=tk.X, pady=(8, 0))
		ttk.Label(last_frame, text="Last azimuth command:").pack(side=tk.LEFT)
		ttk.Label(last_frame, textvariable=self.last_command_var).pack(side=tk.LEFT, padx=(8, 0))

		self.output = tk.Text(top, height=10)
		self.output.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
		self.output.configure(state=tk.DISABLED)

	def _load_into_widgets(self) -> None:
		_dump_json(self.target_text, self.bmc_state.get("target", {}))
		_dump_json(self.fire_text, self.bmc_state.get("fire_command", {}))
		_dump_json(self.bmc_status_text, self.bmc_state.get("status", {}))
		_dump_json(self.turret_status_text, self.turret_status)

	def _log(self, message: str) -> None:
		self.output.configure(state=tk.NORMAL)
		self.output.insert(tk.END, message + "\n")
		self.output.see(tk.END)
		self.output.configure(state=tk.DISABLED)

	def _post(self, path: str, payload: Dict[str, Any]) -> None:
		base_url = self.mmc_base_url_var.get().strip()
		if not base_url:
			messagebox.showerror("Error", "MMC base URL is empty.")
			return
		try:
			with httpx.Client(timeout=5.0) as client:
				response = client.post(f"{base_url}{path}", json=payload)
				self._log(f"POST {path} -> {response.status_code}")
				self._log(f"Payload: {payload}")
				try:
					self._log(json.dumps(response.json(), indent=2))
				except ValueError:
					self._log(response.text)
		except httpx.HTTPError as exc:
			messagebox.showerror("HTTP Error", str(exc))

	def send_target(self) -> None:
		try:
			payload = _parse_json(self.target_text)
			self.bmc_state["target"] = payload
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		self._log("BMC -> MMC: target")
		self._post("/bmc/target", payload)

	def send_fire(self) -> None:
		try:
			payload = _parse_json(self.fire_text)
			self.bmc_state["fire_command"] = payload
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		self._log("BMC -> MMC: fire_command")
		self._post("/bmc/fire-command", payload)

	def send_bmc_status(self) -> None:
		try:
			payload = _parse_json(self.bmc_status_text)
			self.bmc_state["status"] = payload
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		self._log("BMC -> MMC: status")
		self._post("/bmc/status", payload)

	def send_turret_status(self) -> None:
		try:
			payload = _parse_json(self.turret_status_text)
			self.turret_status = payload
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		self._log("Turret -> MMC: azimuth_status")
		self._post("/turret/azimuth-status", payload)

	def _poll_queue(self) -> None:
		try:
			while True:
				payload = self.message_queue.get_nowait()
				self.last_command_var.set(json.dumps(payload))
				self._log(f"MMC -> Turret: azimuth_command {payload}")
		except queue.Empty:
			pass
		self.root.after(200, self._poll_queue)

	def save_state(self) -> None:
		try:
			self.bmc_state["target"] = _parse_json(self.target_text)
			self.bmc_state["fire_command"] = _parse_json(self.fire_text)
			self.bmc_state["status"] = _parse_json(self.bmc_status_text)
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		_save_state(self.state_path, self.bmc_state)
		self._log(f"Saved to {self.state_path}")

	def _on_close(self) -> None:
		self.server.stop()
		if self.mmc_process and self.mmc_process.poll() is None:
			self.mmc_process.terminate()
		self.root.destroy()


if __name__ == "__main__":
	root = tk.Tk()
	app = CombinedSimulatorGUI(root)
	root.mainloop()
