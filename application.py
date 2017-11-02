import tornado.ioloop
import tornado.web
import threading
    
class WebHandler(tornado.web.RequestHandler):
    def get(self, query):
        self.write("Hello, world : " + query)
  
class AppThread(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.stoppedEvent = threading.Event()
        self.stoppedEvent.clear()
        self.__app = tornado.web.Application([
            (r"/(.*)", WebHandler),
        ])
        self.__app.listen(port)
        tornado.log.access_log.setLevel("ERROR")
        
    def run(self):
        tornado.ioloop.IOLoop.current().start()
        print("Stopped.")
        self.stoppedEvent.set()
    
    def stop(self):
        tornado.ioloop.IOLoop.current().add_callback(lambda: tornado.ioloop.IOLoop.current().stop())
  
class Application:
    def __init__(self, port=8888):
        tornado.ioloop.IOLoop.configure('tornado.platform.asyncio.AsyncIOLoop')
        self.__app = tornado.web.Application([
            (r"/(.*)", WebHandler),
        ])
        self.__app.listen(port)
        tornado.log.access_log.setLevel("ERROR")
    
    def run(self):
        tornado.ioloop.IOLoop.current().start()

    def stop(self):
        tornado.ioloop.IOLoop.current().add_callback(lambda: tornado.ioloop.IOLoop.current().stop())
