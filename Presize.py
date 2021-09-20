import tkinter
import threading
from tkinter.constants import LEFT, TRUE
import win32gui,win32api,win32con
import time
import pygetwindow as gw
import pyautogui
class PkrWindow:
    def __init__(self,table_name):
        self.table_name = table_name
        self.hwnd = win32gui.FindWindow(None,self.table_name)
        self.table_geo =win32gui.GetWindowRect(self.hwnd)
        self.first = True
        try:
            self.big_blind = self.get_big_blind()
        except:
            self.big_blind = 10.0
        self.custom_size = 0
        self.t3bip=7.5 
        self.bb3vsSB = 9.5 #keybind shift+1 
        self.threeSB = 9.75 #keybind shift+2
        self.threesbLarge = 10.25 #keybind shift+3
        self.threebetBB = 11.25#keybind shift+4
        self.fourBetOP = 23.25
        self.bet_list = [self.t3bip,self.bb3vsSB,self.threeSB,self.threesbLarge,self.threebetBB,self.fourBetOP]
        self.start = True
        self.button_list = []
    def start_size(self):
        
        self.root = tkinter.Tk()
        self.root.attributes("-topmost",True)
        self.root.overrideredirect(True)
        self.top = tkinter.Frame(self.root)
        self.top.pack()
        self.create_betbutton()
        self.thread = threading.Thread(target=self.set_button_pos,daemon=True)
        self.thread.start()
        self.root.mainloop()
    def set_button_pos(self):
        while True:
            try:
                t_pos = win32gui.GetWindowRect(self.hwnd)

            except Exception as e:
                self.root.destroy()
            if self.table_geo != t_pos or self.start:
                self.table_geo = t_pos
                width_adjust = abs(t_pos[2])-abs(t_pos[0])
                width_adjust = width_adjust/2
                move_x = int(t_pos[0]+width_adjust)
                move_x = move_x-150
                move_y = t_pos[1]+5
                move_x = "+"+str(move_x)
                move_y = "+" + str(move_y)
                move = move_x+move_y
                self.root.geometry(move)
                self.start = False
            time.sleep(0.2)

    def create_betbutton(self):
        for size in self.bet_list:
            button = tkinter.Button(self.root,text=str(size),bg="black",fg="white",command= lambda in_size = size: self.write_Size(in_size))
            button.pack(in_=self.top,side=LEFT)
            self.button_list.append(button)

    def adjust_click_pos(self):
        try:
            self.table_geo =win32gui.GetWindowRect(self.hwnd)
        except Exception as e:
            #print(e)
            self.root.destroy()
        betbox_x =  1223
        betbox_y = 862#868
        default_w = 1359    
        default_h = 1057
        t_x = abs(self.table_geo[0])
        t_y = abs(self.table_geo[1])
        t_w = abs(self.table_geo[2])-abs(t_x)
        t_h = abs(self.table_geo[3])-abs(t_y)
        adjuster_x = ((t_w)/default_w) 
        adjuster_y = ((t_h)/default_h)
        self.x_adjusted =  adjuster_x*(betbox_x)
        self.y_adjusted = adjuster_y*(betbox_y )
        self.x_adjusted = int(self.x_adjusted)
        if t_w>470:
        
            self.y_adjusted = int(self.y_adjusted)
        else:
            self.x_adjusted = 435
            self.y_adjusted = 300
    def get_last_active_poker_table(self):
        while True:
            
            if "NL Hold" in win32gui.GetWindowText(win32gui.GetForegroundWindow()) :
                self.table_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
                for s in self.table_name.split("-"):
                    if "/" in s:
                        self.big_blind = float(s.split("/")[1])
                self.label.configure(text="BB:"+str(self.big_blind)+"kr")
                self.hwnd = win32gui.FindWindow(None,self.table_name)
                self.adjust_click_pos()
            elif  "table" in win32gui.GetWindowText(win32gui.GetForegroundWindow()):
                self.table_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
                for s in self.table_name.split("-"):
                    if "/" in s:
                        self.big_blind = float(s.split(" ")[0].split("/")[1])
                self.label.configure(text="BB:"+str(self.big_blind)+"kr")
                self.hwnd = win32gui.FindWindow(None,self.table_name)
          
            time.sleep(0.5)
    
    def get_big_blind(self):
        if "NL Hold'em" in self.table_name:
            for s in self.table_name.split("-"):
                if "/" in s:
                    self.big_blind = float(s.split("/")[1])
        elif "-table" in self.table_name:
            for s in self.table_name.split("-"):
                if "/" in s:
                    self.big_blind = float(s.split(" ")[0].split("/")[1])
    def write_Size(self,in_size):
        self.get_big_blind()
        self.adjust_click_pos()
        real_size = self.big_blind*in_size
        real_size = str(real_size)
        real_size = real_size.split(".")
        if real_size[1] == "0":
            real_size = real_size[0]
        else:
            try:

                real_size = real_size[0]+"."+real_size[1][0]+real_size[1][1]

            except:
                real_size =  real_size[0]+"."+real_size[1]
        
        lParam = win32api.MAKELONG(self.x_adjusted, self.y_adjusted)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        time.sleep(0.1)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        time.sleep(0.1)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)

        win32gui.SetForegroundWindow(self.hwnd)
        time.sleep(0.1)

        pyautogui.typewrite(real_size)
        
        #pyperclip.copy(real_size)

class SizeHandler:
    def __init__(self):
        self.root = tkinter.Tk()
        self.create_button()
      
        self.size_objs = []
        self.root.mainloop()
        
    def create_button(self):
      
        start_button = tkinter.Button(self.root,text="Start",command=self.start_button)
        start_button.pack()
        exit_button = tkinter.Button(self.root,text="Quit",command=self.close)
        exit_button.pack()
    
    def start_button(self):
        self.thread = threading.Thread(target=self.find_tables,daemon=True)
        self.thread.start()
    def table_name_exist(self,table_name):
        for t in self.size_objs:
            if table_name in t[0]:
                return True
        return False
    def check_table_closed(self,titles):
        for i in range (len(self.size_objs)):
            if self.size_objs[i][0] not in titles:
                self.size_objs.pop(i)
            
    def find_tables(self):
        while True:
            titles = gw.getAllTitles()
            for t in titles:
                if ("NL Hold'em" in t or "-table" in t) and self.table_name_exist(t)==False : 
                    pkr=PkrWindow(table_name=t)
                    self.pkr_thread = threading.Thread(target=pkr.start_size,daemon=True)
                    self.pkr_thread.start()
                    self.size_objs.append([t,pkr])
                #print("hello",len(self.size_objs)) debug
            self.check_table_closed(titles)
            time.sleep(1)
    def close(self):
        self.root.destroy()
        quit()
if __name__ == "__main__":
    SizeHandler()
    #pkr = PkrWindow()