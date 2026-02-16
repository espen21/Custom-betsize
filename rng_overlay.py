import tkinter as tk
import threading
import time
import random
from datetime import datetime

import win32gui
import pygetwindow as gw


# Behåller exakt dina titlar
TABLE_TITLES = (
    "| NL Hold'em |",
    "| PL Omaha |",
    "Texas Hold'em - NL"
)


def title_matches(title: str) -> bool:
    return any(t in title for t in TABLE_TITLES)


class RNGOverlay:
    def __init__(self, hwnd: int, stop_event: threading.Event, update_ms: int = 5000):
        self.hwnd = hwnd
        self.update_ms = update_ms
        self.stop_event = stop_event
        self.running = True

        # Var overlayn hamnar relativt bordets övre vänstra hörn
        self.offset_x = 270
        self.offset_y = 0

        self.visible = True

        # Tk overlay
        self.root = tk.Tk()
        self.root.overrideredirect(True)          # ingen ram
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")

        self.label = tk.Label(
            self.root,
            text="--",
            font=("Consolas", 14, "bold"),
            fg="magenta",
            bg="black",
            padx=8,
            pady=4
        )
        self.label.pack()

        # Klick -> ny RNG direkt
        self.label.bind("<Button-1>", lambda e: self.set_rng())

        # Startvärde
        self.set_rng()

        # Starta följ-loop i tråd
        threading.Thread(target=self.loop, daemon=True).start()

        # Auto-uppdatera RNG
        self.root.after(self.update_ms, self.auto_rng)

        self.root.protocol("WM_DELETE_WINDOW", self.request_stop)

        self.root.mainloop()

    def request_stop(self):
        self.running = False
        try:
            self.root.destroy()
        except:
            pass

    def set_rng(self):
        random.seed(datetime.now().timestamp())
        self.label.config(text=str(random.randint(0, 100)))

    def auto_rng(self):
        if not self.running or self.stop_event.is_set():
            return
        self.set_rng()
        self.root.after(self.update_ms, self.auto_rng)

    def _show(self):
        if self.visible:
            return
        self.visible = True
        self.root.attributes("-topmost", True)
        self.root.deiconify()

    def _hide(self):
        if not self.visible:
            return
        self.visible = False
        self.root.attributes("-topmost", False)
        self.root.withdraw()

    def loop(self):
        while self.running and not self.stop_event.is_set():
            try:
                if not win32gui.IsWindow(self.hwnd):
                    self.running = False
                    self.root.after(0, self.root.destroy)
                    return

                fg = win32gui.GetForegroundWindow()
                is_active_table = (fg == self.hwnd) or (win32gui.GetParent(fg) == self.hwnd)

                if is_active_table:
                    self._show()
                    x1, y1, x2, y2 = win32gui.GetWindowRect(self.hwnd)
                    x = x1 + self.offset_x
                    y = y1 + self.offset_y
                    self.root.geometry(f"+{x}+{y}")
                else:
                    self._hide()

            except:
                pass

            time.sleep(0.02)

        self.running = False
        try:
            self.root.after(0, self.root.destroy)
        except:
            pass


class RNGManager:
    def __init__(self, stop_event: threading.Event):
        self.stop_event = stop_event
        self.active_hwnds = set()

    def run(self):
        while not self.stop_event.is_set():
            try:
                titles = gw.getAllTitles()

                for title in titles:
                    if self.stop_event.is_set():
                        break

                    if title and title_matches(title):
                        hwnd = win32gui.FindWindow(None, title)
                        if hwnd and hwnd not in self.active_hwnds:
                            self.active_hwnds.add(hwnd)
                            threading.Thread(
                                target=RNGOverlay,
                                args=(hwnd, self.stop_event),
                                daemon=True
                            ).start()

                time.sleep(0.5)
            except:
                time.sleep(0.5)


class ControlGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RNG Overlay Controller")

        self.manager_thread = None
        self.stop_event = threading.Event()
        self.running = False

        self.status_var = tk.StringVar(value="Status: Stoppad")

        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack()

        tk.Label(frame, text="RNG Overlay", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(frame, textvariable=self.status_var).pack(anchor="w", pady=(6, 10))

        btns = tk.Frame(frame)
        btns.pack(fill="x")

        self.start_btn = tk.Button(btns, text="Start", width=10, command=self.start)
        self.start_btn.pack(side="left")

        self.stop_btn = tk.Button(btns, text="Stop", width=10, command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))

        tk.Button(frame, text="Quit", command=self.quit).pack(anchor="e", pady=(12, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        # 🔥 Auto-start varje gång programmet körs (ingen config)
        self.start()

        self.root.mainloop()

    def start(self):
        if self.running:
            return

        self.stop_event = threading.Event()
        mgr = RNGManager(self.stop_event)

        self.manager_thread = threading.Thread(target=mgr.run, daemon=True)
        self.manager_thread.start()

        self.running = True
        self.status_var.set("Status: Körs")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def stop(self):
        if not self.running:
            return

        self.stop_event.set()
        self.running = False
        self.status_var.set("Status: Stoppad (stänger overlays...)")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

        self.root.after(800, lambda: self.status_var.set("Status: Stoppad"))

    def quit(self):
        try:
            self.stop_event.set()
        except:
            pass
        self.root.destroy()


if __name__ == "__main__":
    ControlGUI()
