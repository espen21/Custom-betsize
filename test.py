import win32api
import win32process
import win32con
import ctypes
from ReadWriteMemory import ReadWriteMemory

import pygetwindow as gw
titles = gw.getAllTitles()
name = ""
for t in titles:
    if "Ada 2589" in t:
        name = t
print(name)
# Open the process
import win32gui
hwnd = win32gui.FindWindow(None, name)
threadid,pid = win32process.GetWindowThreadProcessId(hwnd)
print(pid)
rwm = ReadWriteMemory()

process = rwm.get_process_by_id(pid)
process.open()
print (process)
print(process.__dict__)
health_pointer = process.get_pointer(0x11096F28)
pot = process.read(health_pointer)
print(pot)