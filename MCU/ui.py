"""
Minimal Tk UI to poll /events and show network messages for MCU.
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import urllib.request
import json


class McuNetworkUI:
    def __init__(self, mcu_url='http://localhost:8003'):
        self.mcu_url = mcu_url
        self.root = tk.Tk()
        self.root.title('MCU Network Monitor')
        self.text = scrolledtext.ScrolledText(self.root, width=80, height=24)
        self.text.pack(fill=tk.BOTH, expand=True)
        self.polling = True
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _append(self, line):
        def _do():
            self.text.insert(tk.END, line)
            self.text.see(tk.END)
        self.root.after(0, _do)

    def _poll_loop(self):
        last = 0
        while self.polling:
            try:
                with urllib.request.urlopen(f"{self.mcu_url}/events", timeout=2.0) as resp:
                    body = resp.read().decode('utf-8')
                    data = json.loads(body) if body else {}
                evs = data.get('events', [])
                new = [e for e in evs if e.get('timestamp',0) > last]
                for e in new:
                    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.get('timestamp', time.time())))
                    self._append(f"[{ts}] {e.get('type').upper()} {e.get('command_id','')}\n")
                    last = max(last, e.get('timestamp', last))
            except Exception as ex:
                self._append(f"[ERROR] Poll: {ex}\n")
            time.sleep(1.0)

    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', self.stop)
        self.root.mainloop()

    def stop(self):
        self.polling = False
        self.root.quit()
