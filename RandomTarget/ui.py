import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import json
import os
import threading
import time
import math
from . import config, target, logger
import subprocess
import sys


class TargetGeneratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("3D Target Generator Controller (NED)")
        self.root.geometry("900x640")
        self.target_counter = 0

        # top controls
        top = tk.Frame(root)
        top.pack(fill=tk.X, pady=6)
        self.btn_add_target = tk.Button(top, text="GENERATE TARGET THREAD", command=self.add_target_thread, bg="#4CAF50", fg="white")
        self.btn_add_target.pack(side=tk.LEFT, padx=6)

        tk.Label(top, text="JSON write interval (s):").pack(side=tk.LEFT, padx=(12, 0))
        self.entry_json_rate = tk.Entry(top, width=6)
        self.entry_json_rate.insert(0, str(config.JSON_WRITE_RATE))
        self.entry_json_rate.pack(side=tk.LEFT, padx=4)
        self.btn_apply_rate = tk.Button(top, text="Apply", command=self.apply_json_rate)
        self.btn_apply_rate.pack(side=tk.LEFT)

        # toolbar with essential actions (always visible)
        tool_frame = tk.Frame(root)
        tool_frame.pack(fill=tk.X, pady=(4, 2))
        self.btn_refresh_json = tk.Button(tool_frame, text="Refresh JSON", command=self.load_json_preview)
        self.btn_refresh_json.pack(side=tk.LEFT, padx=4)
        self.btn_kill_all = tk.Button(tool_frame, text="KILL ALL TARGETS", command=self.kill_all_targets, bg="#f44336", fg="white")
        self.btn_kill_all.pack(side=tk.LEFT, padx=4)
        self.btn_toggle_server = tk.Button(tool_frame, text="Start Server", command=self.toggle_server)
        self.btn_toggle_server.pack(side=tk.LEFT, padx=4)
        self.btn_open_received = tk.Button(tool_frame, text="Open Received Folder", command=self.open_received_folder)
        self.btn_open_received.pack(side=tk.LEFT, padx=4)

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
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        tk.Label(left, text="Active Targets:").pack(anchor=tk.W)
        self.lst_targets = tk.Listbox(left, height=30, width=28)
        self.lst_targets.pack(fill=tk.Y, expand=False)
        self.lst_targets.bind("<<ListboxSelect>>", self.on_select_target)

        # Right-top: progress/details + JSON preview
        right = tk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(right, text="Selected Target Progress (NED):").pack(anchor=tk.W)
        # let the progress bar fill horizontally so it matches the JSON preview width
        self.progress = ttk.Progressbar(right, orient=tk.HORIZONTAL, mode="determinate", maximum=config.TARGET_LIFETIME)
        self.progress.pack(fill=tk.X, pady=6)
        self.lbl_progress = tk.Label(right, text="No selection")
        self.lbl_progress.pack(anchor=tk.W)
        self.lbl_details = tk.Label(right, text="Details: -")
        self.lbl_details.pack(anchor=tk.W, pady=(6, 0))

        # Minimal graphical preview (canvas)
        tk.Label(right, text="Simple map (East right, North up) :").pack(anchor=tk.W, pady=(6, 0))
        # reduce canvas height to give more room to JSON preview below
        self.canvas = tk.Canvas(right, height=180, bg="#f8f8f8", bd=1, relief=tk.SUNKEN, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=False, pady=(4, 6))
        # mapping objects
        self.canvas_items = {}
        # per-target recent position history for trails (screen coords)
        self.target_trails = {}
        self.trail_max = 30
        self.canvas_padding = 20
        # schedule canvas updates
        self._schedule_canvas_draw()

        # JSON preview area
        tk.Label(right, text="Latest JSON snapshot:").pack(anchor=tk.W, pady=(8, 0))
        # make JSON preview larger: fill remaining vertical space
        self.txt_json = scrolledtext.ScrolledText(right, height=20, width=96, wrap=tk.NONE)
        self.txt_json.pack(fill=tk.BOTH, expand=True)
        self.txt_json.config(state=tk.DISABLED)
        btn_frame = tk.Frame(right)
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        self.lbl_json_status = tk.Label(btn_frame, text="")
        self.lbl_json_status.pack(side=tk.LEFT, padx=8)

        # status/footer
        self.label_status = tk.Label(root, text="Active: 0", fg="blue")
        self.label_status.pack(side=tk.BOTTOM, pady=6)

        # Start logger thread
        self.logger_thread = threading.Thread(target=logger.json_logger_task, daemon=False)
        self.logger_thread.start()

        # server process handle (if started from UI)
        self.server_proc = None
        self.server_lock = threading.Lock()

        # start periodic updates
        self._schedule_status_update()
        self._schedule_json_preview()

    def add_target_thread(self):
        self.target_counter += 1
        new_target = target.Target(target_id=f"T-{self.target_counter}")

        with config.targets_lock:
            config.active_targets.append(new_target)

        t = threading.Thread(target=target.target_thread_task, args=(new_target,), daemon=False)
        t.start()
        config.target_threads.append(t)

        self.update_status_label()
        print(f"-> Spawned Target {new_target.target_id} (vn={new_target.vn}, ve={new_target.ve}, vd={new_target.vd})")

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
            details = f"N={found.north}, E={found.east}, D={found.down}  |  vn={found.vn}, ve={found.ve}, vd={found.vd}"
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

    def _schedule_canvas_draw(self):
        try:
            self._draw_canvas()
        except Exception:
            pass
    # redraw at ~20 Hz for smoother animation
        self.root.after(50, self._schedule_canvas_draw)

    def _draw_canvas(self):
        # simple mapping: find bounds from active targets
        with config.targets_lock:
            items = list(config.active_targets)

        w = max(200, self.canvas.winfo_width() or 200)
        h = max(200, self.canvas.winfo_height() or 200)
        pad = self.canvas_padding

        # clear canvas each time (easier grid/axes management)
        self.canvas.delete("all")

        # compute bounds
        if items:
            norths = [t.north for t in items]
            easts = [t.east for t in items]
            min_n, max_n = min(norths), max(norths)
            min_e, max_e = min(easts), max(easts)
            # add small margin and ensure non-zero ranges
            rng_n = max(1.0, (max_n - min_n) or 1.0)
            rng_e = max(1.0, (max_e - min_e) or 1.0)
            # if single or near-single, expand view to show motion
            if rng_n < 50.0:
                min_n -= 25.0
                max_n += 25.0
                rng_n = max_n - min_n
            if rng_e < 50.0:
                min_e -= 25.0
                max_e += 25.0
                rng_e = max_e - min_e
        else:
            # default bounds
            min_n, max_n = -500.0, 500.0
            min_e, max_e = -500.0, 500.0
            rng_n = max_n - min_n
            rng_e = max_e - min_e

        # draw background grid and axes
        # outer border
        self.canvas.create_rectangle(pad, pad, w - pad, h - pad, outline="#cccccc", width=1)
        
        # grid lines (light gray dashed)
        grid_step = max(50.0, rng_e / 5.0)  # aim for ~5 divisions
        e = min_e
        while e <= max_e:
            x = pad + ((e - min_e) / rng_e) * (w - 2 * pad)
            self.canvas.create_line(x, pad, x, h - pad, fill="#e0e0e0", dash=(2, 2))
            e += grid_step
        
        grid_step = max(50.0, rng_n / 5.0)
        n = min_n
        while n <= max_n:
            y = pad + ((max_n - n) / rng_n) * (h - 2 * pad)
            self.canvas.create_line(pad, y, w - pad, y, fill="#e0e0e0", dash=(2, 2))
            n += grid_step
        
        # axis labels (cardinal directions)
        self.canvas.create_text(w - pad - 5, h - pad - 2, text="E", anchor=tk.SE, font=("Arial", 7, "bold"), fill="#333333")
        self.canvas.create_text(pad + 5, pad + 3, text="N", anchor=tk.NW, font=("Arial", 7, "bold"), fill="#333333")
        
        # center reference cross (if origin is visible)
        if rng_n > 100 and rng_e > 100:
            cx = pad + ((0.0 - min_e) / rng_e) * (w - 2 * pad) if min_e <= 0 <= max_e else None
            cy = pad + ((max_n - 0.0) / rng_n) * (h - 2 * pad) if min_n <= 0 <= max_n else None
            if cx is not None and pad <= cx <= w - pad:
                self.canvas.create_line(cx, pad, cx, h - pad, fill="#ffcccc", width=1, dash=(1, 2))
            if cy is not None and pad <= cy <= h - pad:
                self.canvas.create_line(pad, cy, w - pad, cy, fill="#ffcccc", width=1, dash=(1, 2))

        # clear target item id mappings (canvas was cleared, items will be recreated)
        self.canvas_items.clear()
        self.target_trails.clear()

        # clear and reuse items
        existing = set(self.canvas_items.keys())
        now_ids = set(t.target_id for t in items)

        # remove old canvas items (but since canvas.delete("all") was called, just clear the mapping)
        # items will be recreated below

        # draw each target
        for t in items:
            # map east->x, north->y (north up)
            x = pad + ((t.east - min_e) / rng_e) * (w - 2 * pad)
            y = pad + ((max_n - t.north) / rng_n) * (h - 2 * pad)
            # visualize down (z): map down -> circle radius and color
            # compute down bounds for visual scaling
            # (we compute per-loop to keep code simple; small cost)
            downs = [it.down for it in items] if items else [0.0]
            min_d, max_d = min(downs), max(downs)
            rng_d = max(1.0, (max_d - min_d) or 1.0)

            # normalized depth 0..1 (shallower -> 0, deeper -> 1)
            norm_d = max(0.0, min(1.0, (t.down - min_d) / rng_d))
            # radius between 4..14 px
            r = 4 + int(norm_d * 10)

            # color transition from blue (shallow) to red (deep)
            r_col = int(50 + norm_d * 200)
            g_col = int(80 - norm_d * 60)
            b_col = int(200 - norm_d * 200)
            color = f"#{r_col:02x}{g_col:02x}{b_col:02x}"

            # horizontal velocity line scaling
            scale_h = 60.0
            x2 = x + (t.ve / (rng_e or 1.0)) * scale_h
            y2 = y - (t.vn / (rng_n or 1.0)) * scale_h

            # vertical velocity indicator (small vertical line above/below circle)
            vscale = 6.0
            v_len = t.vd * vscale
            # clamp length to reasonable pixels
            v_len = max(-20.0, min(20.0, v_len))
            vx1, vy1 = x, y - r - 4
            vx2, vy2 = x, (y - r - 4) + v_len

            # record screen position into a short trail buffer
            tr = self.target_trails.get(t.target_id)
            if tr is None:
                tr = []
                self.target_trails[t.target_id] = tr
            tr.append((x, y))
            if len(tr) > self.trail_max:
                tr.pop(0)

            # draw or update circle + hv line + vv line + text + trail
            if t.target_id in self.canvas_items:
                existing = self.canvas_items[t.target_id]
                # handle older tuple shapes gracefully
                if len(existing) == 3:
                    o_circ, o_hline, o_text = existing
                    o_vline = self.canvas.create_line(vx1, vy1, vx2, vy2, fill="#000000")
                    o_trail = self.canvas.create_line(*sum(tr, ()), fill=color, width=2)
                    self.canvas_items[t.target_id] = (o_circ, o_hline, o_vline, o_text, o_trail)
                elif len(existing) == 4:
                    o_circ, o_hline, o_vline, o_text = existing
                    o_trail = self.canvas.create_line(*sum(tr, ()), fill=color, width=2)
                    self.canvas_items[t.target_id] = (o_circ, o_hline, o_vline, o_text, o_trail)
                else:
                    o_circ, o_hline, o_vline, o_text, o_trail = existing

                # update coords and style
                self.canvas.coords(o_circ, x - r, y - r, x + r, y + r)
                self.canvas.itemconfigure(o_circ, fill=color)
                self.canvas.coords(o_hline, x, y, x2, y2)
                self.canvas.coords(o_vline, vx1, vy1, vx2, vy2)
                # update trail polyline
                try:
                    pts = sum(tr, ())
                    if len(pts) >= 4:
                        self.canvas.coords(o_trail, *pts)
                        self.canvas.itemconfigure(o_trail, fill=color)
                except Exception:
                    pass
                # show id, speed and altitude
                speed = math.sqrt(t.vn * t.vn + t.ve * t.ve + t.vd * t.vd)
                self.canvas.coords(o_text, x + r + 2, y - r - 2)
                self.canvas.itemconfigure(o_text, text=f"{t.target_id} {speed:.1f}m/s D={t.down:.1f}m")
            else:
                circ = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="#1a1a1a", width=1)
                hline = self.canvas.create_line(x, y, x2, y2, fill="#666666", width=1)
                vline = self.canvas.create_line(vx1, vy1, vx2, vy2, fill="#000000", width=1)
                text = self.canvas.create_text(x + r + 2, y - r - 2, text=t.target_id, anchor=tk.NW, font=("Arial", 8, "bold"), fill="#000000")
                # create trail polyline (flatten coords)
                pts = sum(tr, ())
                trail = None
                if len(pts) >= 4:
                    trail = self.canvas.create_line(*pts, fill=color, width=1)
                self.canvas_items[t.target_id] = (circ, hline, vline, text, trail)

    def _schedule_json_preview(self):
        # update JSON preview every 1 second
        self.load_json_preview()
        self.root.after(1000, self._schedule_json_preview)

    def load_json_preview(self):
        """Read the latest JSON file and display it in the preview box."""
        try:
            path = config.JSON_FILENAME
            if not path or not os.path.exists(path):
                self._set_json_text("(no JSON file found)")
                self.lbl_json_status.config(text="No file")
                return

            mtime = os.path.getmtime(path)
            # quick read
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # pretty if possible
            try:
                parsed = json.loads(content)
                pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
            except Exception:
                pretty = content

            self._set_json_text(pretty)
            self.lbl_json_status.config(text=f"Updated: {time.strftime('%H:%M:%S', time.localtime(mtime))}")
        except Exception as e:
            self._set_json_text(f"Error reading JSON: {e}")
            self.lbl_json_status.config(text="Error")

    def _set_json_text(self, text: str):
        self.txt_json.config(state=tk.NORMAL)
        self.txt_json.delete("1.0", tk.END)
        self.txt_json.insert(tk.END, text)
        self.txt_json.config(state=tk.DISABLED)

    def on_closing(self):
        print("\nStopping all threads... please wait.")
        config.stop_threads_event.set()

        # first, stop all targets
        with config.targets_lock:
            config.active_targets.clear()

        for t in list(config.target_threads):
            t.join(timeout=1.0)

        if hasattr(self, "logger_thread"):
            self.logger_thread.join(timeout=2.0)

        # stop server if started
        with self.server_lock:
            if self.server_proc:
                try:
                    self.server_proc.terminate()
                    self.server_proc.wait(timeout=2.0)
                except Exception:
                    pass
                self.server_proc = None

        time.sleep(0.05)
        self.root.destroy()

    # ---------- New actions ----------
    def kill_all_targets(self):
        removed = target.kill_all_targets()
        print(f"Killed {removed} targets.")
        # also join threads
        for t in list(config.target_threads):
            t.join(timeout=0.2)
        self.update_status_label()

    def toggle_server(self):
        """Start or stop the local test server (server_local.py)."""
        with self.server_lock:
            if self.server_proc:
                # stop it
                try:
                    self.server_proc.terminate()
                    self.server_proc.wait(timeout=2.0)
                except Exception as e:
                    print(f"Error stopping server: {e}")
                self.server_proc = None
                self.btn_toggle_server.config(text="Start Server")
                print("Stopped local server from UI.")
                return

            # start server
            # use same python executable
            python_exe = sys.executable or "python"
            server_path = os.path.join(os.path.dirname(__file__), "server_local.py")
            try:
                # start without shell, detach so UI can still run
                self.server_proc = subprocess.Popen([python_exe, server_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.btn_toggle_server.config(text="Stop Server")
                print(f"Started local server (pid={self.server_proc.pid}) from UI.")
            except Exception as e:
                print(f"Failed to start server: {e}")

    def open_received_folder(self):
        # open the RandomTarget/received_json directory if exists, otherwise open project root
        try:
            received_dir = os.path.join(os.path.dirname(__file__), "received_json")
            if not os.path.exists(received_dir):
                os.makedirs(received_dir, exist_ok=True)
            # Windows: use os.startfile
            if sys.platform.startswith("win"):
                os.startfile(received_dir)
            else:
                # try xdg-open / open
                opener = "xdg-open" if sys.platform.startswith("linux") else "open"
                subprocess.Popen([opener, received_dir])
        except Exception as e:
            print(f"Unable to open folder: {e}")