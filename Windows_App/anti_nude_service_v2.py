import logging
import win32event
import win32serviceutil
import win32service
import servicemanager
import subprocess
import time
import os
import json
import sys
from pathlib import Path

# --- Configuration ---
APP_DIR = Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "AntiWebNSFW"
APP_DIR.mkdir(parents=True, exist_ok=True)

log_path = APP_DIR / "service_debug.log"
logging.basicConfig(
    handlers=[
        logging.FileHandler(log_path, 'w', 'utf-8'),
        logging.StreamHandler() # Also print to console for easy debugging
    ],
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

LOCK_STATE_PATH = APP_DIR / "lock_state.json"
OVERLAY_SCRIPT = os.path.abspath("overlay_lock.py") 
PYTHON_EXE = r"E:\Yahya\Anti_Nude\venv311\Scripts\python.exe"

class AntiNudeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AntiNudeService"
    _svc_display_name_ = "Anti Nude Detection and Lock Service"
    _svc_description_ = "Monitors for NSFW content and locks the device."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.overlay_proc = None
        logging.info("Service __init__ complete.")

    def SvcStop(self):
        logging.info("Service stopping...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.stop_overlay()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        logging.info("Service stopped.")

    def SvcDoRun(self):
        logging.info("Service starting...")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self.main()

    def main(self):
        logging.info("Entering main service loop.")
        while True:
            # Check for a stop signal from the Service Manager
            wait_result = win32event.WaitForSingleObject(self.stop_event, 2000)
            if wait_result == win32event.WAIT_OBJECT_0:
                break # Stop signal received

            locked_until = 0
            try:
                if LOCK_STATE_PATH.exists() and LOCK_STATE_PATH.stat().st_size > 0:
                    data = json.loads(LOCK_STATE_PATH.read_text())
                    locked_until = data.get("locked_until", 0)
            except Exception as e:
                logging.error(f"Failed to read or parse lock state: {e}")
                locked_until = 0

            now = int(time.time())
            if locked_until > now:
                if not self.overlay_proc or self.overlay_proc.poll() is not None:
                    logging.info("Lock is active. Starting overlay process.")
                    self.start_overlay()
            else:
                if self.overlay_proc:
                    logging.info("Lock has expired. Stopping overlay process.")
                    self.stop_overlay()

    def start_overlay(self):
        try:
            self.overlay_proc = subprocess.Popen([PYTHON_EXE, OVERLAY_SCRIPT])
            logging.info(f"Overlay process started with PID: {self.overlay_proc.pid}")
        except Exception as e:
            logging.error(f"Failed to start overlay process: {e}")

    def stop_overlay(self):
        if self.overlay_proc and self.overlay_proc.poll() is None:
            try:
                logging.info(f"Terminating overlay process PID: {self.overlay_proc.pid}")
                self.overlay_proc.terminate()
                self.overlay_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.warning("Overlay process did not terminate gracefully, killing.")
                self.overlay_proc.kill()
            except Exception as e:
                logging.error(f"Error while stopping overlay: {e}")
        self.overlay_proc = None

# --- New Debug Function ---
def run_debug_mode():
    """Function to run the service logic without installing it, for testing."""
    print("Running in debug mode. Press Ctrl+C to stop.")
    logging.info("Running in debug mode.")
    
    # Create a dummy object that mimics the service class for debugging
    class ServiceRunner:
        def __init__(self):
            # We need a stop event for the main loop to use
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.overlay_proc = None

        # Copy the methods from the actual service class
        main = AntiNudeService.main
        start_overlay = AntiNudeService.start_overlay
        stop_overlay = AntiNudeService.stop_overlay

    runner = ServiceRunner()
    try:
        runner.main()
    except KeyboardInterrupt:
        print("\nDebug mode stopped by user.")
        logging.info("Debug mode stopped by user.")
        runner.stop_overlay()

# --- Updated Main Execution Block ---
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'debug':
        run_debug_mode()
    else:
        win32serviceutil.HandleCommandLine(AntiNudeService)