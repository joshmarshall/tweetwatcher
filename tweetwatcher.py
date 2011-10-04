from tornado.ioloop import IOLoop
from tweetstream import TweetStream
import redis
import json
try:
    from settings import SETTINGS
except ImportError:
    # No local settings
    SETTINGS = {}

SETTINGS.setdefault("twitter_url", "/1/statuses/sample.json")
SETTINGS.setdefault("redis_pub_channel", "tweetwatcher")

# Using blocking client because async one is underdeveloped
PUBLISH_CLIENT = redis.Redis()

def tweet_callback(message):
    """ Publish message """
    PUBLISH_CLIENT.publish(SETTINGS["redis_pub_channel"], json.dumps(message))

def main():
    stream = TweetStream(clean=True)
    stream.fetch(SETTINGS["twitter_url"], callback=tweet_callback)
    IOLoop.instance().start()

if __name__ == "__main__":
    main()
