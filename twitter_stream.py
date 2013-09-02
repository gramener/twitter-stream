from TwitterAPI import TwitterAPI

import tornado.ioloop
import tornado.web
import tornado.options
from tornado import escape

import os

# Connect to Twitter Authentication
api = TwitterAPI(consumer_key, consumer_secret, access_token_key, access_token_secret)


# Handler for homepage
class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("index.html")


# Handler which returns the results
class SearchHandler(tornado.web.RequestHandler):

    def get(self):
        search_query = escape.xhtml_escape(self.get_argument('q'))
        if search_query:
            api.request('search/tweets', {'q': search_query})
            iter = api.get_iterator()
            self.render("search.html", search_term=iter)


def launcher():
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/search", SearchHandler),
    ],
        debug=True,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        xsrf_cookies=True,
    )
    application.listen(8080)
    tornado.options.parse_command_line()
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    launcher()
