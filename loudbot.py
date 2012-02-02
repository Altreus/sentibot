#!/usr/bin/python

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys, re, random

IRCHOST = "irc.quakenet.org"
IRCPORT = 6667
IRCNICK = "loudbot"
IDENT = "loudbot"
REALNAME = "loudbot"

class Loudlist:
	list = []
	filename = None

	def __init__(self, filename):
		self.filename = filename
		
		file = open(filename, 'r')
		self.list = file.readlines()

		file.close()

		self.list = [line.strip() for line in self.list]

	def __del__(self):
                pass
#		file = open(self.filename, 'w')
#
#		for line in self.list:
#			file.write("%s\n" % line)
#
#		file.close()

	def add_loudness(self, noise):
		self.list.append(noise)

	def get_loudness(self):
		return random.choice(self.list)

	def num_loudnesses(self):
		return len(self.list)
		

class Loudbot(irc.IRCClient):
	"""A loud IRC bot."""

	nickname = IRCNICK

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

          # Beware of inflatable monkeys

			else:
				to_me = re.match("%s[,:]?\s+(.*)$" % self.nickname, msg)

				if to_me is not None:
					msg = msg.split(self.nickname,1)[1][2:]

					if msg.lower().startswith('be'):
						who = re.match("be\s+(\S+)", msg)

						if who is not None:
                                                        print "Being %s" % who.group(1)
							self.msg(channel, "<%s> %s" % (who.group(1), self.be_loud()))

					elif msg.lower().strip() == "leave":
						self.part(channel)

					else:
						self.msg(channel, "%s: %s" % (user, self.be_loud()))
							

				else:
					if msg.upper() == msg and len(msg) > 10 and re.match('[a-z]', msg, re.I):
						if self.factory.list.num_loudnesses() > 30:
							self.msg(channel, self.be_loud())
						self.add_loudness(msg)

	def be_loud(self):
		return self.factory.list.get_loudness()

	def add_loudness(self, noise):
		self.factory.list.add_loudness(noise)


class LoudbotFactory(protocol.ClientFactory):
	"""A factory for Loudbots.

	A new protocol instance will be created each time we connect to the server.
	"""

	# the class of the protocol to build when new connection is made
	protocol = Loudbot

	def __init__(self):
		self.list = Loudlist("list")

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
