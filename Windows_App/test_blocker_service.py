import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os

# IMPORTANT: Use the full, absolute path to the EXE you created
BLOCKER_EXE_PATH = r"E:\Yahya\Anti_Nude\dist\test.exe"

class TestBlockerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TestBlockerService"
    _svc_display_name_ = "Test Input Blocker Service"
    _svc_description_ = "Launches the test.exe to test permissions."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.proc = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        
        # Launch the test EXE
        self.proc = subprocess.Popen([BLOCKER_EXE_PATH])
        
        # The service will just wait here. The EXE will run for 10s and exit.
        # This service will stop itself after 20 seconds for cleanup.
        win32event.WaitForSingleObject(self.stop_event, 20000)

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(TestBlockerService)