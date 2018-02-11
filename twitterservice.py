from tweepy.streaming import StreamListener
import tweepy
import json
import sqlite3
import db

# Secret credentials :)
credentials = json.load(open('_secret.json'))

# API Authentication
auth = tweepy.OAuthHandler(credentials["consumer_key"], credentials["consumer_secret"])
auth.set_access_token(credentials["access_token"], credentials["access_secret"])
api = tweepy.API(auth)

# Gets the list of users and their attributes from the database
users_list = db.get_following_twitter()

# Puts all the User IDs into a set for optimal performance
following = {x[1] for x in users_list}

# Tweet stream
class MyStreamListener(StreamListener):

    def on_data(self, data):
       
       	# Converts the data into usable JSON
    	data = json.loads(data)

    	# Puts user attributes into this list if the tweeet is from somebody the bot is following
    	# If the tweet isn't from someone the bot is following, set to None
    	user_of_tweet = next((x for x in users_list if x[1] == data['user']['id_str']), None)

    	# Sends the tweet to the database
    	def send_tweet_to_db():
    		db.insert_message('Twitter', data['user']['screen_name'], data['text'], 'https://twitter.com/' + data['user']['screen_name'] + '/status/' + data['id_str'])

    	# Is the tweet from somebody the bot cares about?
    	if user_of_tweet != None:
    		
     		# Is it a retweet?             Is the retweet flag of the user set to 1?
    		if "retweeted_status" in data and user_of_tweet[2] == 1:
    			send_tweet_to_db()
    			#print (data['text'])

    		# Is a reply?                  Is the reply flag of the user set to 1?
    		if data['in_reply_to_status_id'] != None and user_of_tweet[3]:
    			send_tweet_to_db()
    			#print (data['text'])

    		# If it's a normal tweet
    		elif "retweeted_status" not in data:
    			#print("not a retweeted_status")
    			send_tweet_to_db()
    			#print(data['text'])

    def on_error(self, status):
    	if status == 420:
    		return False

    	print(status)

# Makes the stream object
myStreamListener = MyStreamListener()
myStream = tweepy.Stream(auth, myStreamListener)

# Streams tweets
myStream.filter(follow=following)