import keyboard
import ctypes
import time
import threading
import logging
from pathlib import Path
from pynput import mouse

def on_click(x, y, button, pressed):
    # Suppress all mouse clicks by returning False
    return False


user32 = ctypes.WinDLL('user32', use_last_error=True)

user32.BlockInput(True)
# --- Setup Logging ---
APP_DIR = Path("C:/ProgramData/AntiWebNSFW")
APP_DIR.mkdir(parents=True, exist_ok=True)
log_path = APP_DIR / "hybrid_blocker_test.log"
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# A threading event to safely stop our cursor jail loop
stop_cursor_jail = threading.Event()

def cursor_jail_thread():
    """A function that will run in a separate thread to trap the mouse."""
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    center_x, center_y = screen_width, screen_height
    
    logging.info("Cursor jail thread started. Trapping mouse.")
    while not stop_cursor_jail.is_set():
        user32.SetCursorPos(center_x, center_y)
        time.sleep(0.000000000000000001) # Loop very quickly to make the mouse feel stuck
    logging.info("Cursor jail thread stopped.")



# --- Main Test Logic ---
logging.info("--- Hybrid Blocker Test Starting ---")
print("--- Hybrid Blocker Test ---")
print("Starting test. Your keyboard AND mouse should be blocked for 15 seconds.")

# 1. Start the cursor jail in a background thread
jail_thread = threading.Thread(target=cursor_jail_thread, daemon=True)
jail_thread.start()

# 2. Block all keyboard events using the keyboard library's hook
# This hook intercepts all key events and the callback (lambda) does nothing.
# 'suppress=True' ensures the keystrokes don't get passed to other applications.
keyboard_hook = keyboard.hook(lambda e: None, suppress=True)
mouse_listener = mouse.Listener(on_click=on_click, suppress=True)
mouse_listener.start()
try:
    # Wait for 15 seconds while the block is active
    time.sleep(15)
    time.sleep(10)

finally:
    # --- Cleanup: Always restore input ---
    logging.info("Stopping block...")
    
    # 1. Unhook the keyboard to restore typing
    keyboard.unhook(keyboard_hook)
    
    # 2. Signal the cursor jail thread to stop
    stop_cursor_jail.set()
    jail_thread.join(timeout=1) # Wait a moment for the thread to exit
    mouse_listener.stop()
    user32.BlockInput(False)

    print("INPUT RESTORED. Test complete.")
    logging.info("INPUT RESTORED. Test complete.")