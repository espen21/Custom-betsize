import win32gui, win32api, win32con
import time
import keyboard
import pyautogui
import pygetwindow as gw

# --------------------
# CLICK HELPERS
# --------------------

def adjust_pos_click(x, y, handle, name):
    table_geo = win32gui.GetWindowRect(handle)

    default_w = 640
    default_h = 390
    if "| NL Hold'em |" in name or "| PL Omaha |" in name:
        default_w = 557
        default_h = 395

    t_x, t_y = table_geo[0], table_geo[1]
    t_w = table_geo[2] - t_x
    t_h = table_geo[3] - t_y

    adjuster_x = t_w / default_w
    adjuster_y = t_h / default_h

    x_adjusted = int(adjuster_x * x)
    y_adjusted = int(adjuster_y * y)

    return x_adjusted, y_adjusted


def unibet_fold(handle):
    win32gui.SetForegroundWindow(handle)
    print("FOLD (right click)")
    pyautogui.click(button="right")


def set_rfi_size(handle, name):
    try:
        rfi_size_bb = "2.3"
        if "Omaha" in win32gui.GetWindowText(handle):
            rfi_size_bb = "100"

        betbox_x = 387
        betbox_y = 310

        if "| NL Hold'em |" in name or "| PL Omaha |" in name:
            betbox_x = 388
            betbox_y = 862

        x_adj, y_adj = adjust_pos_click(betbox_x, betbox_y, handle, name)
        lParam = win32api.MAKELONG(x_adj, y_adj)

        for _ in range(3):
            win32gui.SendMessage(handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
            win32gui.SendMessage(handle, win32con.WM_LBUTTONUP, 0, lParam)
            time.sleep(0.01)

        win32gui.SetForegroundWindow(handle)
        time.sleep(0.01)
        pyautogui.typewrite(rfi_size_bb)
    except Exception as e:
        print("RFI error:", e)


def check_svsx2(titles):
    count = 0
    str_svs = "Svenska Spel Poker"
    for t in titles:
        if t == str_svs:
            count += 1
        if count >= 2:
            return True
    return False


# --------------------
# MAIN LOOP
# --------------------

print("Started autofold with SAME-TABLE protection")
print("M4 = fold ONLY if released on SAME table")
print("M5 = RFI ONLY if released on SAME table")
print("[Ctrl]+[P] toggles auto-lift")

lift_table = True

M4 = 0x06
M5 = 0x05

prev_m4 = win32api.GetKeyState(M4)
prev_m5 = win32api.GetKeyState(M5)

m4_down_handle = None
m5_down_handle = None

while True:
    try:
        point = win32gui.GetCursorPos()
        handle = win32gui.WindowFromPoint(point)
        name = win32gui.GetWindowText(handle)
        titles = gw.getAllTitles()

        name_stuff = (
            "| PL Omaha |" in name or
            "NLH" in name or
            "| NL Hold'em |" in name or
            "table-" in name or
            "Rush & Cash" in name or
            "Spin & Gold" in name or
            "PLO " in name or
            "Texas Hold'em - NL" in name or
            "Omaha -" in name or
            "(" in name
        )

        if keyboard.is_pressed("ctrl+p"):
            lift_table = not lift_table
            print("Lift table:", lift_table)
            time.sleep(0.5)

        if (
            name_stuff
            and lift_table
            and win32gui.GetForegroundWindow() != handle
            and not check_svsx2(titles)
        ):
            win32gui.SetForegroundWindow(handle)

        # ----------------------------
        # M4 (fold) — DOWN = store table
        # ----------------------------
        curr_m4 = win32api.GetKeyState(M4)

        # M4 pressed down
        if curr_m4 < 0 and prev_m4 >= 0:
            if name_stuff:
                m4_down_handle = handle   # store the table
                # print("M4 DOWN on table:", win32gui.GetWindowText(handle))

        # M4 released
        if curr_m4 >= 0 and prev_m4 < 0:
            if handle == m4_down_handle and name_stuff:
                print("M4 RELEASE on SAME TABLE → FOLD")
                unibet_fold(handle)
            # reset
            m4_down_handle = None

        prev_m4 = curr_m4

        # ----------------------------
        # M5 (RFI) — DOWN = store table
        # ----------------------------
        curr_m5 = win32api.GetKeyState(M5)

        # M5 pressed down
        if curr_m5 < 0 and prev_m5 >= 0:
            if name_stuff:
                m5_down_handle = handle

        # M5 released
        if curr_m5 >= 0 and prev_m5 < 0:
            if handle == m5_down_handle and name_stuff:
                print("M5 RELEASE on SAME TABLE → RFI size")
                set_rfi_size(handle, name)
            m5_down_handle = None

        prev_m5 = curr_m5

    except Exception as e:
        print("Main loop error:", e)

    time.sleep(0.01)
