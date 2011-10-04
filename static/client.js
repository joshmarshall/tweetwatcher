/* Globals for settings */
var TWEETHOSE = {
  maxTweets: 50,
  hostName: "localhost"
};

(function ($, WebSocket, JSON, console) {


  if (typeof JSON === "undefined") {
    throw new Error("Required JSON library missing.");
  }

  if (typeof console === "undefined") {
    console = { log: function() {} }; // dead function
  }


  $(function() {
    var tweetList, socket, Socket, lastFailed, Poll, parseMessage;
    tweetList = $("#tweets");
    lastFailed = null;

    parseMessage = function(data) {
      var tweetChildren, newTweet;
      if (data.type === "tweet") {
        while (tweetList.children("li").length > TWEETHOSE.maxTweets) {
          tweetChildren = tweetList.children("li");
          $(tweetChildren[tweetChildren.length-1]).remove();
        }
        if (!data.avatar) {
          data.avatar = "/static/irc_avatar.png";
        }
        newTweet = $(
          "<li>"+
            "<img src='"+data.avatar+"' class='avatar'/>"+
            "<p class='user'>"+
              "<span class='name'>"+data.name+"</span>"+
              "<span class='username'>@"+data.username+"</span>"+
            "</p>"+
            "<p class='text'>"+data.text+"</p>"+
          "</li>"
        );
        newTweet.hide();
        tweetList.prepend(newTweet);
        newTweet.slideDown();
      } else if (data.type === "clients") {
        $("#clients").text(data.count);
      }
    };


    Socket = function() {
      var conn = new WebSocket("ws://"+TWEETHOSE.hostName+"/stream");
      conn.onopen = function() {
        console.log("Connected.");
      };

      conn.onmessage = function(msg) {
        var data = JSON.parse(msg.data);
        parseMessage(data);
      };

      conn.onclose = function() {
        console.log("Closed.");
        if (lastFailed && new Date().getTime() - lastFailed < 2) {
          /* failed again in less than two seconds */
          return;
        }
        lastFailed = new Date().getTime();
        conn = new Socket();
      };

      return conn;
    };

    Poll = function(lastTime) {
      lastTime = (lastTime) ? lastTime : 0;
      $.ajax({
        url: "/poll?last_time="+lastTime+"&rand="+new Date().getTime(),
        success: function(data) {
          if (data.type === "messages") {
            for (var i=0; i<data.messages.length; i++) {
              parseMessage(data.messages[i]);
            }
          }
          Poll(data.time);
        }
      });

    };

    if (WebSocket) {
      socket = new Socket();
      window.setInterval(function() {
        var message = JSON.stringify({heartbeat: new Date().getTime()});
        socket.send(message);
      }, 5000); // send a heartbeat every 5 secs.
    } else {
      console.log("Long polling");
      Poll();
    }
  });

}(window.$, window.WebSocket, window.JSON, window.console));
