import logging
import win32event
import win32serviceutil
import win32service
import servicemanager
import subprocess
import time
import os
import json
from pathlib import Path
import threading

APP_DIR = Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "AntiWebNSFW"
APP_DIR.mkdir(parents=True, exist_ok=True)  # Create folder if missing

log_path = APP_DIR / "service_debug.log"
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)
LOCK_STATE_PATH = APP_DIR / "lock_state.json"

OVERLAY_SCRIPT = os.path.join(os.path.dirname(__file__), "overlay_lock.py")
PYTHON_EXE = r"E:\\Yahya\\Anti_Nude\\venv311\\Scripts\\python\.exe"


class AntiNudeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AntiNudeService"
    _svc_display_name_ = "Anti Nude Detection and Lock Service"

    def __init__(self, args, init_for_debug=False):
        if not init_for_debug:
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        else:
            # debug mode - don't call base init or create Windows event
            self.stop_event = None

        self.overlay_proc = None

        # Setup logging (repeated call is safe but redundant)
        log_path = APP_DIR / "service_debug.log"
        logging.basicConfig(filename=log_path, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("Service init")

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.stop_overlay()
        servicemanager.LogInfoMsg("AntiNudeService - Stopped")
        logging.info("Service stopped")

    def SvcDoRun(self):
        try:
            logging.info("SvcDoRun entered")
            servicemanager.LogInfoMsg("AntiNudeService - Started")

            self.ReportServiceStatus(win32service.SERVICE_RUNNING)

            self.worker_thread = threading.Thread(target=self.main)
            self.worker_thread.daemon = True
            self.worker_thread.start()

            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

            logging.info("Service stop event received, cleaning up...")

            self.stop_overlay()

        except Exception as e:
            logging.error(f"Exception in SvcDoRun: {e}")
            servicemanager.LogErrorMsg(f"AntiNudeService exception: {e}")
            raise


    def main(self):
        while True:
            # Check for stop event every 2 seconds
            rc = win32event.WaitForSingleObject(self.stop_event, 2000)
            if rc == win32event.WAIT_OBJECT_0:
                logging.info("Stop event detected, exiting main loop")
                break

            try:
                locked_until = 0
                if LOCK_STATE_PATH.exists():
                    data = json.loads(LOCK_STATE_PATH.read_text())
                    locked_until = data.get("locked_until", 0)
                now = int(time.time())
                if locked_until > now:
                    if not self.overlay_proc or self.overlay_proc.poll() is not None:
                        logging.info("Lock active - starting overlay")
                        self.start_overlay()
                else:
                    if self.overlay_proc:
                        logging.info("Lock expired - stopping overlay")
                        self.stop_overlay()
            except Exception as e:
                logging.error(f"Exception in main loop: {e}")

    def start_overlay(self):
        try:
            self.overlay_proc = subprocess.Popen([PYTHON_EXE, OVERLAY_SCRIPT])
            logging.info("Overlay started")
        except Exception as e:
            logging.error(f"Failed to start overlay: {e}")

    def stop_overlay(self):
        try:
            if self.overlay_proc and self.overlay_proc.poll() is None:
                self.overlay_proc.terminate()
                self.overlay_proc.wait(timeout=5)
                logging.info("Overlay stopped")
        except Exception as e:
            logging.error(f"Failed to stop overlay: {e}")
        self.overlay_proc = None

    def debug(self):
        # Debug mode: run main loop in console with keyboard interrupt handling
        print("Starting debug mode loop. Press Ctrl+C to stop.")
        logging.info("Debug mode started")
        self.stop_event = None  # disable win32 stop event for debug mode
        try:
            while True:
                try:
                    locked_until = 0
                    if LOCK_STATE_PATH.exists():
                        data = json.loads(LOCK_STATE_PATH.read_text())
                        locked_until = data.get("locked_until", 0)
                    now = int(time.time())
                    if locked_until > now:
                        if not self.overlay_proc or self.overlay_proc.poll() is not None:
                            print("Lock active - starting overlay")
                            self.start_overlay()
                    else:
                        if self.overlay_proc:
                            print("Lock expired - stopping overlay")
                            self.stop_overlay()
                    print("Debug loop running...")
                    logging.info("Debug loop running")
                    time.sleep(2)
                except Exception as e:
                    print(f"Exception in debug loop: {e}")
                    logging.error(f"Exception in debug loop: {e}")
        except KeyboardInterrupt:
            print("Debug mode interrupted.")
            logging.info("Debug mode interrupted")
            self.stop_overlay()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        svc = AntiNudeService([], init_for_debug=True)
        svc.debug()
    else:
        win32serviceutil.HandleCommandLine(AntiNudeService)
