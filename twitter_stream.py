from TwitterAPI import TwitterAPI

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.options
from tornado import escape

import os

# Connect to Twitter Authentication
import secret_twitter
api = TwitterAPI(
    secret_twitter.consumer_key,
    secret_twitter.consumer_secret,
    secret_twitter.access_token_key,
    secret_twitter.access_token_secret)

# Handler for homepage
class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("index.html")


# Handler which returns the results
class SearchHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        search_query = escape.xhtml_escape(self.get_argument('q'))
        if search_query:
            api.request('statuses/filter', {'track': search_query})
            for item in api.get_iterator():
                self.write_message(item)


def launcher():
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/search", SearchHandler),
    ],
        debug=True,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        xsrf_cookies=True,
        static_path=os.path.join(os.path.dirname(__file__), "static"),
    )
    application.listen(8080)
    tornado.options.parse_command_line()
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    launcher()
