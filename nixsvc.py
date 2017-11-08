import daemon
import signal
import lockfile.pidlockfile
import os
import errno
import sys
import stat
import time
import subprocess
import application

class NixService():
    _svc_name_ = application.Application._svc_name_
    _svc_display_name_ = application.Application._svc_display_name_
    _svc_description_ = application.Application._svc_description_
    _lock_file_ = f"/var/run/{_svc_name_}.pid"
    _init_script_ = f"/etc/init.d/{_svc_name_}"
    __pid = None

    @classmethod
    def __GetCommand(cls):
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            return "%s %s" % (os.path.abspath(sys.executable), os.path.abspath(sys.argv[0]))
    
    @classmethod
    def __IsInstalled(cls):
        if os.path.isfile(cls._init_script_):
            return True
        return False

    @classmethod
    def __GetProcessId(cls):
        if cls.__pid is None:
            if os.path.isfile(cls._lock_file_):
                with open(cls._lock_file_, "r") as pf:
                    cls.__pid = int(pf.readline())


    @staticmethod
    def __IsProcessRunning(pid):
        try:
            os.kill(pid, 0)
        except OSError as err:
            if err.errno == errno.EPERM:
                return True
            return False
        else:
            return True        

    
    @classmethod
    def __IsRunning(cls):
        try:
            cls.__GetProcessId()
            if cls.__pid is not None:
                if cls.__IsProcessRunning(cls.__pid):
                    cmd = subprocess.run(["ps", "-p", str(cls.__pid), "--no-headers", "-o", "args"], stdout=subprocess.PIPE).stdout.decode("utf-8")
                    if cmd.startswith(cls.__GetCommand()):
                        return True
        except OSError:
            pass
        try:
            os.remove(cls._lock_file_)
        except OSError:
            pass
        return False
    
    @classmethod
    def __Stop(cls):
        cls.__GetProcessId()
        rc = False
        if cls.__pid is not None:
            os.kill(cls.__pid, signal.SIGTERM)
            for _ in range(60):
                if not cls.__IsRunning():
                    rc = True
                    break
                time.sleep(0.25)
            if not rc:
                os.kill(cls.__pid, signal.SIGKILL)
                for _ in range(60):
                    if not cls.__IsRunning():
                        rc = False
                        break
                    time.sleep(0.25)
            try:
                if rc and os.path.isfile(cls._lock_file_): 
                    os.remove(cls._lock_file_)
            except OSError:
                pass
        return rc
    
    @classmethod
    def Install(cls):
        if cls.__IsInstalled():
            print("Service %s installed already." % cls._svc_name_)
            return
        
        success = False
        try:
            with open(cls._init_script_, 'w') as f:
                f.write("""\
#! /bin/sh
### BEGIN INIT INFO
# Provides:          {serviceName}
# Required-Start:    $local_fs $network $named $remote_fs $syslog $time
# Required-Stop:     $local_fs $network $named $remote_fs $syslog $time
# Default-Start:     3 4 5
# Default-Stop:      0 1 2 6
# Short-Description: {serviceDisplayName}
# Description:       {serviceDescription}
### END INIT INFO

APPCOMMAND="{applicationCommand}"

case "$1" in
    uninstall)
        $APPCOMMAND --uninstall
    ;;
    start)
        $APPCOMMAND --start
    ;;
    stop)
        $APPCOMMAND --stop
    ;;
    restart|force-reload)
        $APPCOMMAND --restart
    ;;
    status)
        $APPCOMMAND --status
    ;;
    *)
        echo "Usage: $0 {{uninstall|start|stop|restart|status}}"
        exit 1
    ;;
esac
""".format(
                serviceName = cls._svc_name_,
                serviceDisplayName = cls._svc_display_name_,
                serviceDescription = cls._svc_description_,
                applicationCommand = cls.__GetCommand()
                ))
            
            mode = os.stat(cls._init_script_).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            os.chmod(cls._init_script_, mode)
                
            if os.path.isfile("/usr/lib/lsb/install_initd") and os.access("/usr/lib/lsb/install_initd", os.X_OK):
                if subprocess.run(["/usr/lib/lsb/install_initd", cls._init_script_]).returncode == 0:
                    success = True
                else:
                    os.remove(cls._init_script_)
            else:
                success = True
        except OSError as err:
            print(repr(err))
            
        if success:
            print("Service %s installed successfully." % cls._svc_name_)
        else:
            print("Service %s installation failed." % cls._svc_name_)
    
    @classmethod
    def Uninstall(cls):
        if not cls.__IsInstalled():
            print("Service %s is not installed." % cls._svc_name_)
            return
        if cls.__IsRunning():
            if not cls.__Stop():
                print("Service %s stop failed." % cls._svc_name_)
                return
                
        success = False
        try:
            cleanup = True
            if os.path.isfile("/usr/lib/lsb/remove_initd") and os.access("/usr/lib/lsb/remove_initd", os.X_OK):
                if subprocess.run(["/usr/lib/lsb/remove_initd", cls._init_script_]).returncode != 0:
                    cleanup = False
            if cleanup:
                os.remove(cls._init_script_)
                if os.path.isfile(cls._lock_file_):
                    os.remove(cls._lock_file_)
                success = True
        except OSError as err:
            print(repr(err))

        if success:
            print("Service %s uninstalled successfully." % cls._svc_name_)
        else:
            print("Service %s uninstallation failed." % cls._svc_name_)

    @classmethod
    def Start(cls):
        if not cls.__IsInstalled():
            print("Service %s is not installed." % cls._svc_name_)
            return
        if cls.__IsRunning():
            print("Service %s started already." % cls._svc_name_)
            return
        print("Service %s started successfully." % cls._svc_name_)
        cls().Run()

    @classmethod
    def Stop(cls):
        if not cls.__IsInstalled():
            print("Service %s is not installed." % cls._svc_name_)
            return
        if not cls.__IsRunning():
            print("Service %s in not started." % cls._svc_name_)
            return
        if cls.__Stop():
            print("Service %s stopped successfully." % cls._svc_name_)
        else:
            print("Service %s stop failed." % cls._svc_name_)

    @classmethod
    def Status(cls):
        if not cls.__IsInstalled():
            print("Service %s is not installed." % cls._svc_name_)
        elif cls.__IsRunning():
            print("Service %s is running." % cls._svc_name_)
        else:
            print("Service %s stopped." % cls._svc_name_)

    @classmethod
    def __StopHandler(cls, signal_number, stack_frame):
        del signal_number, stack_frame
        global __app
        print("Stopping")
        __app.stop()

    def Run(self):
        global __app
        
        context = daemon.DaemonContext(
            umask=0o002,
            pidfile=lockfile.pidlockfile.PIDLockFile(self._lock_file_)
        )
        
        context.signal_map = {
            signal.SIGTERM: NixService.__StopHandler
        }
        
        with context:
            print("Started")
            try:
                __app = application.Application()
                __app.run()
            except:
                print(sys.exc_info())
                raise
            print("Stopped")
