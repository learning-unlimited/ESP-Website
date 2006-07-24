import copy
import re
import struct
import itertools

#Frame types
FT_SIGNON, FT_DATA, FT_ERROR, FT_SIGNOFF, FT_KEEP_ALIVE = range(1,6)

HEADER_LENGTH = 6

roastString = "Tic/Toc"

class BadFLAPHeader(Exception):
    """Thrown if a bad FLAP header is received."""
    pass

class FLAPHeader:
    """Represent the header of a TOC SFLAP Packet.

        Holds the following fields:
            star                The asterisk that begins every SFLAP header
            frametype	        The SFLAP Frametype
            sequence            The incoming sequenc number
            length              The length of the incoming data
        In practice, only frametype is likely to be useful to clients.
    """
    def __init__(self):
        self.star = None
        self.frametype = None
        self.sequence = None
        self.length = None

class TOCPacket:
    """Represent a TOC SFLAP Packet.

        Holds the following fields:
            header          A FLAPHeader object holding the packet header
            data            The incoming message, arguments unparsed
    """
    def __init__(self):
        self.header = FLAPHeader()
        self.data = None

class FLAPConnection:
    """Maintain a TOC SFLAP Connection

        Maintains sequence numbers, and parses incoming and assembles
		outgoing packets.
    """

    def __init__(self):
        self.inSequence = None
        self.outSequence = 0
        self.buffer = ""
        self.header = FLAPHeader()
        self.gotHeader = False
        self.packets = []

    def addData(self, data):
        """Add incoming data to the connection to be parsed."""
        self.buffer += data
        self._processData()

    def newPackets(self):
        """Returns an iterator over all available packets."""
        while self.packets:
            yield self.packets.pop(0)
        return

    def signonPacket(self, sn):
        """Returns a TOC signon packet for the given screen name."""
        sn = normalize(sn)
        length = len(sn)
        data = struct.pack(">LHH%ds"%length,1,1,length,sn)
        return self._rawPacket(data,FT_SIGNON)

    def dataPacket(self, data):
        """Returns a TOC data packet for the given data."""
        return self._rawPacket(data + "\0")

    def TOCCommandPacket(self, command, *args):
        """Returns a TOC data packet for the given command and arguments.
        Arguments are quoted and escaped as needed."""
        for arg in args:
            command += " " + self._escapeTOCArg(str(arg))
        return self.dataPacket(command)

    def _escapeTOCArg(self,arg):
        """Escapes and quotes a TOC argument string as needed."""
        arg = re.sub('([${}\\[\\]()"\'\\\\])',r'\\\1',arg)
        if arg.find(" ") != -1: arg = '"%s"' % arg
        return arg

    def _rawPacket(self, data, frametype = FT_DATA):
        """Returns a TOC packet with the given raw data and frametype."""
        length = len(data)
        packet = struct.pack(">cBHH%ds"%length,"*", \
                        frametype,self.outSequence,length,data)
        self.outSequence = (self.outSequence + 1) % 0xFFFF
        return packet

    def _processData(self):
        """Parses TOC packets out of an internal buffer."""
        while 1:
            if not self.gotHeader:
                if len(self.buffer) >= HEADER_LENGTH:
                    self.header.star, \
                        self.header.frametype, \
                        self.header.sequence, \
                        self.header.length = \
                        struct.unpack("cBHH",self.buffer[0:HEADER_LENGTH])
                    self.buffer = self.buffer[HEADER_LENGTH:]
                    self.gotHeader = True
                    if self.header.star != "*":
                        raise BadFLAPHeader("Bad initial byte: %s" \
                                    % self.header.star)
                    if self.inSequence is None:
                        self.inSequence = self.header.sequence
                    else:
                        self.inSequence += 1
						self.inSequence %= 0xFFFF
                        if self.header.sequence != self.inSequence:
                            raise BadFLAPHeader("Bad sequence number - " \
												"Got %d, " \
												"wanted %d" % \
												(self.header.sequence,
												 self.inSequence))
                else:
                    return
            elif len(self.buffer) >= self.header.length:
                packet = TOCPacket()
                packet.header = copy.copy(self.header)
                packet.data = self.buffer[0:self.header.length]
                self.packets.append(packet)
                self.buffer = self.buffer[self.header.length:]
                self.gotHeader = 0
            else:
                return

def normalize(sn):
    """Normalizes an AIM Screen name by removing spaces and lowercasing."""
    return sn.lower().replace(" ","").replace("\t","")

def roast(password):
    """"Roasts" a AIM password for the toc_signon command."""
    out = "0x"
    for char,roast in itertools.izip(password,itertools.cycle(roastString)):
        out += (hex(ord(char)^ord(roast))+"0")[2:4]
    return out
