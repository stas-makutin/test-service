import tornado.ioloop
import tornado.web
import threading
    
class WebHandler(tornado.web.RequestHandler):
    def get(self, query):
        self.write("Hello, world : " + query)
  
class Application:
    _svc_name_ = "testsvc"
    _svc_display_name_ = "Test Service"
    _svc_description_ = "Test Python service with HTTP server in it."
    
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
