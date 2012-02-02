#!/usr/bin/python

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys, re, random, string

IRCHOST = "irc.quakenet.org"
IRCPORT = 6667
IRCNICK = "loudbot"
IDENT = "loudbot"
REALNAME = "loudbot"
FIRSTWORD_SCORE = 3 #This is low so a response-heavy retort can beat a response-firstword one.

class Loudlist:
	list = []

	def __init__(self, retortfile, callrespfile):
		#set up retort file
		self.retortfile = retortfile
		retortf = open(retortfile, 'r')
		self.list = retortf.readlines()
		retortf.close()
		self.list = [line.strip() for line in self.list]

		#set up calls and responses
		self.callrespfile = callrespfile
		callrespf = open(callrespfile, 'r')
		self.responses = []
		for line in callrespf:
			if line.strip(): #ignore empty lines
				self.responses.append(line)
		callrespf.close()
		self.responses = [line.strip() for line in self.responses]

		self.calls = self.responses[::2]	#calls is every other item in responses, starting from zero
		del self.responses[::2]		#delete every other item from responses, starting from zero

		if len(self.calls) > len(self.responses):
			self.calls = self.calls[:len(self.responses)]

		#print self.calls
		#print self.responses

	def __del__(self):
		pass

	def add_loudness(self, noise):
		if noise not in self.list:	#avoid dupes.
			self.list.append(noise)
			retortf = open(self.retortfile, 'a')
			retortf.write('\n'+noise)

	def get_loudness(self, msg):
		if msg == None:
			#print "msg is none"
			return random.choice(self.list)
		else:
			#print "msg is " + msg
			return self.get_sentience(msg.split())

	def get_sentience(self, msg):
		"""Gets a possibly sentient response to msg."""
		best = []
		bestScore = 0

		msg = map( string.upper, msg )

		unique_inwords = set(msg)

		#print "Unique calls: " + str(list(set(unique_inwords) & set(self.calls)))

		#Find the absolute bestest retort, or retorts.
		for retort in self.list:
			score = self.calc_score( retort.split(), unique_inwords, msg[0] )
			if score == bestScore:
				#print "Equal score " + str(score) + " for " + str(retort)
				best.append( retort )
			elif score > bestScore:
				#print "Better score " + str(score) + " for " + str(retort)
				bestScore = score
				best = [retort]

		return random.choice(best)


	def calc_score( self, retort, inwords, first_inword ):
		"""Scores a single retort based on how many responses it has to the calls in the message"""
		score = 0
		for inword in list(set(inwords) & set(self.calls)):
			for resp in self.get_call_responses( inword ):
				if resp in retort:
					#print "Response " + str(resp) + " is in " + str(retort)
					if retort[0] == resp:
						score += FIRSTWORD_SCORE
						if first_inword == inword:
							#extra points if the first word of the retort is the response to
							#the first word of the message
							score += FIRSTWORD_SCORE
					else:
						score += 1
					#don't count multiple responses to a given call
					break
		return score

	def get_call_responses( self, call ):
		"""Gets the set of responses that match a given call."""
		out_responses = []
		response_idxs = [i for i,x in enumerate(self.calls) if x == call ]
		for idx in response_idxs:
			out_responses.append( self.responses[idx] )
		return out_responses

	def num_loudnesses(self):
		return len(self.list)

	def print_sentience(self):
		return str(zip(self.calls,self.responses))

	def add_sentience(self, call, resp):
		callrespf = open(self.callrespfile, 'a')
		callrespf.write( '\n' + call )
		callrespf.write( '\n' + resp )
		callrespf.close()
		self.calls.append(call)
		self.responses.append(resp)

	def rem_sentience(self, call, resp):
		#open callresp file for writing. we'll rewrite the entire thing.
		callrespf = open(self.callrespfile, 'w')

		#loop backwards so deleting doesn't fuck up the list order.
		#means we'll write the new file with all the entries (pairwise) backwards, but who cares :)
		for i in range(len(self.calls)-1,-1,-1):
			#baleet from local list
			if self.calls[i] == call and self.responses[i] == resp:
				del self.calls[i]
				del self.responses[i]
			else:
				callrespf.write( self.calls[i] + '\n' )
				callrespf.write( self.responses[i] + '\n' )
		callrespf.close()


class Loudbot(irc.IRCClient):
	"""A loud IRC bot."""

	nickname = IRCNICK

	def __init__(self):
		#irc.IRCClient.__init__(self)
		self.bListenOnly = False

	def connectionMade(self):
		print "Connected"
		irc.IRCClient.connectionMade(self)

	def connectionLost(self, reason):
		print "Disconnected"
		irc.IRCClient.connectionLost(self, reason)


	# callbacks for events

	def signedOn(self):
		"""Called when bot has succesfully signed on to server."""
		self.msg('Q@cserve.quakenet.org', 'auth loudbot l0udb0tisl0ud')
		self.mode(None, None, '+ix', None, self.nickname)
		print "Signed on"

	def privmsg(self, user, channel, msg):
		"""This will get called when the bot receives a message."""
		user = user.split('!', 1)[0]
		whisper = (channel == self.nickname)

		if whisper:
			print "Received whisper: %s" % msg
			if msg.lower().startswith("join"):
				chan = re.match("join\s+(#\S+)", msg)
				if chan is not None:
					print "Joining %s" % chan.group(1)
					self.join(chan.group(1))
			elif msg.lower().startswith("shutup"):
				self.bListenOnly = True
			elif msg.lower().startswith("talk"):
				self.bListenOnly = False
			elif msg.lower().startswith("print sentience"):
				self.print_sentience(user)
			elif msg.lower().startswith("add sentience"):
				msg = msg.split()
				if len(msg) >= 4:
					self.add_sentience( msg[2].upper(), msg[3].upper() )
			elif msg.lower().startswith("rem sentience"):
				msg = msg.split()
				if len(msg) >= 4:
					self.rem_sentience( msg[2].upper(), msg[3].upper() )

		else:
			to_me = re.match("%s[,:]?\s+(.*)$" % self.nickname, msg)

			if to_me is not None:
				msg = msg.split(self.nickname,1)[1]
				if msg[0] == ":" or msg[0] == ",":
					msg = msg[2:]
				else:	#need to account for the possibility of no punctuation.
					msg = msg[1:]

				if msg.lower().startswith('be'):
					who = re.match("be\s+(\S+)", msg)

					if who is not None:
						print "Being %s" % who.group(1)
						self.msg(channel, "<%s> %s" % (who.group(1), self.be_loud()))

				elif msg.lower().strip() == "leave":
					self.part(channel)

				else:
					msg = re.split("%s[,:]?\s+(.*)$" % self.nickname, msg)[0]
					self.msg(channel, "%s: %s" % (user, self.be_loud(msg)))

			else:
				if msg.upper() == msg and len(msg) > 10 and re.match('[a-z]', msg, re.I):
					if self.factory.list.num_loudnesses() > 30 and not self.bListenOnly:
						self.msg(channel, self.be_loud(msg))
					self.add_loudness(msg)

	def be_loud(self, msg = None):
		return self.factory.list.get_loudness(msg)

	def add_loudness(self, noise):
		self.factory.list.add_loudness(noise)

	def print_sentience(self,user):
		self.msg(user, self.factory.list.print_sentience())

	def add_sentience(self,call,resp):
		self.factory.list.add_sentience(call,resp)

	def rem_sentience(self,call,resp):
		self.factory.list.rem_sentience(call,resp)


class LoudbotFactory(protocol.ClientFactory):
	"""A factory for Loudbots.

	A new protocol instance will be created each time we connect to the server.
	"""

	# the class of the protocol to build when new connection is made
	protocol = Loudbot

	def __init__(self):
		self.list = Loudlist("list", "sentience")

	def clientConnectionLost(self, connector, reason):
		"""If we get disconnected, reconnect to server."""
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		print "connection failed:", reason
		reactor.stop()

    #This bit doesn't do anything, because it's a comment

if __name__ == '__main__':
		# create factory protocol and application
		f = LoudbotFactory()

		# connect factory to this host and port
		reactor.connectTCP(IRCHOST, IRCPORT, f)

		# run bot
		reactor.run()
