import win32gui,win32api,win32con
import time
import keyboard
def send_click(handle,press):
    win32gui.SetActiveWindow(handle)
    if press: keyboard.press("ctrl+left")
    else: keyboard.release("ctrl+left")
    print(win32gui.GetWindowText(handle),press)
state_left = win32api.GetKeyState(0x06)  # Left button down = 0 or 1. Button up = -127 or -128


while True:
    point = win32gui.GetCursorPos()
    handle = win32gui.WindowFromPoint(point)
    name = win32gui.GetWindowText(handle)
    a = win32api.GetKeyState(0x06)
    if a != state_left:  # Button state changed
        state_left = a
        if a < 0 and ("- PL Omaha -" in name or "NLH" in name or "- NL Hold" in name or "Rush & Cash" in name or "Spin & Gold" in name):
            send_click(handle,True)
        else:
            send_click(handle,False)
    time.sleep(0.1)