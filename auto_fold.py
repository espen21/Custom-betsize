
import win32gui,win32api,win32con
import time
import keyboard
import pyautogui
def send_click_fold(handle,press):
    win32gui.SetActiveWindow(handle)
    if press: keyboard.press("ctrl+left")
    else: keyboard.release("ctrl+left")
    print(win32gui.GetWindowText(handle),press)
def get_big_blind(name):
        if "NL Hold'em" in name or "PL Omaha" in name:
            for s in name.split("-"):
                if "/" in s:
                    return float(s.split("/")[1].replace(",","."))
        elif "table-" in name:
            for s in name.split("-"):
                if "/" in s:
                    return float(s.split(" ")[1].split("/")[1].replace(",","."))
def send_raise(handle,press,name):
    big_blind = get_big_blind(name)
    win32gui.SetActiveWindow(handle)
    
    if press: keyboard.press("ctrl+right")
    else: keyboard.release("ctrl+right")
    print(win32gui.GetWindowText(handle),press)

def write_Size(self,in_size):
    try:
        self.get_big_blind()
        real_size = self.remove_dec_bb_size(in_size)

        self.adjust_pos_click_betbox()
        
        lParam = win32api.MAKELONG(self.x_adjusted_betbox, self.y_adjusted_betbox)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        time.sleep(0.05)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        time.sleep(0.05)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)

        win32gui.SetForegroundWindow(self.hwnd)
        time.sleep(0.05)

        pyautogui.typewrite(real_size)
    except Exception as e:
        print(e)
state_left = win32api.GetKeyState(0x06)  # m4 button down = 0 or 1. Button up = -127 or -128
state_right = win32api.GetKeyState(0x05)  # m4 button down = 0 or 1. Button up = -127 or -128

print("Started autofold, mouse4 = fold, mouse5 = raise")
while True:
    try:
        point = win32gui.GetCursorPos()
        handle = win32gui.WindowFromPoint(point)
        name = win32gui.GetWindowText(handle)
        name_stuff = "- PL Omaha -" in name or "NLH" in name or "Hold'em -" in name or "table-" in name or "Rush & Cash" in name or "Spin & Gold" in name or "PLO "in name
        #if name_stuff: win32gui.SetForegroundWindow(handle)
        temp_left= win32api.GetKeyState(0x06)
        temp_right = win32api.GetKeyState(0x05)  #
        if temp_left!= state_left:  # Button state changed
            state_left = temp_left
            if temp_left< 0 and name_stuff:
                send_click_fold(handle,True)
            else:
                send_click_fold(handle,False)
        if temp_right!= state_right:  # Button state changed
            state_right = temp_right
            if temp_right< 0 and name_stuff:
                send_raise(handle,True,name)
            else:
                send_raise(handle,False,name)
    except Exception as e:
        print(e)

    time.sleep(0.05)