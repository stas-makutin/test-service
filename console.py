import signal
import threading

class AppThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.stoppedEvent = threading.Event()
        self.stoppedEvent.clear()
        self.app = app
        
    def run(self):
        print("Started.")
        self.app.run()
        print("Stopped.")
        self.stoppedEvent.set()
    
    def stop(self):
        self.app.stop()

def signal_handler(signal_number, stack_frame):
    del signal_number, stack_frame
    global appThread
    appThread.stop()

def run(_app_):
    global appThread
    appThread = AppThread(_app_)
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal_handler)
    appThread.start()
    appThread.stoppedEvent.wait()
    