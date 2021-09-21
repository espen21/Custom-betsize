import tkinter
import threading
from tkinter.constants import LEFT, TRUE
import win32gui,win32api,win32con
import time
import pygetwindow as gw
import pyautogui
import random
from tkinter import Tk, messagebox as mb
from datetime import datetime 
class PkrWindow:
    def __init__(self,table_name,size_list,rng_yes):
        self.table_name = table_name
        self.rng_yes = rng_yes
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
        self.bet_list = size_list
        self.start = True
        self.button_list = []
        self.top_most = True
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
    def write_custom(self):
        in_size=self.entry1.get()
       
        try:
            in_size=float(in_size)
            self.write_Size(in_size)

        except:
            tkinter.messagebox.showinfo("Error custom size","To use custom size(CU) , u need to input for example (use dot not comma)  5.5 to raise to 5.5bb")

    def create_betbutton(self):
        self.entry1 = tkinter.Entry(self.root,bg="black",fg="white",width=4)
        self.entry1.pack(in_=self.top,side=LEFT)
        self.be = tkinter.Button(self.root,text="CU",bg="black",fg="white",command= self.write_custom)
        self.be.pack(in_=self.top,side=LEFT)
        for size in self.bet_list:
            button = tkinter.Button(self.root,text=str(size),bg="black",fg="white",command= lambda in_size = size: self.write_Size(in_size))
            button.pack(in_=self.top,side=LEFT)
            self.button_list.append(button)
        if self.rng_yes == True:
            self.rng()
            self.rng_button = tkinter.Button(self.root,text="RNG",bg="black",fg="white",command= self.rng)
            self.rng_button.pack(in_=self.top,side=LEFT)
            self.label = tkinter.Label(self.root,text=self.rng_num,bg="black",fg="white",width=4)
            self.label.pack(in_=self.top,side=LEFT)
    def rng(self):
        random.seed(datetime.now())
        self.rng_num= str( random.randint(0,100))
        try:
            self.label.configure(text = self.rng_num)
        except:
            pass
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
        elif "table-" in self.table_name:
            for s in self.table_name.split("-"):
                if "/" in s:
                    self.big_blind = float(s.split(" ")[1].split("/")[1])
    
    def write_Size(self,in_size):
        try:
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
            tkinter.messagebox.showinfo("Error custom size","To use custom size(CU) , u need to input  5.5 to raise to 5.5bb")
           
class SizeHandler:
    def __init__(self):
        self.bet_sizes = []
        self.path_saved_sizes = "saved_sizes.txt"
        self.root = tkinter.Tk()

        self.ca = tkinter.Canvas(self.root, width = 400, height = 300)
        self.ca.pack()
        
        self.entry1 = tkinter.Entry(self.root,width=50) 
        self.read_config()
        self.rng_yes = tkinter.BooleanVar()
        self.ca.create_window(200, 140, window=self.entry1)
        self.create_button()
        
        self.size_objs = []
        self.root.mainloop()
    def is_foreground_table_poker(self):
        fg_table = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        if "table-" in fg_table or "NL Hold'em" in fg_table or "Omaha" in fg_table:
            for o in self.size_objs:
                if o[1].top_most ==False:
                    o[1].root.attributes("-topmost",True)
                    o[1].top_most = True
        else:
            for o in self.size_objs:
                if o[1].top_most == True:
                    o[1].root.attributes("-topmost",False)
                    o[1].top_most = False
    def read_config(self):
        try:
            with open(self.path_saved_sizes,'r') as f:
                txt = f.read()
                self.entry1.insert(0,txt)
        except Exception as e:
            self.entry1.insert(0,"")
    def write_saved_sizes(self):
        with open(self.path_saved_sizes,'w', encoding="utf-8") as f:
            f.write(self.entry1.get())
    def set_sizes(self):
        self.write_saved_sizes()
        unfiltred_sizes = self.entry1.get().split(",")
        if unfiltred_sizes[0]!="" :
        
            for s in unfiltred_sizes:
                self.bet_sizes.append(float(s))
          
    def create_button(self):
        
        self.start_button2 = tkinter.Button(text="Start",command=self.start_button)
        self.exit_button = tkinter.Button(text="Quit",command=self.close)
        #button1 = tkinter.Button(text='Set sizes', command=self.set_sizes)
        #self.ca.create_window(150, 180, window=button1)
        self.rng_check = tkinter.Checkbutton( text='RNG',variable=self.rng_yes, onvalue=True, offvalue=False)
        self.ca.create_window(150,180,window=self.rng_check)
        self.ca.create_window(200,180,window=self.start_button2)
        self.ca.create_window(240,180,window=self.exit_button)

    def start_button(self):
        self.rng_yes = self.rng_yes.get()
        try:
            self.start_button2.destroy()
            self.set_sizes()
            self.thread = threading.Thread(target=self.find_tables,daemon=True)
            self.thread.start()
            
        except Exception as e:
            tkinter.messagebox.showinfo("Error set sizes","U can leave this empty. To set sizes input for example 5.5,7.5 and 5.5bb and 7.5bb will be set as sizes ")
            print(e)
            
    def table_name_exist(self,table_name):
        for t in self.size_objs:
            if  t[0] in table_name :
                return True
        return False
    def is_table_closed(self,sizeobj,titles):
        for t in titles:
            if sizeobj in t:
                return False
        return True
    def check_table_closed(self,titles):
        for i in range (len(self.size_objs)):
            try:
                if self.is_table_closed(self.size_objs[i][0],titles):
                    a = self.size_objs.pop(i)
            except:
                pass
    def find_tables(self):
        while True:
            titles = gw.getAllTitles()
            for t in titles:
                if ("NL Hold'em" in t or "table-" in t) and self.table_name_exist(t)==False : 
                    t_copy = t.split("-")
                    try:
                        t_copy = t_copy[0]+"-"+t_copy[1]+"-"+t_copy[2]
                    except:
                        t_copy = t
                    pkr=PkrWindow(table_name=t,size_list=self.bet_sizes,rng_yes= self.rng_yes)
                    self.pkr_thread = threading.Thread(target=pkr.start_size,daemon=True)
                    self.pkr_thread.start()
                    self.size_objs.append([t_copy,pkr])
                #print("hello",len(self.size_objs)) debug
            self.check_table_closed(titles)
            try:
                self.is_foreground_table_poker()
            except:
                pass
            time.sleep(1)
    def close(self):
        self.root.destroy()
        quit()
if __name__ == "__main__":
    SizeHandler()
    #pkr = PkrWindow()