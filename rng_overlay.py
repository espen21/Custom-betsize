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
    def __init__(self, hwnd: int, update_ms: int = 5000):
        self.hwnd = hwnd
        self.update_ms = update_ms
        self.running = True

        # Var overlayn hamnar relativt bordets övre vänstra hörn
        self.offset_x = 20
        self.offset_y = 20

        self.visible = True

        # Tk overlay
        self.root = tk.Tk()
        self.root.overrideredirect(True)          # ingen ram
        self.root.attributes("-topmost", True)    # bara relevant när vi visar den
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

        self.root.mainloop()

    def set_rng(self):
        random.seed(datetime.now().timestamp())
        self.label.config(text=str(random.randint(0, 100)))

    def auto_rng(self):
        if not self.running:
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
        while self.running:
            try:
                # Om bordet stängs
                if not win32gui.IsWindow(self.hwnd):
                    self.running = False
                    self.root.destroy()
                    return

                fg = win32gui.GetForegroundWindow()

                # Aktivt fönster = bordet (eller child till bordet)
                is_active_table = (fg == self.hwnd) or (win32gui.GetParent(fg) == self.hwnd)

                if is_active_table:
                    self._show()

                    # Följ bordets position
                    x1, y1, x2, y2 = win32gui.GetWindowRect(self.hwnd)
                    x = x1 + self.offset_x
                    y = y1 + self.offset_y
                    self.root.geometry(f"+{x}+{y}")

                else:
                    self._hide()

            except:
                pass

            time.sleep(0.02)


class RNGManager:
    def __init__(self):
        self.active_hwnds = set()
        self.run()

    def run(self):
        while True:
            titles = gw.getAllTitles()

            for title in titles:
                if title_matches(title):
                    hwnd = win32gui.FindWindow(None, title)
                    if hwnd and hwnd not in self.active_hwnds:
                        self.active_hwnds.add(hwnd)
                        threading.Thread(
                            target=RNGOverlay,
                            args=(hwnd,),
                            daemon=True
                        ).start()

            time.sleep(0.5)


if __name__ == "__main__":
    RNGManager()
