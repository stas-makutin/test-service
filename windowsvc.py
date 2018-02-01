from sys import modules, executable
import sys
import os.path
import errno
import logging
import zipfile
import win32api
import winerror
import win32service
import win32serviceutil
import servicemanager
import application

class WindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = application.Application._svc_name_
    _svc_display_name_ = application.Application._svc_display_name_
    _svc_description_ = application.Application._svc_description_
    _log_backup_count_ = application.Application._svc_log_backup_count_
    _log_max_bytes_ = application.Application._svc_log_max_bytes_
    
    @staticmethod
    def __getLogDir():
        moduleDir = os.path.dirname(WindowsService.__getModuleFile())
        return os.path.join(moduleDir, "log")
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.__app = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.__app is not None:
            self.__app.stop()

    def SvcDoRun(self):
        logDir = WindowsService.__getLogDir()
        logFile = os.path.join(logDir, f"{self._svc_name_}.log")
        try:
            os.makedirs(logDir)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
        
        def namer(name):
            return name + ".zip"
        
        def rotator(source, dest):
            with zipfile.ZipFile(dest, 'w') as zf:
                zf.write(source, os.path.basename(source))
            os.remove(os.path.basename(source))
        
        lh = logging.handlers.RotatingFileHandler(
            filename=logFile, 
            encoding="utf-8", 
            maxBytes=self._log_max_bytes_, 
            backupCount=self._log_backup_count_
        )
        lh.rotator = rotator
        lh.namer = namer
        lh.setFormatter(logging.Formatter('%(asctime)s %(levelno)s %(message)s'))
        
        log = logging.getLogger(self._svc_name_);
        log.propagate = False
        log.setLevel(logging.INFO);
        log.addHandler(lh)
        
        log.info(f"{self._svc_name_} started")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.__app = application.Application(log, logFile)
            self.__app.run()
        except:
            log.error(f"{self._svc_name_} failed:\n{sys.exc_info()}", )
        
        log.info(f"{self._svc_name_} stopped")
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
    
    @staticmethod
    def __getModuleFile():
        try:
            moduleFile = modules[WindowsService.__module__].__file__
        except AttributeError:
            moduleFile = executable
        return os.path.abspath(moduleFile)

    @classmethod
    def Install(cls):
        state = cls.__CurrentState();
        if state is not None:
            print("Service %s installed already." % cls._svc_name_)
            return
        
        modulePath = WindowsService.__getModuleFile()
        classString = os.path.splitext(modulePath)[0] + '.' + cls.__name__;
        
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

    @classmethod
    def Status(cls):
        state = cls.__CurrentState();
        if state is None:
            print("Service %s is not installed." % cls._svc_name_)
        elif state == win32service.SERVICE_RUNNING:
            print("Service %s is running." % cls._svc_name_)
        elif state == win32service.SERVICE_STOP_PENDING:
            print("Service %s is stopping." % cls._svc_name_)
        elif state == win32service.SERVICE_PAUSE_PENDING:
            print("Service %s is pausing." % cls._svc_name_)
        elif state == win32service.SERVICE_STOPPED:
            print("Service %s stopped." % cls._svc_name_)
        elif state == win32service.SERVICE_PAUSED:
            print("Service %s paused." % cls._svc_name_)
        else:
            print("Service %s is starting." % cls._svc_name_)
