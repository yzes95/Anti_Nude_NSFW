import ctypes
import time
import keyboard

# Load user32 DLL
user32 = ctypes.WinDLL('user32', use_last_error=True)

def block_input(block: bool):
    # BlockInput blocks mouse and keyboard at a very low level (admin required)
    # Returns nonzero if success
    result = user32.BlockInput(block)
    if not result:
        err = ctypes.get_last_error()
        print(f"BlockInput failed with error code: {err}")
    return result



if __name__ == "__main__":
    print("You have 5 seconds to prepare")
    
    time.sleep(5)
    
    print("Blocking all keyboard and mouse input for 20 seconds...")
    success = block_input(True)
    if not success:
        print("Failed to block input. Are you running as Administrator?")
    else:
        time.sleep(20)  # Block duration
        block_input(False)
        print("Input unblocked.")


# import ctypes

# def is_admin():
#     try:
#         return ctypes.windll.shell32.IsUserAnAdmin()
#     except:
#         return False

# print("Is admin:", is_admin())

# import ctypes
# from ctypes import wintypes
# import sys
# user32 = ctypes.windll.user32
# kernel32 = ctypes.windll.kernel32

# WH_MOUSE_LL = 14

# LowLevelMouseProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

# def dummy_proc(nCode, wParam, lParam):
#     return user32.CallNextHookEx(None, nCode, wParam, lParam)



# mouse_callback = LowLevelMouseProc(dummy_proc)

# GetModuleHandleW = kernel32.GetModuleHandleW

# python_module_handle = GetModuleHandleW(ctypes.create_unicode_buffer("python{}.dll".format(sys.version_info.major)))
# print(f"Python module handle: {python_module_handle}")

# hook_id = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_callback, python_module_handle, 0)

# # hook_id = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_callback, kernel32.GetModuleHandleW(None), 0)

# if hook_id:
#     print("Hook installed successfully!")
#     user32.UnhookWindowsHookEx(hook_id)
# else:
#     print("Failed to install hook.")
