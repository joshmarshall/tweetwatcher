TweetWatcher
===========
This is a simple little Tornado site that uses Redis, Websockets, and long-
polling to push tweets to a web browser. It's useful for conferences and
events where you want to encourage people to tweet with a certain hashtag.

Usage
-----
It's fairly easy to setup after git'ing:

```bash
mkvirtualenv --no-site-packages tweetwatcher
pip install -r requirements.txt
python tweetwatcher.py & python serve.py
```

... although you should probably run it behind supervisord or something
in production.

It works pretty simply -- the tweetwatcher.py file publishes the incoming
tweets from the streaming API to a Redis channel, and the serve.py
simply keeps the current clients in memory and subscribes to the Redis
channel, sending out messages to all the clients as they come in.

This means that you can spin up multiple serve.py on different ports and
load balance between them behind nginx or something similar. Keep in mind that
WebSockets will need access to each "native" Tornado instance.

You (must) override the settings with a settings.py file in the main 
directory. It should look something like this:

```python
import tweetstream
tweetstream.TWITTER_APP_USER = "myTwitterName"
tweetstream.TWITTER_APP_PASSWORD = "myPassword"

SETTINGS = {
    "redis_pub_channel": "myawesomechannel",
    "twitter_url": "/1/statuses/filter.json?track=foobar",
    "port": 8081
}
```

You can also set the port with a `--port 8888` argument to serve.py

Graphics / Look and Feel
------------------------
Changing the look is as simply as editing the `static/style.css` file. You can
also just swap out the `static/logo.png` file for your own logo if you are
happy with the default color scheme, etc.

Feedback
--------
I'd love to hear about it if you use this somewhere or if you have any issues
or suggestions.

TODO:
-----
* Add a cache for reloading, etc.
* Add a pre-fetch in case of server crashes and restarts
