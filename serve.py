from tornado.web import RequestHandler, Application, asynchronous
from tornado.httpclient import AsyncHTTPClient
from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from toredis.client import Client
import json
import uuid
import time
import optparse
import logging
import urllib
import urlparse

SETTINGS = {
    "port": 8888,
    "twitter_url": "/1/statuses/sample.json",

    # Arg / cookie settings
    "client_id_cookie": "client_id",
    "last_time_argument": "last_time",

    # Redis arguments
    "redis_host": "localhost",
    "redis_pub_channel": "tweetwatcher",

    # cache settings (should use redis for this later!!)
    "max_cache": 50
}

try:
    from settings import SETTINGS as local_settings
    SETTINGS.update(local_settings)
except ImportError:
    # No local settings
    pass

OPTIONS = optparse.OptionParser()
OPTIONS.add_option("-p", "--port", dest="port", type="int",
    default=8888, help="the server port")

CLIENTS = {} # in memory list of this Tornado instance's connections
CACHE = []

class PageHandler(RequestHandler):
    """ Just a simple handler for loading the base index page. """

    def get(self):
        host = self.request.host
        if ":" not in host:
            host += ":%s" % SETTINGS["port"]
        self.render("index.htm", host=host)

class PollHandler(RequestHandler):

        @asynchronous
        def get(self):
            """ Long polling group """
            self.client_id = self.get_cookie(SETTINGS["client_id_cookie"])
            last_time = int(self.get_argument(SETTINGS["last_time_argument"], 0))
            if not self.client_id:
                self.client_id = uuid.uuid4().hex
                self.set_cookie(SETTINGS["client_id_cookie"], self.client_id)
            CLIENTS[self.client_id] = self
            messages = {
                "type": "messages",
                "messages": [],
                "time": int(time.time())
            }
            for msg in CACHE[:]:
                if msg["time"] > last_time:
                    messages["messages"].append(msg)
            if messages["messages"]:
                return self.finish(messages)

        def write_message(self, message):
            """ Write a response and close connection """
            del CLIENTS[self.client_id]
            self.finish({
                "type": "messages",
                "messages":[message,],
                "time": int(time.time())
            })


class StreamHandler(WebSocketHandler):
    """ Watches the Twitter stream """

    client_id = None

    def open(self):
        """ Creates the client and watches stream """
        self.client_id = uuid.uuid4().hex
        CLIENTS[self.client_id] = self
        [self.write_message(msg) for msg in CACHE]

    def send_message(self, message):
        """ Send a message to the watching clients """
        msg_type, msg_channel, msg_value = message
        if msg_type == "message":
            self.write_message(json.loads(msg_value))

    def on_message(self, message):
        """ Just a heartbeat, no real purpose """
        pass

    def on_close(self):
        """ Removes a client from the connection list """
        del CLIENTS[self.client_id]
        print "Client %s removed." % self.client_id


def handle_message(message):
    """ Handle a publish message """
    msg_type, msg_channel, msg_value = message
    if msg_type != "message":
        # Nothing important right now
        return
    message = json.loads(msg_value)
    CACHE.append(message)
    while len(CACHE) > 50:
        CACHE.pop(0)
    for client in CLIENTS.values():
        try:
            client.write_message(message)
        except Exception, exc:
            # Client is already closed?
            logging.error("%s", exc)


def cache_prefetched_tweets(response):
    """ Fills cache with new messages """
    if response.code != 200:
        logging.error("Invalid twitter response: %s" % response.code)
        return
    results = json.loads(response.body)["results"]
    results.reverse()
    for result in results:
        try:
            text = result["text"]
            name = ""
            username = result["from_user"]
            avatar = result["profile_image_url"]
        except KeyError:
            logging.error("Invalid tweet response %s" % result)
            continue
        CACHE.append({
            "type": "tweet",
            "text": text,
            "name": name,
            "username": username,
            "avatar": avatar,
            "time": 1
        })


def prefetch_tweets(ioloop):
    """ Prefetches the tweets for the configured keyword """
    client = AsyncHTTPClient()
    twitter_url_parsed = urlparse.urlparse(SETTINGS["twitter_url"])
    twitter_query = urlparse.parse_qs(twitter_url_parsed.query)
    twitter_keywords = twitter_query.get("track")
    if not twitter_keywords:
        logging.warning("No twitter keywords -- not prefetching.")
        return
    params = {
        "result_type": "recent",
        "rpp": SETTINGS["max_cache"],
        "with_twitter_user_id": "true",
        "q": " ".join(twitter_keywords)
    }
    query_params = urllib.urlencode(params)
    client.fetch("https://search.twitter.com/search.json?%s" % query_params,
        callback=cache_prefetched_tweets)

def main():
    """ Start the application and Twitter stream monitor """
    options, args = OPTIONS.parse_args()
    if options.port:
        SETTINGS["port"] = options.port
    ioloop = IOLoop.instance()
    prefetch_tweets(ioloop)
    app = Application([
        (r"/", PageHandler),
        (r"/stream", StreamHandler),
        (r"/poll", PollHandler)
    ], static_path="static", debug=True)
    app.listen(SETTINGS["port"])
    client = Client() # redis connection for all connected clients
    client.connect()
    client.subscribe(SETTINGS["redis_pub_channel"], callback=handle_message)
    # Monitor Twitter Stream once for all clients
    ioloop.start()


if __name__ == "__main__":
    main()
