'''
Demo of using the memory service to read the CDI from memory, then an example of parsing

Usage:
python3 example_memory_transfer.py [host|host:port]

Options:
host|host:port            (optional) Set the address (or using a colon,
                          the address and port). Defaults to a hard-coded test
                          address and port.
'''


from openlcb.canbus.tcpsocket import TcpSocket

from openlcb.canbus.canphysicallayergridconnect import CanPhysicalLayerGridConnect
from openlcb.canbus.canlink import CanLink
from openlcb.nodeid import NodeID
from openlcb.datagramservice import (
    DatagramService,
)
from openlcb.memoryservice import (
    MemoryReadMemo,
    MemoryService,
)

# specify connection information
host = "192.168.16.212"
port = 12021
localNodeID = "05.01.01.01.03.01"
#farNodeID = "09.00.99.03.00.35"
farNodeID = "02.01.57.00.04.9C"

# region same code as other examples


def usage():
    print(__doc__, file=sys.stderr)


if __name__ == "__main__":
    # global host  # only necessary if this is moved to a main/other function
    import sys
    if len(sys.argv) == 2:
        host = sys.argv[1]
        parts = host.split(":")
        if len(parts) == 2:
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                usage()
                print("Error: Port {} is not an integer.".format(parts[1]),
                      file=sys.stderr)
                sys.exit(1)
        elif len(parts) > 2:
            usage()
            print("Error: blank, address or address:port format was expected.")
            sys.exit(1)
    elif len(sys.argv) > 2:
        usage()
        print("Error: blank, address or address:port format was expected.")
        sys.exit(1)

# endregion same code as other examples

s = TcpSocket()
s.connect(host, port)


#print("RR, SR are raw socket interface receive and send;"
#      " RL, SL are link interface; RM, SM are message interface")

def sendToSocket(string):
    #print("      SR: {}".format(string.strip()))
    s.send(string)


def printFrame(frame):
    # print("   RL: {}".format(frame))
    pass

def printMessage(message):
    #print("RM: {} from {}".format(message, message.source))
    pass

def printDatagram(memo):
    """create a call-back to print datagram contents when received

    Args:
        memo (_type_): _description_

    Returns:
        bool: Always False (True would mean we sent a reply to this datagram,
            but let MemoryService do that).
    """
    #print("Datagram receive call back: {}".format(memo.data))
    return False


canPhysicalLayerGridConnect = CanPhysicalLayerGridConnect(sendToSocket)
canPhysicalLayerGridConnect.registerFrameReceivedListener(printFrame)

canLink = CanLink(NodeID(localNodeID))
canLink.linkPhysicalLayer(canPhysicalLayerGridConnect)
canLink.registerMessageReceivedListener(printMessage)

datagramService = DatagramService(canLink)
canLink.registerMessageReceivedListener(datagramService.process)

datagramService.registerDatagramReceivedListener(printDatagram)

memoryService = MemoryService(datagramService)



# accumulate the CDI information
resultingCDI = []

# Invoked when the memory read successfully returns, 
# this queues a new read until the entire CDI has been
# returned.  At that point, it invokes the XML processing below.
def memoryReadSuccess(memo):
    """createcallbacks to get results of memory read

    Args:
        memo (_type_): _description_
    """
    #print("successful memory read: {}".format(memo.data))
    
    global resultingCDI

    # is this done?
    if len(memo.data) == 64 and not 0 in memo.data:
        # save content
        resultingCDI += memo.data
        # update the address
        memo.address = memo.address+64
        # and read again
        memoryService.requestMemoryRead(memo)
    else :
        # and we're done!
        # save content 
        resultingCDI += memo.data
        # concert resultingCDI to a string up to 1st zero
        cdiString = ""
        for x in resultingCDI:
            if x == 0 : break
            cdiString += chr(x)
        # print (cdiString)

        # and process that
        processXML(cdiString)
        
        # done
        
def memoryReadFail(memo):
    print("memory read failed: {}".format(memo.data))

#######################
# The XML parsing section.
# 
# This creates a handler object that just prints
# information as it's presented. 
#
# Since `characters` can be called multiple times
# in a row, we buffer up the characters until the `endElement`
# call is invoked to indicate the text is complete

import xml.sax

# define XML SAX callbacks in a handler object
class MyHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self._charBuffer = []

    def startElement(self, name, attrs):
        print ("Start: ", name)
        if attrs is not None and attrs :
            print ("  Atributes: ", attrs.getNames())

    def endElement(self, name):
        print (name, "cpntent:", self._flushCharBuffer())
        print ("End: ", name)
        pass

    def _flushCharBuffer(self):
        s = ''.join(self._charBuffer)
        self._charBuffer = []
        return s

    def characters(self, data):
        self._charBuffer.append(data)

handler = MyHandler()

# process the XML and invoke callbacks
def processXML(content) :
    xml.sax.parseString(content, handler)
    print("\nParser done")

#######################

# have the socket layer report up to bring the link layer up and get an alias
#print("      SL : link up")
canPhysicalLayerGridConnect.physicalLayerUp()


def memoryRead():
    """Create and send a read datagram.
    This is a read of 20 bytes from the start of CDI space.
    We will fire it on a separate thread to give time for other nodes to reply
    to AME
    """
    import time
    time.sleep(1)

    # read 64 bytes from the CDI space starting at address zero
    memMemo = MemoryReadMemo(NodeID(farNodeID), 64, 0xFF, 0, memoryReadFail,
                             memoryReadSuccess)
    memoryService.requestMemoryRead(memMemo)


import threading  # noqa E402
thread = threading.Thread(target=memoryRead)
thread.start()

# process resulting activity
while True:
    received = s.receive()
    #print("      RR: {}".format(received.strip()))
    # pass to link processor
    canPhysicalLayerGridConnect.receiveString(received)
