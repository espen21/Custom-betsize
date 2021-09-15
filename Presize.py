import tkinter
import threading
import win32gui,win32api,win32con
import time
import pyperclip
class PkrWindow:
    def __init__(self):
        self.window_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        if "NL Hold" in self.window_name: self.table_name = self.window_name
        self.big_blind = float(self.table_name.split("-")[3].split("/")[1])
        self.custom_size = 0
        self.bb3vsSB = 9.5 #keybind shift+1 
        self.threeSB = 9.75 #keybind shift+2
        self.threesbLarge = 10.25 #keybind shift+3
        self.threebetBB = 11.25#keybind shift+4
        self.fourBetOP = 23.25
        self.bet_list = [self.bb3vsSB,self.threeSB,self.threesbLarge,self.threebetBB,self.fourBetOP]
        
        self.button_list = []
        self.root = tkinter.Tk()
        self.create_betbutton()
        self.thread = threading.Thread(target=self.get_last_active_poker_table,daemon=True)
        self.thread.start()

        self.root.mainloop()
        
    def create_betbutton(self):
        for size in self.bet_list:
            button = tkinter.Button(self.root,text=str(size),command= lambda in_size = size: self.write_Size(in_size))
            button.pack()
            self.button_list.append(button)

    def adjust_click_pos(self):
        betbox_x =  1227
        betbox_y = 910
        default_w = 1364
        default_h = 1050
        t_x = self.table_geo[0]
        t_y = self.table_geo[1]
        t_w = self.table_geo[2]-t_x
        t_h = self.table_geo[3]-t_y
        adjuster_x = ((t_w)/default_w) 
        adjuster_y = ((t_h)/default_h) 
        self.x_adjusted =  adjuster_x*(betbox_x)
        self.y_adjusted = adjuster_y*(betbox_y )
        self.x_adjusted = int(self.x_adjusted)
        self.y_adjusted = int(self.y_adjusted)

    def get_last_active_poker_table(self):
        while True:
            if "NL Hold" in win32gui.GetWindowText(win32gui.GetForegroundWindow()):
                self.table_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            print(self.table_name,win32gui.GetWindowText(win32gui.GetForegroundWindow()))
            time.sleep(1)
    def write_Size(self,in_size):

        print(self.window_name,self.table_name)
        self.big_blind = float(self.table_name.split("-")[3].split("/")[1])
        real_size = self.big_blind*in_size
        real_size = str(real_size)
        real_size = real_size.split(".")
        try:
            real_size = real_size[0]+"."+real_size[1][0]+real_size[1][1]
        except:
            real_size =  real_size[0]+"."+real_size[1]
        pyperclip.copy(real_size)

if __name__ == "__main__":
    while True:
        unfiltered = win32gui.GetWindowText (win32gui.GetForegroundWindow())
        if "NL Hold" in unfiltered:
            pkr = PkrWindow()