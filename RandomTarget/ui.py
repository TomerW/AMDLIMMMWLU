import tkinter as tk
from tkinter import ttk
import threading
import time
from . import config, target, logger

class TargetGeneratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("3D Target Generator Controller")
        self.root.geometry("640x420")
        self.target_counter = 0

        # top controls
        top = tk.Frame(root)
        top.pack(fill=tk.X, pady=6)
        self.btn_add_target = tk.Button(top, text="GENERATE TARGET THREAD", command=self.add_target_thread, bg="#4CAF50", fg="white")
        self.btn_add_target.pack(side=tk.LEFT, padx=6)

        tk.Label(top, text="JSON write interval (s):").pack(side=tk.LEFT, padx=(12,0))
        self.entry_json_rate = tk.Entry(top, width=6)
        self.entry_json_rate.insert(0, str(config.JSON_WRITE_RATE))
        self.entry_json_rate.pack(side=tk.LEFT, padx=4)
        self.btn_apply_rate = tk.Button(top, text="Apply", command=self.apply_json_rate)
        self.btn_apply_rate.pack(side=tk.LEFT)

        # endpoint controls
        ep_frame = tk.Frame(root)
        ep_frame.pack(fill=tk.X, pady=6, padx=8)
        tk.Label(ep_frame, text="Endpoint URL:").grid(row=0, column=0, sticky=tk.W)
        self.entry_endpoint = tk.Entry(ep_frame, width=64)
        self.entry_endpoint.insert(0, config.ENDPOINT_URL)
        self.entry_endpoint.grid(row=0, column=1, padx=6)
        tk.Label(ep_frame, text="API Key (opt):").grid(row=1, column=0, sticky=tk.W)
        self.entry_api_key = tk.Entry(ep_frame, width=64, show="*")
        self.entry_api_key.insert(0, config.ENDPOINT_API_KEY)
        self.entry_api_key.grid(row=1, column=1, padx=6)
        self.var_send_enabled = tk.BooleanVar(value=config.SEND_TO_ENDPOINT)
        self.chk_send = tk.Checkbutton(ep_frame, text="Send JSON to endpoint", variable=self.var_send_enabled)
        self.chk_send.grid(row=2, column=0, sticky=tk.W, pady=4)
        self.btn_apply_endpoint = tk.Button(ep_frame, text="Apply Endpoint", command=self.apply_endpoint_settings)
        self.btn_apply_endpoint.grid(row=2, column=1, sticky=tk.E, padx=6)

        # main panels
        main = tk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left: list of targets
        left = tk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0,8))
        tk.Label(left, text="Active Targets:").pack(anchor=tk.W)
        self.lst_targets = tk.Listbox(left, height=16, width=20)
        self.lst_targets.pack()
        self.lst_targets.bind("<<ListboxSelect>>", self.on_select_target)

        # Right: progress/details
        right = tk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(right, text="Selected Target Progress:").pack(anchor=tk.W)
        self.progress = ttk.Progressbar(right, orient=tk.HORIZONTAL, length=400, mode="determinate", maximum=config.TARGET_LIFETIME)
        self.progress.pack(pady=6)
        self.lbl_progress = tk.Label(right, text="No selection")
        self.lbl_progress.pack(anchor=tk.W)
        self.lbl_details = tk.Label(right, text="Details: -")
        self.lbl_details.pack(anchor=tk.W, pady=(6,0))

        # status/footer
        self.label_status = tk.Label(root, text="Active: 0", fg="blue")
        self.label_status.pack(side=tk.BOTTOM, pady=6)

        # Start logger thread
        self.logger_thread = threading.Thread(target=logger.json_logger_task, daemon=False)
        self.logger_thread.start()

        self._schedule_status_update()

    def add_target_thread(self):
        self.target_counter += 1
        new_target = target.Target(target_id=f"T-{self.target_counter}")

        with config.targets_lock:
            config.active_targets.append(new_target)

        t = threading.Thread(target=target.target_thread_task, args=(new_target,), daemon=False)
        t.start()
        config.target_threads.append(t)

        self.update_status_label()
        print(f"-> Spawned Target {new_target.target_id} (vx={new_target.vx}, vy={new_target.vy}, vz={new_target.vz})")

    def apply_json_rate(self):
        try:
            val = float(self.entry_json_rate.get())
            if val <= 0:
                raise ValueError("Must be positive")
            config.JSON_WRITE_RATE = val
            print(f"JSON write interval set to {config.JSON_WRITE_RATE} s")
        except Exception as e:
            print(f"Invalid interval: {e}")

    def apply_endpoint_settings(self):
        config.ENDPOINT_URL = self.entry_endpoint.get().strip()
        config.ENDPOINT_API_KEY = self.entry_api_key.get().strip()
        config.SEND_TO_ENDPOINT = bool(self.var_send_enabled.get())
        print(f"Endpoint set to: {config.ENDPOINT_URL} (send_enabled={config.SEND_TO_ENDPOINT})")

    def update_status_label(self):
        with config.targets_lock:
            ids = [t.target_id for t in config.active_targets]
        # refresh listbox
        self.lst_targets.delete(0, tk.END)
        for tid in ids:
            self.lst_targets.insert(tk.END, tid)
        self.label_status.config(text=f"Active: {len(ids)}")

    def on_select_target(self, event):
        sel = self.lst_targets.curselection()
        if not sel:
            self.lbl_progress.config(text="No selection")
            self.progress['value'] = 0
            self.lbl_details.config(text="Details: -")
            return
        idx = sel[0]
        tid = self.lst_targets.get(idx)
        # find target object
        with config.targets_lock:
            found = next((t for t in config.active_targets if t.target_id == tid), None)
        if found:
            age = time.time() - found.creation_time
            remaining = max(0.0, config.TARGET_LIFETIME - age)
            self.progress['maximum'] = config.TARGET_LIFETIME
            self.progress['value'] = min(config.TARGET_LIFETIME, age)
            self.lbl_progress.config(text=f"ID {found.target_id} — age {age:.1f}s / {config.TARGET_LIFETIME}s (remaining {remaining:.1f}s)")
            details = f"pos=({found.x},{found.y},{found.z}) vel=({found.vx},{found.vy},{found.vz})"
            self.lbl_details.config(text=f"Details: {details}")
        else:
            self.lbl_progress.config(text="Selected target not found")
            self.progress['value'] = 0
            self.lbl_details.config(text="Details: -")

    def _schedule_status_update(self):
        self.update_status_label()
        # update selection progress too
        self.on_select_target(None)
        self.root.after(100, self._schedule_status_update)

    def on_closing(self):
        print("\nStopping all threads... please wait.")
        config.stop_threads_event.set()

        for t in list(config.target_threads):
            t.join(timeout=1.0)

        if hasattr(self, "logger_thread"):
            self.logger_thread.join(timeout=2.0)

        time.sleep(0.05)
        self.root.destroy()