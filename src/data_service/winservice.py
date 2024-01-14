import pythoncom
import win32serviceutil
import win32service
import win32event
import servicemanager
import win32api
import socket
import sys
from data_service.dataApp import app
import config
import logging
import tempfile
import os


class RealtimeImagingDBService(win32serviceutil.ServiceFramework):
    _svc_name_ = "RealtimeImagingDBService"
    _svc_display_name_ = "Image-X Real-time Imaging DB"
    _svc_description_ = "This service uses RESTful API to serve "\
                        "information about Clinical data "

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def log(self, msg):
        servicemanager.LogInfoMsg(str(msg))        

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        logging.info("realtimeImagingDB service stopped")

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        try:
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, 
                        servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ''))
            self.main()
        except Exception as ex:
            # self.log('Exception while starting service')
            logging.warn("caught an exception while trying to start the service - " + str(ex))
            self.SvcStop()

    def main(self):
        rc = None
        while rc != win32event.WAIT_OBJECT_0:
            logging.info("RealtimeImagingDB Starting service")
            app.run (host=config.LISTENING_HOST, 
                    port=config.LISTENING_PORT, 
                    debug=False, use_reloader=False)
            rc = win32event.WaitForSingleObject(self.hWaitStop, 24*60*60*1000)
        
        logging.info("Exiting the RealtimeImagingDBService::main()\n")


if __name__ == '__main__':
    logfilePath = os.path.join(tempfile.gettempdir(), config.LOGFILE_NAME)
    print("logging to ", logfilePath)
    logging.basicConfig(filename=logfilePath)

    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(RealtimeImagingDBService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32api.SetConsoleCtrlHandler(lambda x: True, True)
        win32serviceutil.HandleCommandLine(RealtimeImagingDBService)
