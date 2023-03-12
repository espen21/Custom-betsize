from ast import keyword
import tkinter
import threading
from tkinter.constants import FALSE, LEFT, TRUE
from turtle import color
import win32gui,win32api,win32con
import time
import pygetwindow as gw
import pyautogui
import pyperclip
import random
from tkinter import Tk, messagebox as mb
from datetime import datetime 
class PkrWindow:
    def __init__(self,table_name,size_list,rng_yes):
        self.table_name = table_name
        self.is_Unibet = False
        if "Texas Hold'em - NL" in self.table_name: self.is_Unibet = True
        self.rng_yes = rng_yes
        self.hwnd = win32gui.FindWindow(None,self.table_name)
        print(win32gui.GetWindowRect(self.hwnd))

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
        self.manual_move = False
        self.manual_x = 0
        self.manual_y = 0
        self.manual_toggled = False
        if self.is_Unibet:
            self.betbox_x =  387
            self.betbox_y = 310
            self.halfpot_x = 366
            self.halfpot_y = 437
        else: #svs
            self.betbox_x =  1223
            self.betbox_y = 862
            self.halfpot_x = 798
            self.halfpot_y = 841 #funkar inte för max size på bord
        self.reset = False
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

    def get_betbox_num(self):
        self.adjust_pos_click_betbox()
        lParam_reset = win32api.MAKELONG(self.x_adjusted_betbox, self.y_adjusted_betbox-40)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam_reset) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam_reset)
        time.sleep(0.01)
        lParam = win32api.MAKELONG(self.x_adjusted_betbox, self.y_adjusted_betbox)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        
        time.sleep(0.01)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        time.sleep(0.01)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        win32gui.SetForegroundWindow(self.hwnd)
        time.sleep(0.01)

        pyautogui.hotkey('ctrl', 'c')
        
        time.sleep(.01)  # ctrl-c is usually very fast but your program may execute faster
        str_bet_box= pyperclip.paste()
        
        return str_bet_box
    def get_pot_size(self):
        #self.press_half_pot() #buggig maunelltklick på 1/2
        str_bet_box = self.get_betbox_num()
        try:
            pot_size = float(str_bet_box)*2.0
        except:
            pot_size = 0
        return pot_size

    def is_table_fg(self):
        fg_table_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        """point = win32gui.GetCursorPos()
        handle = win32gui.WindowFromPoint(point)
        cursor_table_name = win32gui.GetWindowText(handle)"""
        
        try:
            if "table-" in self.table_name:
                if "table-" in fg_table_name :
                    self.root.attributes("-topmost",True)
                else:
                    self.root.attributes("-topmost",False)
            else:
            
                if  fg_table_name == self.table_name :
                    self.root.attributes("-topmost",True)
               
                else:
                    self.root.attributes("-topmost",False)
        except Exception as e:
                print(e)

    def is_table_under_cursor(self):
        point = win32gui.GetCursorPos()
        handle = win32gui.WindowFromPoint(point)
        name = win32gui.GetWindowText(handle)
    def press_half_pot(self):
        self.adjusted_half_pot_x,self.adjusted_half_pot_y = self.adjust_pos_click(self.halfpot_x,self.halfpot_y)
        print(self.adjusted_half_pot_x,self.adjusted_half_pot_y,"adjusted")
        lParam = win32api.MAKELONG(self.adjusted_half_pot_x, self.adjusted_half_pot_y)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
    def write_postflop_size(self,in_size):
        in_size = in_size.replace("%","")
        in_size = float(in_size)/100
        potsize =self.get_pot_size()
      
        bet_size_unfilt = float(potsize)*float(in_size)
        bet_size_filtered = self.remove_dec_nums(bet_size_unfilt)
        self.adjust_pos_click_betbox()
            
        try:
           

            self.adjust_pos_click_betbox()
            lParam_reset = win32api.MAKELONG(self.x_adjusted_betbox, self.y_adjusted_betbox-40)
            lParam = win32api.MAKELONG(self.x_adjusted_betbox, self.y_adjusted_betbox)
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam_reset) 
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam_reset)
            time.sleep(0.01)
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            time.sleep(0.01)
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            time.sleep(0.01)
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
           
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.01)
            pyautogui.typewrite(bet_size_filtered)
        except Exception as e:
            print(e)
            tkinter.messagebox.showinfo("Error custom size","To use custom size(CU) , u need to input  5.5 to raise to 5.5bb")
    def set_move(self,bo):
        self.manual_move = bo
        self.manual_toggled = True
    def set_reset_move(self,bo):
        self.manual_toggled = bo
    def set_button_pos(self):
        while True:
            self.is_table_fg() #döljer knapparna om det inte är fokus
            try:
                t_pos = win32gui.GetWindowRect(self.hwnd)
            except Exception as e:
                self.root.destroy()
            if self.manual_move == True:
                self.manual_x = self.root.winfo_x()
                self.manual_y = self.root.winfo_y()
                self.a_x = abs(self.manual_x)- abs(t_pos[0]) 
                self.a_y = abs(self.manual_y)-abs(t_pos[1])

                self.manual_toggled = True
            
            if (self.manual_toggled  and self.manual_move== False) and (self.table_geo != t_pos or self.start):
                move_x = self.a_x + t_pos[0]
                move_y = self.a_y + t_pos[1]
                if move_x>= 0 :move_x = "+"+str(move_x)
                else :move_x =str(move_x)
                if move_y>0: move_y = "+" + str(move_y)
                else: move_y =str(move_y)
                move = move_x+move_y
                self.root.geometry(move)
                
            if (self.table_geo != t_pos or self.start) and self.manual_toggled == False:
                self.table_geo = t_pos
                if t_pos[0] >= 0: width_adjust = abs(t_pos[2])-abs(t_pos[0])
                else: width_adjust = (abs(t_pos[2])+(t_pos[0]))
                width_adjust = width_adjust/2
                move_x = t_pos[0]+8
                if move_x >= 0:  move_x = int(t_pos[0]+width_adjust)
                else: move_x = int(t_pos[0]-width_adjust)
                if move_x >= 0: move_x = move_x-200
                else: move_x = move_x -1850
                move_y = t_pos[1]
                if move_y >= 0: move_y = t_pos[1]+5
                else: move_y = t_pos[1]-5
                if move_x>= 0 :move_x = "+"+str(move_x)
                else :move_x =str(move_x)
                if move_y>0: move_y = "+" + str(move_y)
                else: move_y =str(move_y)
                move = move_x+move_y
                self.root.geometry(move)
                self.start = False
            time.sleep(0.01)
        
    def write_custom(self):
        
        in_size=self.entry1.get()
        in_size = in_size.replace(",",".")
        if "%" in in_size:
            self.write_postflop_size(in_size)
        else:    
            try:
                in_size=float(in_size)
                self.write_Size(in_size)

            except:
                tkinter.messagebox.showinfo("Error custom size, example write 5.5 to raise to 5.5bb or 10% to bet 10%, of pot ")

    def create_betbutton(self):
        self.entry1 = tkinter.Entry(self.root,bg="black",fg="white",width=4)
        self.entry1.pack(in_=self.top,side=LEFT)
        self.be = tkinter.Button(self.root,text="CU",bg="black",fg="white",command= self.write_custom)
        self.be.pack(in_=self.top,side=LEFT)
        for size in self.bet_list:
            if "=" in size.lower():
                size = size.split("=")[1]
                self.entry1.insert(0,size)
            elif "%" not in size:
                button = tkinter.Button(self.root,text=str(size),bg="black",fg="white",command= lambda in_size = size: self.write_Size(in_size))
                button.pack(in_=self.top,side=LEFT)
                self.button_list.append(button)
            else:
                button = tkinter.Button(self.root,text=str(size),bg="black",fg="white",command= lambda in_size = size: self.write_postflop_size(in_size))
                button.pack(in_=self.top,side=LEFT)
                self.button_list.append(button)
        if self.rng_yes == True:
            self.rng()
            #self.rng_button = tkinter.Button(self.root,text="RNG",bg="black",fg="white",command= self.rng)
            #self.rng_button.pack(in_=self.top,side=LEFT)
            self.label = tkinter.Label(self.root,text=self.rng_num,bg="black",fg="magenta",width=4)
            self.label.pack(in_=self.top,side=LEFT)
            self.label.bind("<Button-1>",lambda e:self.rng(clicked= True))
        
    def rng(self,clicked =False):
        random.seed(datetime.now())
        self.rng_num= str( random.randint(0,100))
        try:
            
            self.label.configure(text = self.rng_num)

        except:
            pass
        if not clicked :self.root.after(5000,self.rng) # update value every 5 sec
    def adjust_pos_click(self,x,y):
        try:
            self.table_geo =win32gui.GetWindowRect(self.hwnd)
        except Exception as e:
            #print(e)
            self.root.destroy()
        betbox_x = x
        betbox_y = y 
        default_w = 1359    
        default_h = 1057
        if self.is_Unibet:
            default_w = 640    
            default_h = 390
        t_x = self.table_geo[0]
        t_y = self.table_geo[1]
        t_w = self.table_geo[2]-t_x
        t_h = self.table_geo[3]-t_y
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
    def destroy_sub_root(self):
        self.root.attributes("-topmost",True)
    def adjust_pos_click_betbox(self):
        self.x_adjusted_betbox,self.y_adjusted_betbox = self.adjust_pos_click(self.betbox_x,self.betbox_y)
    
    ##not used
    def get_last_active_poker_table(self):
        while True:
            
            if "NL Hold" in win32gui.GetWindowText(win32gui.GetForegroundWindow()) :
                self.table_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
                for s in self.table_name.split("-"):
                    if "/" in s:
                        self.big_blind = float(s.split("/")[1])
                self.label.configure(text="BB:"+str(self.big_blind)+"kr")
                self.hwnd = win32gui.FindWindow(None,self.table_name)
                self.adjust_pos_click_betbox()
            elif  "table" in win32gui.GetWindowText(win32gui.GetForegroundWindow()):
                self.table_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
                for s in self.table_name.split("-"):
                    if "/" in s:
                        self.big_blind = float(s.split(" ")[0].split("/")[1])
                self.label.configure(text="BB:"+str(self.big_blind)+"kr")
                self.hwnd = win32gui.FindWindow(None,self.table_name)
          
            time.sleep(0.01)
    
    def get_big_blind(self):
        self.table_name = win32gui.GetWindowText(self.hwnd)
        if "NL Hold'em" in self.table_name or "PL Omaha" in self.table_name:
            for s in self.table_name.split("-"):
                if "/" in s:
                    self.big_blind = float(s.split("/")[1].replace(",","."))
        elif "table-" in self.table_name:
            for s in self.table_name.split("-"):
                if "/" in s:
                    self.big_blind = float(s.split(" ")[1].split("/")[1].replace(",","."))
        elif self.is_Unibet:
            #split_name = self.table_name.split(" ")
            #str_level = split_name[3].replace("NL","")
            #self.big_blind = round(float(str_level)*0.01,2)
            self.big_blind = 1.0
        
    def remove_dec_bb_size(self,in_size):
        in_size = float(str(in_size).replace(",","."))

        if "table-" in self.table_name:
            real_size = int(self.big_blind*in_size)
            
        else:  
            real_size = round(self.big_blind*in_size,2)
        real_size = str(real_size)
        
        return real_size
    def remove_dec_nums(self,in_size):
        real_size = str(in_size)
        if real_size  == "0" : return real_size
        real_size = round(float(real_size),2)
        real_size = str(real_size)
        
        return real_size
    def write_Size(self,in_size):
        try:
            self.get_big_blind()
            real_size = self.remove_dec_bb_size(in_size)
            print(self.big_blind)
            self.adjust_pos_click_betbox()
            
            lParam = win32api.MAKELONG(self.x_adjusted_betbox, self.y_adjusted_betbox)
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
            win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            time.sleep(0.01)
            if self.is_Unibet == False:
                win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
                win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
                time.sleep(0.01)
                win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam) 
                win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
                
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.01)

            pyautogui.typewrite(real_size)
        except Exception as e:
            print(e)
            tkinter.messagebox.showinfo("Error custom size","To use custom size(CU) , u need to input  5.5 to raise to 5.5bb")
           
class SizeHandler:
    def __init__(self):
        self.bet_sizes = []
        self.path_saved_sizes = "saved_sizes.txt"
        self.root = tkinter.Tk()
        self.root.title("SVS sizes")
        self.ca = tkinter.Canvas(self.root, width = 400, height = 300)
        self.ca.pack()
        
        self.entry1 = tkinter.Entry(self.root,width=50)
        self.entry1.setvar() 
        self.read_config()
        self.move_yes = tkinter.BooleanVar()
        self.rng_yes = tkinter.BooleanVar()
        self.ca.create_window(200, 140, window=self.entry1)
        self.create_button()
        
        self.size_objs = []
        self.root.mainloop()
    def is_foreground_table_poker(self):
        fg_table = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        if "table-" in fg_table or "NL Hold'em" in fg_table or "Omaha" in fg_table or "tk" in fg_table:            
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
        self.bet_sizes=[]
        self.write_saved_sizes()
        unfiltred_sizes = self.entry1.get().split("-")
        if unfiltred_sizes[0]!="" :
        
            for s in unfiltred_sizes:
                s = s.replace(",",".")
                self.bet_sizes.append((s))
          
    def create_button(self):
        
        self.start_button2 = tkinter.Button(text="Start",command=self.start_button)
        self.exit_button = tkinter.Button(text="Quit",command=self.close)
        #button1 = tkinter.Button(text='Set sizes', command=self.set_sizes)
        #self.ca.create_window(150, 180, window=button1)
        self.rng_check = tkinter.Checkbutton( text='RNG',variable=self.rng_yes, onvalue=True, offvalue=False)
        self.ca.create_window(150,180,window=self.rng_check)
        self.ca.create_window(200,180,window=self.start_button2)
        self.ca.create_window(240,180,window=self.exit_button)
    
    def add_toolbar_to_move(self):
        move_bool = self.move_yes.get()
        for o in self.size_objs:
            o[1].root.overrideredirect(not move_bool)
            o[1].set_move(move_bool)
    
    def reset_move(self):
        
        for o in self.size_objs:
            
            o[1].set_reset_move(False)
    def refind_tables(self):
        for s in self.size_objs:
            s[1].destroy_sub_root()
      

    def start_button(self):
        self.rng_yes = self.rng_yes.get()
        try:
            self.start_button2.destroy()#tar bort startknapp
            self.set_sizes()
            self.thread = threading.Thread(target=self.find_tables,daemon=True)
            self.thread.start()
            self.move_check = tkinter.Checkbutton( text='Move',variable=self.move_yes, onvalue=True, offvalue=False,command=self.add_toolbar_to_move)
            self.ca.create_window(100,180,window=self.move_check)
            self.reset_move_button = tkinter.Button(text="Reset Move",command=self.reset_move)
            self.ca.create_window(100,220,window=self.reset_move_button)
            self.reset_move_button = tkinter.Button(text="On top",command=self.refind_tables)
            self.ca.create_window(100,260,window=self.reset_move_button)
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
            #print(win32gui.GetCursorPos())
            for t in titles:
                if ("- NL Hold'em -" in t or "table-" in t or "- PL Omaha -" in t or "Texas Hold'em - NL" in t) and self.table_name_exist(t)==False : 
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
            
            time.sleep(0.01)
    def close(self):
        self.root.destroy()
        quit()
    
if __name__ == "__main__":
    SizeHandler()
    #pkr = PkrWindow()