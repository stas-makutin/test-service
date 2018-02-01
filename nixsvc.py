import daemon
import signal
import lockfile.pidlockfile
import os
import pwd
import grp
import errno
import sys
import shutil
import stat
import time
import subprocess
import application
import logging

class NixService():
    _svc_name_ = application.Application._svc_name_
    _svc_display_name_ = application.Application._svc_display_name_
    _svc_description_ = application.Application._svc_description_
    _svc_user_ = _svc_name_
    _svc_group_ = _svc_name_
    _lock_file_ = f"/var/run/{_svc_name_}/pid"
    _init_script_ = f"/etc/init.d/{_svc_name_}"
    _log_file_ = f"/var/log/{_svc_name_}/{_svc_name_}.log"
    _logrotate_file_ = f"/etc/logrotate.d/{_svc_name_}"
    _log_backup_count_ = application.Application._svc_log_backup_count_
    _log_max_bytes_ = application.Application._svc_log_max_bytes_
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
                    return True
        except OSError:
            pass
        return False
    
    @classmethod
    def __Stop(cls):
        cls.__GetProcessId()
        rc = True
        if cls.__pid is not None:
            rc = False
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
                        rc = True
                        break
                    time.sleep(0.25)
            try:
                if rc and os.path.isfile(cls._lock_file_): 
                    os.remove(cls._lock_file_)
            except OSError:
                pass
        return rc
    
    @staticmethod
    def __MakeDir(dirPath, uid, gid):
        dirCreated = False
        error = None
        try:
            os.makedirs(dirPath)
            dirCreated = True
        except OSError as err:
            if err.errno != errno.EEXIST:
                error = err
        if error is None:
            try:
                os.chmod(dirPath, stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH | stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                os.chown(dirPath, uid, gid)
            except OSError as err:
                error = err
                if dirCreated:
                    try:
                        os.rmdir(dirPath)
                    except:
                        pass
        return (dirPath, dirCreated, error)
    
    @classmethod
    def __GetLockDir(cls):
        return os.path.dirname(os.path.abspath(cls._lock_file_))
    
    @classmethod
    def __MakeLockDir(cls, uid, gid):
        return cls.__MakeDir(cls.__GetLockDir(), uid, gid)

    @classmethod
    def __GetLogDir(cls):
        return os.path.dirname(os.path.abspath(cls._log_file_))
    
    @classmethod
    def __MakeLogDir(cls, uid, gid):
        return cls.__MakeDir(cls.__GetLogDir(), uid, gid)

    @classmethod
    def __GetUserAndGroup(cls):
        gid = None
        uid = None
        if cls._svc_group_:
            try:
                gid = grp.getgrnam(cls._svc_group_).gr_gid
            except KeyError:
                pass
        if cls._svc_user_:
            try:
                user = pwd.getpwnam(cls._svc_user_)
                uid = user.pw_uid;
                if gid is None:
                    gid = user.pw_gid;
            except KeyError:
                pass
        return (uid, gid)
    
    @classmethod
    def Install(cls):
        if cls.__IsInstalled():
            print("Service %s installed already." % cls._svc_name_)
            return
        
        success = True
        uid, gid = cls.__GetUserAndGroup()
        
        groupCreated = False
        if success and gid is None and cls._svc_group_:
            success = False
            if subprocess.run(["groupadd", cls._svc_group_]).returncode == 0:
                gid = grp.getgrnam(cls._svc_group_).gr_gid
                groupCreated = success = True

        userCreated = False
        if success and uid is None and cls._svc_user_:
            success = False
            cmd = ["useradd", "--system", cls._svc_user_];
            if gid is not None:
                cmd.append("--gid")
                cmd.append(str(gid))
            if subprocess.run(cmd).returncode == 0:
                user = pwd.getpwnam(cls._svc_user_)
                uid = user.pw_uid
                if gid is None:
                    gid = user.pw_gid;
                userCreated = success = True

        if uid is None:
            uid = os.getuid()
        if gid is None:
            gid = os.getgid()

        lockDir, lockDirCreated, error = None, False, None
        if success:
            lockDir, lockDirCreated, error = cls.__MakeLockDir(uid, gid) 
            if error is not None:
                print(repr(error))
                success = False

        logDir, logDirCreated, error = None, False, None
        if success:
            logDir, logDirCreated, error = cls.__MakeLogDir(uid, gid) 
            if error is not None:
                print(repr(error))
                success = False

        if success and os.path.isdir(os.path.dirname(os.path.abspath(cls._logrotate_file_))):
            success = False
            try:
                with open(cls._logrotate_file_, 'w') as f:
                    f.write("""\
{logFile} {{
    rotate {backupCount}
    size {maxBytes}
    compress
    missingok
    notifempty
}}
"""
                    .format(
                        logFile = cls._log_file_,
                        backupCount = cls._log_backup_count_,
                        maxBytes = cls._log_max_bytes_
                    ))

                success = True
            except OSError as err:
                print(repr(err))
        
        if success:
            success = False
            try:
                with open(cls._init_script_, 'w') as f:
                    f.write("""\
#! /bin/sh
### BEGIN INIT INFO
# Provides:          {serviceName}
# Required-Start:    $local_fs $network $named $remote_fs $syslog $time
# Required-Stop:     $local_fs $network $named $remote_fs $syslog $time
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
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
"""
                    .format(
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
                	if subprocess.run(["update-rc.d", cls._svc_name_, "defaults"]).returncode == 0:
                		success = True
            except OSError as err:
                print(repr(err))

        if success:
            print("Service %s installed successfully." % cls._svc_name_)
        else:
            try:
                os.remove(cls._init_script_)
            except:
                pass
            try:
                os.remove(cls._logrotate_file_)
            except:
                pass
            if lockDirCreated:
                try:
                    os.rmdir(lockDir)
                except:
                    pass
            if logDirCreated:
                try:
                    os.rmdir(logDir)
                except:
                    pass
            if userCreated:
                subprocess.run(["userdel", cls._svc_user_])
            if groupCreated:
                subprocess.run(["groupdel", cls._svc_group_])
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
            if os.path.isfile("/usr/lib/lsb/remove_initd") and os.access("/usr/lib/lsb/remove_initd", os.X_OK):
                if subprocess.run(["/usr/lib/lsb/remove_initd", cls._init_script_]).returncode == 0:
                    success = True
            else:
                if subprocess.run(["update-rc.d", cls._svc_name_, "remove"]).returncode == 0:
                    success = True
        except OSError as err:
            print(repr(err))
            
        if success:
            try:
                os.remove(cls._init_script_)
            except:
                pass
            try:
                os.remove(cls._lock_file_)
            except:
                pass
            try:
                shutil.rmtree(cls.__GetLockDir(), True)
            except:
                pass
            try:
                os.remove(cls._logrotate_file_)
            except:
                pass
            try:
                shutil.rmtree(cls.__GetLogDir(), True)
            except:
                pass
            
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
        
        _uid, _gid = self.__GetUserAndGroup()
            
        if _uid is None:
            _uid = os.getuid()
        if _gid is None:
            _gid = os.getgid()
            
        self.__MakeLockDir(_uid, _gid);
        self.__MakeLogDir(_uid, _gid);
        
        log = logging.getLogger(self._svc_name_);
        log.propagate = False
        lh = None
        if os.path.exists(self._logrotate_file_):
            lh = logging.handlers.WatchedFileHandler(filename=self._log_file_, encoding="utf-8")
        else:
            import gzip
            
            def namer(name):
                return name + ".gz"
            
            def rotator(source, dest):
                with open(source, 'rb') as fsrc:
                    with gzip.open(dest, 'wb') as fdst:
                        shutil.copyfileobj(fsrc, fdst)
            
            lh = logging.handlers.RotatingFileHandler(
                filename=self._log_file_, 
                encoding="utf-8", 
                maxBytes=self._log_max_bytes_, 
                backupCount=self._log_backup_count_
            )
            lh.rotator = rotator
            lh.namer = namer
            
        lh.setFormatter(logging.Formatter('%(asctime)s %(levelno)s %(message)s'))
        log.setLevel(logging.INFO);
        log.addHandler(lh)
        
        context = daemon.DaemonContext(
            files_preserve=[lh.stream],
            uid=_uid,
            gid=_gid,
            umask=0o002,
            pidfile=lockfile.pidlockfile.PIDLockFile(self._lock_file_)
        )
        
        context.signal_map = {
            signal.SIGTERM: NixService.__StopHandler
        }
        
        with context:
            print("Started")
            log.info(f"{self._svc_name_} started")
            try:
                __app = application.Application(log, self._log_file_)
                __app.run()
            except:
                print(sys.exc_info())
                log.error(f"{self._svc_name_} failed:\n{sys.exc_info()}", )
            log.info(f"{self._svc_name_} stopped")
            print("Stopped")
