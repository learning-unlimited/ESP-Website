import socket
import asyncore
import struct

import TOC.Protocol

WANT_FLAP_SIGNON, WANT_SIGNON, WANT_CONFIG, CONNECTED = range(4)

class BadPacket(Exception):
	"""Raised when a Client class receives a packet it doesn't expect
	or know how to deal with.
	"""
	pass

class UnsupportedVersion(Exception):
	"""Raised if the server returns a version number we don't support."""
	pass

class RawClient(asyncore.dispatcher):
	"""This class implements an extremely bare-bones TOC client.  It
	handles connecting to the server, and provides simple callbacks,
	but leaves everything else to subclasses.

	TOC.Client.RawClient is an asyncore.dispatcher, so once a client
	is created, it must be run with asyncore.loop()

	Calling TOC.Client.RawClient(sn,pass) will connect the specified
	user to the TOC server, but any additional behavior must be
	defined by a subclass
	"""
	def __init__(self, sn, password, host="toc.oscar.aol.com", \
		     port=5190):
		asyncore.dispatcher.__init__(self)
		self.FLAP = TOC.Protocol.FLAPConnection()
		self.outBuffer = ""
		self.screenName = sn
		self.password = password
		self.host = host
		self.port = port
		self.state = None
		self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
		self.connect( (host,port) )
		self._send("FLAPON\r\n\r\n")
		self.state = WANT_FLAP_SIGNON

	def sendCommand(self, command, *args):
		"""Send a command to the TOC server. Extra arguments will be
		handled as in TOC.Protocol.FLAPConnection.encodeTOCArgument()
		"""
		packet = self.FLAP.TOCCommandPacket(command,*args)
		self._send(packet)

	def CONFIGReceived(self, config):
		"""Called to give subclasses an opportunity to send TOC config
		commands, such as privacy modes or adding or removing buddies,
		before the client is actually signed on.
		"""
		#By default, add ourself to our buddy
		#list so the server will sign us on
		self.sendCommand("toc_add_buddy", \
				 TOC.Protocol.normalize(self.screenName))

	def commandReceived(self, command, args):
		"""Called when a command is received from the TOC server.
		Subclasses should override this in order to handle these
		commands.  args will be in the raw colon-separated form
		received from the server.
		"""
		pass

	def keepAliveReceived(self):
		pass

	def _send(self,data):
		"""Add data to an outgoing buffer to be sent."""
		self.outBuffer += data

	def _handlePacket(self, packet):
		"""Handle an incoming TOC packet."""
		if packet.header.frametype == TOC.Protocol.FT_SIGNON:
			if self.state != WANT_FLAP_SIGNON:
				raise BadPacket("Unexpected FLAP SIGN_ON packet.")
			FLAPVersion, = struct.unpack("L",packet.data)
			if FLAPVersion != 1:
				raise UnsupportedVersion("Bad server FLAP version: %d" \
										 % FLAPVersion)
			self._send(self.FLAP.signonPacket(self.screenName))
			self.sendCommand("toc_signon",
								"login.oscar.aol.com", self.port,
								TOC.Protocol.normalize(self.screenName),
								TOC.Protocol.roast(self.password),
								"english","PyAIM v.pi")
			self.state = WANT_SIGNON
		elif packet.header.frametype == TOC.Protocol.FT_KEEP_ALIVE:
			self.keepAliveReceived()
		elif packet.header.frametype == TOC.Protocol.FT_DATA:
			command, args = packet.data.split(":",1)
			if command == "SIGN_ON":
				if self.state != WANT_SIGNON:
					raise BadPacket("Unexpected SIGN_ON")
				print "Signon with server version: %s" % args
				self.state = WANT_CONFIG
			elif command == "CONFIG":
				if self.state == WANT_CONFIG:
					#Give subclasses the chance to deal with and send config
					self.CONFIGReceived(args)
					self.sendCommand("toc_init_done")
					self.state = CONNECTED
					print "Config Received."
				else:
					self.commandReceived(command,args)
			else:
				self.commandReceived(command,args)
		else:
			raise BadPacket("Unexpected frametype: %d (%s)" \
							% (packet.header.frametype, packet.data))
			pass	

	def handle_connect(self):
		pass

	def handle_read(self):
		self.FLAP.addData(self.recv(8192))
		for packet in self.FLAP.newPackets(): self._handlePacket(packet)

	def handle_write(self):
		sent = self.send(self.outBuffer)
		self.outBuffer = self.outBuffer[sent:]

	def handle_close(self):
		print "Connection Dropped"
		raise asyncore.ExitNow

	def writable(self):
		return (len(self.outBuffer) > 0)


class SimpleClient(RawClient):
	"""This is a subclass of RawClient that provides a higher-level
	interface to the TOC protocol. Incoming messages are handled by
	on_<MESSAGE> function calls to the SimpleClient subclass, with
	arguments passed as a flattened array.  SimpleClient also makes
	available an interface for sending specific commands to the
	server.

	All of the SimpleClient methods will normalize screen names for
	you if required by the protocol.
	"""

	#Maintain a dict of command -> split count for separating arguments
	splitCount = {
		"IM_IN"			:	3,
		"CHAT_IN"		:	4,
		"CHAT_INVITE"	:	4
		}

	def commandReceived(self, command, args):
		try:
			func = getattr(self,"on_%s" % command)
			argList = []
			if self.splitCount.has_key(command):
				argList = args.split(":",self.splitCount[command])
			else:
				argList = args.split(":")
			func(*argList)
		except (NameError, AttributeError):
		#Ignore lookup errors from the getattr
			pass

	def sendIM(self, toSN, message, auto=False):
		"""Send an IM to the specified screen name, optionally an
		autoresponse."""
		if not auto:
			self.sendCommand("toc_send_im", TOC.Protocol.normalize(toSN), \
							 message)
		else:
			self.sendCommand("toc_send_im", TOC.Protocol.normalize(toSN), \
							 message, "auto")

	def updateBuddy(self, sn):
		"""Ask the server to send you an UPDATE_BUDDY or ERROR message
		for the given buddy."""
		self.sendCommand("toc_get_status", TOC.Protocol.normalize(sn))

	def addBuddies(self, *sns):
		"""Add buddies to your current buddy list (Does not affect the
		saved config."""
		self.sendCommand("toc_add_buddy",*[TOC.Protocol.normalize(sn) \
										   for sn in sns])

	def removeBuddies(self, *sns):
		"""Remove buddies from your current buddy list, not changing
		the save config."""
		self.sendCommand("toc_remove_buddy",*[TOC.Protocol.normalize(sn) \
											  for sn in sns])

	def warn(self, sn, anon = False):
		"""Warn(Evil) a buddy, optionally anonymously."""
		self.sendCommand("toc_evil",TOC.Protocol.normalize(sn), anon \
						 and "anon" or "norm")

	def allow(self, *sns):
		"""Switch to permit privacy mode, and add the specified people
		to the allow list."""
		self.sendCommand("toc_add_permit",*[TOC.Protocol.normalize(sn) \
											for sn in sns])

	def deny(self, *sns):
		"""Switch to deny privacy mode, and add the specified people
		to the deny list."""
		self.sendCommand("toc_add_deny",*[TOC.Protocol.normalize(sn) \
										  for sn in sns])

	def joinChat(self, chat):
		"""Join the specified chat."""
		self.sendCommand("toc_chat_join", 4, chat)

	def sendChat(self, chatID, message):
		"""Send a message to a chat, using the chat ID from a CHAT_JOIN."""
		self.sendCommand("toc_chat_send", chatID, message)

	def whisperChat(self, chatID, dest, message):
		"""Send a whisper to someone in a chat room."""
		self.sendCommand("toc_chat_whisper", chatID, \
						 TOC.Protocol.normalize(dest), message)

	def leaveChat(self, chatID):
		"""Leave a chat room."""
		self.sendCommand("toc_chat_leave", chatID)

	def acceptChat(self, chatID):
		"""Accept a chat invitation."""
		self.sendCommand("toc_chat_accept", chatID)
