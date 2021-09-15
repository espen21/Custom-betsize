import win32con,win32api,win32gui
import pygetwindow as gw
import time
import keyboard
while True:
    titles = gw.getAllTitles()
    for title in titles:
        if "NL" in title:
            print(title)
            hwnd = win32gui.FindWindow(None,title)
            print(win32gui.GetWindowRect(hwnd))
            print(win32gui.GetCursorPos())
            x_adjusted = 727
            y_adjusted = 579
            lParam = win32api.MAKELONG(x_adjusted, y_adjusted)
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            c=win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            print(c)
            a = "2141"
            keyboard.write(a)
    time.sleep(2)