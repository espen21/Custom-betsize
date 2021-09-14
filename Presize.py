import tkinter
import threading
import win32gui
import time

class PkrWindow:
    def __init__(self,table_name):
        self.table_name = table_name
        self.hwnd = win32gui.FindWindow(None, table_name )  
        self.big_blind = None
        self.custom_size = 0
        self.bb3vsSB = 9.5 #keybind shift+1 
        self.threeSB = 9.75 #keybind shift+2
        self.threesbLarge = 10.25 #keybind shift+3
        self.threebetBB = 11.25#keybind shift+4
        self.fourBetOP = 23.25