'''
Development demo of a testing skeleton.
This uses a CAN link layer to gather remote node info

Usage:
python3.10 example_pip_test.py [host|host:port]

Options:
host|host:port            (optional) Set the address (or using a colon,
                          the address and port). Defaults to a hard-coded test
                          address and port.
'''

from canbus.canphysicallayergridconnect import CanPhysicalLayerGridConnect
from canbus.canframe import CanFrame
from canbus.canlink import CanLink
from canbus.controlframe import ControlFrame
from canbus.tcpsocket import TcpSocket

from openlcb.node import Node
from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.localnodeprocessor import LocalNodeProcessor
from openlcb.pip import PIP
from openlcb.remotenodeprocessor import RemoteNodeProcessor
from openlcb.remotenodestore import RemoteNodeStore
from openlcb.snip import SNIP

from queue import Queue
from queue import Empty

# specify default connection information
host = "192.168.16.212"
port = 12021
localNodeID = "05.01.01.01.03.01"
trace = False
timeout = 0.5

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


if trace :
    print("RR, SR are raw socket interface receive and send; RL, SL are link (frame) interface")

def sendToSocket(string) :
    if trace : print("   SR: "+string)
    s.send(string)

def receiveFrame(frame) : 
    if trace: print("RL: "+str(frame) )
 
canPhysicalLayerGridConnect = CanPhysicalLayerGridConnect(sendToSocket)
canPhysicalLayerGridConnect.registerFrameReceivedListener(receiveFrame)

def printMessage(msg):
    if trace: print("RM: {} from {}".format(msg, msg.source))
    readQueue.put(msg)

canLink = CanLink(NodeID(localNodeID))
canLink.linkPhysicalLayer(canPhysicalLayerGridConnect)
canLink.registerMessageReceivedListener(printMessage)

# create a node and connect it update
# This is a very minimal node, which just takes part in the low-level common
# protocols
localNode = Node(
    NodeID(localNodeID),
    SNIP("PythonOlcbNode", "example_node_implementation",
         "0.1", "0.2", "User Name Here", "User Description Here"),
    set([PIP.SIMPLE_NODE_IDENTIFICATION_PROTOCOL, PIP.DATAGRAM_PROTOCOL])
)

localNodeProcessor = LocalNodeProcessor(canLink, localNode)
canLink.registerMessageReceivedListener(localNodeProcessor.process)

# arrange for remote nodes to be tracked
remoteNodeStore = RemoteNodeStore(NodeID(localNodeID))
remoteNodeProcessor = RemoteNodeProcessor(canLink)
remoteNodeStore.processors = [remoteNodeProcessor]
canLink.registerMessageReceivedListener(remoteNodeStore.processMessageFromLinkLayer)


readQueue = Queue()

# put the read on a separate thread
def receiveLoop() :
    # bring the CAN level up
    if trace : print("      SL : link up")
    canPhysicalLayerGridConnect.physicalLayerUp()
    while True:
        input = s.receive()
        if trace : print("   RR: "+input)
        # pass to link processor
        canPhysicalLayerGridConnect.receiveString(input)
import threading
thread = threading.Thread(daemon=True, target=receiveLoop)

# define a routine for checking tests
def result(arg1, arg2=None, arg3=None, result=True) :
    # returns True if OK, False if failed
    # If arg1 and arg2 provided
    #   compare those, and fail if not equal; arg3 is then message
    # If only arg1, report it and return result for fail value
    if arg2 is not None :
        if arg1 == arg2 :
            # OK
            print(arg1)
            return True
        else :
            print("{} does not equal {}, FAIL".format(arg1, arg2))
            return False
    else:
        print(arg1)
        return result

# start the process
thread.start()


# pull the received messages
while True :
    try :
        received = readQueue.get(True, timeout)
        if trace : print("received: ", received)
    except Empty:
         break

# send an VerifyNodes message to provoke response
print("\nSend Verify NodeID Number Global\n")
message = Message(MTI.Verify_NodeID_Number_Global, NodeID(localNodeID), None)
if trace : print("SM: {}".format(message))
canLink.sendMessage(message)

# pull the received messages
while True :
    try :
        received = readQueue.get(True, timeout)
        if trace : print("received: ", received)
    except Empty:
         break

# print the resulting node store contents
print("\nDiscovered nodes:")

for node in remoteNodeStore.asArray() :
    print(node, node.snip.manufacturerName, "/", node.snip.userProvidedNodeName)

# this ends here, which takes the local node offline
