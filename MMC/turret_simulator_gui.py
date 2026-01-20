from __future__ import annotations

import json
import os
import queue
import threading
import subprocess
import sys
from typing import Any, Dict

import httpx
import tkinter as tk
from tkinter import messagebox, ttk
import uvicorn
from fastapi import FastAPI, Request

DEFAULT_STATUS: Dict[str, Any] = {
	"current_azimuth": 0,
}


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


class TurretSimulatorGUI:
	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("Turret Simulator")
		self.mmc_base_url_var = tk.StringVar(value=os.getenv("MMC_BASE_URL", "http://127.0.0.1:4000"))
		self.status_payload = DEFAULT_STATUS.copy()
		self.mmc_process: subprocess.Popen[str] | None = None

		self.message_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
		self.server = TurretServer("0.0.0.0", 5000, self.message_queue)

		self._build_ui()
		self._load_into_widgets()
		self._start_mmc()
		self.server.start()
		self._log("Turret server started on port 5000.")
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

		self.status_text = tk.Text(top, width=60, height=8)
		self.status_text.pack(fill=tk.BOTH, expand=False)

		button_frame = ttk.Frame(top)
		button_frame.pack(fill=tk.X, pady=(8, 0))
		ttk.Button(button_frame, text="Send Azimuth Status", command=self.send_status).pack(side=tk.LEFT)

		self.last_command_var = tk.StringVar(value="No command received yet")
		last_frame = ttk.Frame(top)
		last_frame.pack(fill=tk.X, pady=(8, 0))
		ttk.Label(last_frame, text="Last azimuth command:").pack(side=tk.LEFT)
		ttk.Label(last_frame, textvariable=self.last_command_var).pack(side=tk.LEFT, padx=(8, 0))

		self.output = tk.Text(top, height=6)
		self.output.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
		self.output.configure(state=tk.DISABLED)

	def _load_into_widgets(self) -> None:
		_dump_json(self.status_text, self.status_payload)

	def _log(self, message: str) -> None:
		self.output.configure(state=tk.NORMAL)
		self.output.insert(tk.END, message + "\n")
		self.output.see(tk.END)
		self.output.configure(state=tk.DISABLED)

	def _poll_queue(self) -> None:
		try:
			while True:
				payload = self.message_queue.get_nowait()
				self.last_command_var.set(json.dumps(payload))
				self._log(f"Received azimuth command: {payload}")
		except queue.Empty:
			pass
		self.root.after(200, self._poll_queue)

	def send_status(self) -> None:
		try:
			payload = _parse_json(self.status_text)
			self.status_payload = payload
		except json.JSONDecodeError as exc:
			messagebox.showerror("Invalid JSON", str(exc))
			return
		base_url = self.mmc_base_url_var.get().strip()
		if not base_url:
			messagebox.showerror("Error", "MMC base URL is empty.")
			return
		try:
			with httpx.Client(timeout=5.0) as client:
				response = client.post(f"{base_url}/turret/azimuth-status", json=payload)
				self._log(f"POST /turret/azimuth-status -> {response.status_code}")
				try:
					self._log(json.dumps(response.json(), indent=2))
				except ValueError:
					self._log(response.text)
		except httpx.HTTPError as exc:
			messagebox.showerror("HTTP Error", str(exc))

	def _on_close(self) -> None:
		self.server.stop()
		if self.mmc_process and self.mmc_process.poll() is None:
			self.mmc_process.terminate()
		self.root.destroy()


if __name__ == "__main__":
	root = tk.Tk()
	app = TurretSimulatorGUI(root)
	root.mainloop()
