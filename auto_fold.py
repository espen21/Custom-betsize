import win32gui,win32api,win32con
import time
import keyboard
def send_click(handle):
    win32gui.SetActiveWindow(handle)
    keyboard.press_and_release("ctrl+left")
    
    print("pressed ")    
state_left = win32api.GetKeyState(0x06)  # Left button down = 0 or 1. Button up = -127 or -128


while True:
    point = win32gui.GetCursorPos()
    handle = win32gui.WindowFromPoint(point)
    name = win32gui.GetWindowText(handle)
    a = win32api.GetKeyState(0x06)
    if a != state_left:  # Button state changed
        state_left = a
        if a < 0:
          
            pass
        elif "- PL Omaha -" in name or "NLH" in name or "- NL Hold" in name or "Rush & Cash" in name:
            send_click(handle)
    time.sleep(0.1)