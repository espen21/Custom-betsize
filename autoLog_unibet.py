import pyautogui
import time
import pygetwindow as gw
import win32gui
# Give some time to switch to the desired window
def set_unibet_lobby_active():
    titles = gw.getAllTitles()
    for title in titles:
        if ("Unibet Poker v" in title):
            handle =gw.getWindowsWithTitle(title)[0]
            win32gui.SetForegroundWindow(handle._hWnd)
            break

set_unibet_lobby_active()

# The message you want to write
u_name = "esbram162"
mail= "hotmail.com"
password = "extra3K5!"
# Type the message
time.sleep(0.1)

pyautogui.write(u_name)
pyautogui.press('@') 
pyautogui.write(mail)

time.sleep(0.05)
pyautogui.press('tab')
pyautogui.write(password)
time.sleep(0.05)

# Press 'Enter' to send the message
#pyautogui.press('enter')


