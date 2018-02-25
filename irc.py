# Todo
# Two threads running at once (Instagram)
# IRC Commands
# Separate logic for EsperNet and SnooNet
# Get NickServ to work properly / Change NickServ Password

import twitterservice, db
import socket, ssl
import threading
import json
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#HOST = 'irc.esper.net'
HOST = 'irc.snoonet.org'
PORT = 6697
NICK = 'MaxQ'
admin = 'jclishman'
channels = ['#lishbot']

# Secret credentials :)
credentials = json.load(open('_secret.json'))
password = credentials['nickserv_password']

# Responds to server pings
def pong(text):
    print('PONG' + text.split()[1])
    irc.send(parse('PONG ' + text.split()[1]))

# Makes things human-readable
def parse(string): return bytes(string + '\r\n', 'UTF-8')

# Sends messages
def send_message(message):
	for channel in channels:
		irc.send(parse('PRIVMSG ' + channel + ' :' + message))

# Estabilishes a secure SSL connection
s.connect((HOST, PORT))
irc = ssl.wrap_socket(s)

print('Connecting...')

time.sleep(2)

# Tells the server who it is
irc.send(parse("USER " + NICK + " " + NICK + " " + NICK + " :Bot"))
irc.send(parse("NICK " + NICK))

time.sleep(2)


# Responds to the initial server ping on connection
has_responded_to_ping = False

while not has_responded_to_ping:
    text=irc.recv(1024).decode("UTF-8").strip('\r\n')

    if text.find('PING') != -1:
    	pong(text)
    	has_responded_to_ping = True


time.sleep(2)

# Identifies nickname
irc.send(parse('PRIVMSG NickServ IDENTIFY %s %s' % (NICK, password)))

# Joins channel(s)
for channel in channels:

	irc.send(('JOIN {}\n').format(channel).encode())
	time.sleep(2)

# Threading magic
# I barely understand how this works, so not gonna touch it
class twitter_thread(threading.Thread):
	def __init__(self, threadID, name):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.name = name

	def run(self):
		twitterservice.run()

	def getID(self, username):
		return twitterservice.getID(username)

	def refresh_stream(self):
		twitterservice.refresh_stream()
		print("> Refreshed the twitter stream")

twitter = twitter_thread(1, "Twitter thread")
twitter.start()

# Reads messages
# setBlocking needs to be False to allow for the passive sending of messages
irc.setblocking(False)
while True:
	irc_stream = None

	try:
		irc_stream = irc.recv(1024).decode('UTF-8')

	except OSError as e:
		#print("No data")
		time.sleep(0.05)

	if irc_stream is not None: print(irc_stream)

	# Sends ping
	if irc_stream is not None and irc_stream.find('PING') != -1:
		pong(text)
	
	#print(time.ctime())
	if irc_stream is not None and irc_stream.find('PRIVMSG') != -1:

		message_author = irc_stream.split('!',1)[0][1:]
		message_channel = irc_stream.split('PRIVMSG',1)[1].split(':', 1)[0].lstrip()
		message_contents = irc_stream.split('PRIVMSG',1)[1].split(':',1)[1]

		# Debugging
		print('Author: ' + message_author)
		print('Channel: ' + message_channel)
		print('Contents: ' + message_contents)

		# Admins can make the bot quit
		if message_author == admin and message_contents.rstrip() == 'bye':
			irc.send(parse("QUIT"))
			print('Exiting...')
			time.sleep(1)
			irc.close()

		# Basic commands
		if message_contents.startswith(("%s: ") % NICK):
			
			# Default values
			user_id = None
			found_user = False
			retweets = 0
			replies = 0

			# Makes everything lowercase, removes the bot username, and take out all spaces
			message_clean = message_contents.rstrip().replace(NICK + ': ', '').lower().replace(' ', '')
			
			# Clean-up and readability
			command = message_clean.split(',')
			action = command[0]

			if len(command) > 2:
				
				# Strip '@' from usernames
				command[2] = command[2].replace('@', '')
				
				# Are the right parameters passed? Throw an error if not
				try:
					platform = command[1]
					target_user = command[2]

				except:
					action = 'error'

				# If the account is on Twitter, try and get the retweet and reply flags. If there aren't any, throw an error
				if platform == 'twitter':

					try:
						user_id = twitter.getID(target_user)
						retweets = command[3]
						replies = command[4]
					except:
						action = 'error'

				elif platform == 'instagram':
					pass

				else: action = 'error' 	

				# Does the user exist?
				if user_id is not None:

					if action == 'follow' or action == 'unfollow':
						
						if platform == 'twitter' or platform == 'instagram':

							# Is the bot already following?
							for row in db.get_following(platform):
								
								if target_user in row: 

									# Checks if the flag on the specified platform is set
									if platform == 'twitter' and row[4] == 1: found_user = True
									if platform == 'instagram' and row[5] == 1: found_user = True				
							
							if found_user:
								send_message(("Already following @%s on %s") % (target_user, platform))

							# This runs if the bot is not following the account specified in the command
							else : 
								print('> Following: ' + str(user_id))
								db.follow_account(target_user, user_id, retweets, replies, platform)
								twitter.refresh_stream()
								send_message(("Followed @%s on %s with retweets %s and replies %s") % (target_user, platform, retweets, replies))
								#send_message(("Not following @%s on %s") % (target_user, platform))
								

					elif action == 'error':
						send_message(("Error: Invalid command. Say '%s: help' for syntax") % NICK)

				elif action == 'error':
					send_message(("Error: Invalid command. Say '%s: help' for syntax") % NICK)

				else: send_message(("Error: @%s does not exist") % target_user)

			elif action == 'set':
					print("WIP")

			elif action == 'help':
					send_message(('Command syntax: %s: follow|unfollow, twitter|instagram, @username, 0|1 <retweets>, 0|1 <replies>') % NICK)
			
			else:
				send_message(("Error: Invalid command. Say '%s: help' for syntax") % NICK)


			#print(command)

	start_time = time.time()

	posts = db.get_post_queue()
	if posts is not None:
		for row in posts:
			
			print(row)

			# Assembles and sends the IRC message
			send_message('[%s] @%s wrote: %s %s' % (row[1], row[2], row[3].replace('\n', ' '), row[4]))

			# Sends how long it took from tweet creation to irc message (debug)
			send_message('Tweet #' + str(row[0]) + ', Took ' + str(round(time.time() - start_time, 5)) + 's')
			#print(str(round(time.time() - start_time, 5)), file=open("output.txt", "a"))
			
			# Updates the database after it posts something
			db.update_after_publish(row[0])
			
			time.sleep(0.5)

irc.close()
exit()