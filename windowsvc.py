from sys import modules, executable
import os.path
import win32api
import winerror
import win32service
import win32serviceutil
import servicemanager
import application

class WindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "testsvc"
    _svc_display_name_ = "Test Service"
    _svc_description_ = "Test Python service with HTTP server in it."
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.__app = application.Application();

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.__app.stop()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.__app.run();
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )

    @classmethod
    def __CurrentState(cls):
        state = None
        try:
            state = win32serviceutil.QueryServiceStatus(cls._svc_name_)[1]
        except win32api.error as details:
            if details.winerror not in [winerror.ERROR_SERVICE_DOES_NOT_EXIST, winerror.ERROR_INVALID_NAME]:
                raise
        return state;

    @classmethod
    def Install(cls):
        state = cls.__CurrentState();
        if state is not None:
            print("Service %s installed already." % cls._svc_name_)
            return
        
        try:
            modulePath=modules[cls.__module__].__file__
        except AttributeError:
            modulePath=executable
        classString = os.path.splitext(os.path.abspath(modulePath))[0] + '.' + cls.__name__;
        
        win32serviceutil.InstallService(
            pythonClassString = classString,
            serviceName       = cls._svc_name_,
            displayName       = cls._svc_display_name_ or cls._svc_name_,
            description       = cls._svc_description_ or cls._svc_display_name_ or cls._svc_name_,
            startType         = win32service.SERVICE_AUTO_START
        )
        print("Service %s installed successfully." % cls._svc_name_) 

    @classmethod
    def Uninstall(cls):
        state = cls.__CurrentState();
        if state is None:
            print("Service %s is not installed." % cls._svc_name_)
            return
        
        if state not in [win32service.SERVICE_STOPPED]:
            win32serviceutil.StopServiceWithDeps(cls._svc_name_)
            
        win32serviceutil.RemoveService(cls._svc_name_)
        print("Service %s uninstalled successfully." % cls._svc_name_)

    @classmethod
    def Start(cls):
        state = cls.__CurrentState();
        if state is None:
            print("Service %s is not installed." % cls._svc_name_)
            return
        if state == win32service.SERVICE_RUNNING:
            print("Service %s started already." % cls._svc_name_)
            return
        
        if state == win32service.SERVICE_STOP_PENDING:
            win32serviceutil.WaitForServiceStatus(cls._svc_name_, win32service.SERVICE_STOPPED, 30)
            state = win32service.SERVICE_STOPPED
        elif state == win32service.SERVICE_PAUSE_PENDING:
            win32serviceutil.WaitForServiceStatus(cls._svc_name_, win32service.SERVICE_PAUSED, 30)
            state = win32service.SERVICE_PAUSED

        if state == win32service.SERVICE_STOPPED:
            win32serviceutil.StartService(cls._svc_name_)
        elif state == win32service.SERVICE_PAUSED:
            win32serviceutil.ControlService(cls._svc_name_, win32service.SERVICE_CONTROL_CONTINUE)
        
        win32serviceutil.WaitForServiceStatus(cls._svc_name_, win32service.SERVICE_RUNNING, 30)
        print("Service %s started successfully." % cls._svc_name_)
        

    @classmethod
    def Stop(cls):
        state = cls.__CurrentState();
        if state is None:
            print("Service %s is not installed." % cls._svc_name_)
            return
        if state == win32service.SERVICE_STOPPED:
            print("Service %s stopped already." % cls._svc_name_)
        else:
            win32serviceutil.StopServiceWithDeps(cls._svc_name_)
            print("Service %s stopped successfully." % cls._svc_name_)
