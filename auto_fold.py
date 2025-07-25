
import win32gui,win32api,win32con
import time
import keyboard
import pyautogui
import pygetwindow as gw
def send_click_fold(handle,press):
    win32gui.SetActiveWindow(handle)
    keyboard.press_and_release("F1")
    
def adjust_pos_click(x,y,handle,name):
        table_geo =win32gui.GetWindowRect(handle)
        
        betbox_x = x
        betbox_y = y 
       
        default_w = 640    
        default_h = 390
        if "| NL Hold'em |" in name or  "| PL Omaha |" in name:
            default_w = 557    
            default_h = 395
        t_x = table_geo[0]
        t_y = table_geo[1]
        t_w = table_geo[2]-t_x
        t_h = table_geo[3]-t_y
        #if t_w>557:
         #   betbox_y = betbox_y-18
         #   betbox_x =  betbox_x +10
        adjuster_x = ((t_w)/default_w) 
        adjuster_y = ((t_h)/default_h)
        x_adjusted =  adjuster_x*(betbox_x)
        y_adjusted = adjuster_y*(betbox_y )
        x_adjusted = int(x_adjusted)
        y_adjusted = int(y_adjusted)
        return x_adjusted,y_adjusted

def set_rfi_size(handle,name):
    try:
        rfi_size_bb = "2.3"
        if "Omaha" in win32gui.GetWindowText(handle): rfi_size_bb ='100' 
        betbox_x =  387
        betbox_y = 310
        if "| NL Hold'em |" in name or  "| PL Omaha |" in name:
            betbox_x =  388
            betbox_y = 862
        x_adjusted_betbox,y_adjusted_betbox= adjust_pos_click(betbox_x,betbox_y,handle,name)
        
        lParam = win32api.MAKELONG(x_adjusted_betbox, y_adjusted_betbox)
        win32gui.SendMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(handle, win32con.WM_LBUTTONUP, 0, lParam)
        time.sleep(0.01)
        if "| NL Hold'em |" in name or  "| PL Omaha |" in name:
            
            win32gui.SendMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
            win32gui.SendMessage(handle, win32con.WM_LBUTTONUP, 0, lParam)
            time.sleep(0.01)
            win32gui.SendMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
            win32gui.SendMessage(handle, win32con.WM_LBUTTONUP, 0, lParam)
            
        win32gui.SetForegroundWindow(handle)
        time.sleep(0.01)

        pyautogui.typewrite(rfi_size_bb)
    except Exception as e:
        print(e)
def send_unibet_fold(handle):
   
    win32gui.SetActiveWindow(handle)
    halfpot_x = 225
    fold_btn_y = 340
    x_adjust,y_adjust = adjust_pos_click(halfpot_x,fold_btn_y,handle,name)
    lParam = win32api.MAKELONG(x_adjust, y_adjust)
    win32gui.SendMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
    win32gui.SendMessage(handle, win32con.WM_LBUTTONUP, 0, lParam)
    time.sleep(0.05)

    win32gui.SetForegroundWindow(handle)

def unibet_fold2(handle):
    win32gui.SetActiveWindow(handle)
    
    pyautogui.click(button='right')     

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


state_left = win32api.GetKeyState(0x06)  # m4 button down = 0 or 1. Button up = -127 or -128
state_right = win32api.GetKeyState(0x05)  # m4 button down = 0 or 1. Button up = -127 or -128

print("Started autofold, mouse4 = fold, mouse5 = raise, works for Unibet and SVS,\n Press [Ctrl] +[P] to turn on/off lift table")
lift_table = True  # poppar upp fönstret över mouseover
def check_svsx2(titles):
    count=0
    str_svs = "Svenska Spel Poker"
    for t in titles:
        if count >=2: return True
        if t == str_svs:
            count+=1 
    return False 
while True:
    try:
        
        point = win32gui.GetCursorPos()
        handle = win32gui.WindowFromPoint(point)
        name = win32gui.GetWindowText(handle)
        titles = gw.getAllTitles()
      
        name_stuff = ("| PL Omaha |" in name or "NLH" in name or "| NL Hold'em |" in name or "table-" in name or "Rush & Cash" in name or "Spin & Gold" in name or 
                      "PLO "in name or "Texas Hold'em - NL" in name or "Omaha -" in name or "(" in name)
        if keyboard.is_pressed("ctrl+p"): 
            lift_table = not lift_table
            print("Lift table is ",lift_table)
            time.sleep(0.5)
        if name_stuff  and lift_table and win32gui.GetForegroundWindow() != handle and check_svsx2(titles) is False:
            win32gui.SetForegroundWindow(handle)
            
        temp_left= win32api.GetKeyState(0x06)
        temp_right = win32api.GetKeyState(0x05)  
        if temp_left!= state_left:  # Button state changed
            state_left = temp_left
            if  name_stuff:
                if "| NL Hold'em |" in name or  "| PL Omaha |" in name : #svs
                    send_click_fold(handle,True)

            
                elif "Texas Hold'em - NL" in name or "Omaha -" in name or "(" in name: #unibet
                    unibet_fold2(handle)
                    
                
        if temp_right!= state_right:  # Button state changed
            state_right = temp_right
            if temp_right< 0 and name_stuff:
                
                if "Texas Hold'em - NL" in name or "Omaha -" in name or "| NL Hold'em |" in name or  "| PL Omaha |" in name or "(" in name :
                    set_rfi_size(handle,name)
                    
                else:
                    pass
                   # send_raise(handle,True,name)
            else:
                if "Texas Hold'em - NL" in name or "Omaha -" in name:
                    set_rfi_size(handle,name)
                

                else:
                    pass
                    #send_raise(handle,True,name)
    except Exception as e:
        print(e)

    time.sleep(0.05)