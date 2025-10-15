import keyboard
import ctypes
import time
import threading
import json
import os
from tkinter import Tk, Label
from pathlib import Path

# --- Configuration ---
# APP_DIR = Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "AntiWebNSFW"
# APP_DIR = Path(os.getenv("LOCALAPPDATA")) / "AntiWebNSFW"
# Use a data folder inside our project directory to avoid C: drive permissions
APP_DIR = Path(__file__).parent.resolve() / "data"
LOCK_STATE_PATH = APP_DIR / "lock_state.json"
START_DATE = 1754954400  # Placeholder for Aug 11, 2025
ONE_YEAR_SECONDS = 365 * 24 * 3600

# --- Win32 API Functions ---
user32 = ctypes.windll.user32
BlockInput = user32.BlockInput
SetCursorPos = user32.SetCursorPos

# A threading event to safely stop our cursor jail loop
stop_cursor_jail = threading.Event()

def cursor_jail_thread():
    """A function that will run in a separate thread to trap the mouse."""
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    center_x, center_y = screen_width // 2, screen_height // 2
    
    while not stop_cursor_jail.is_set():
        SetCursorPos(center_x, center_y)
        time.sleep(0.001) # Loop very quickly but efficiently

def read_lock():
    try:
        if LOCK_STATE_PATH.exists() and LOCK_STATE_PATH.stat().st_size > 0:
            return json.loads(LOCK_STATE_PATH.read_text())
    except Exception:
        pass
    return {"locked_until": 0}

def show_overlay(duration_seconds):
    # --- Start All Locking Mechanisms ---
    
    # 1. Start the cursor jail in a background thread
    jail_thread = threading.Thread(target=cursor_jail_thread, daemon=True)
    jail_thread.start()

    # 2. Block all keyboard events using the keyboard library's hook
    keyboard_hook = keyboard.hook(lambda e: None, suppress=True)

    # 3. Engage the primary BlockInput lock for both mouse and keyboard
    BlockInput(True)

    # --- Setup the Tkinter GUI Overlay ---
    root = Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.config(cursor="none")
    root.configure(bg="black")
    
    Label(
        root, text="Device Locked: Content Detected",
        font=("Segoe UI", 40, "bold"), fg="red", bg="black"
    ).pack(expand=False, pady=(150, 20))
    
    countdown_label = Label(root, text="", font=("Segoe UI", 30), fg="white", bg="black")
    countdown_label.pack(expand=True)

    end_time = time.time() + duration_seconds

    def update_countdown():
        remaining = end_time - time.time()
        if remaining > 0:
            mins, secs = divmod(int(remaining), 60)
            hours, mins = divmod(mins, 60)
            countdown_label.config(text=f"Time remaining: {hours:02d}:{mins:02d}:{secs:02d}")
            root.after(1000, update_countdown)
        else:
            # --- Time is up: Release all locks ---
            BlockInput(False)            # 1. Release primary lock
            keyboard.unhook(keyboard_hook) # 2. Release keyboard hook
            stop_cursor_jail.set()     # 3. Signal cursor jail thread to stop
            root.destroy()

    update_countdown()
    root.mainloop()

def main():
    now = int(time.time())
    if now > START_DATE + ONE_YEAR_SECONDS:
        return # Exit if expired

    state = read_lock()
    locked_until = state.get("locked_until", 0)

    if now < locked_until:
        remaining = locked_until - now
        show_overlay(remaining)

if __name__ == "__main__":
    main()