#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check for an OIR reply to an unknown MTI

Usage:
python3.10 check_me40_oir.py

The -h option will display a full list of options.
'''

import sys

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI

from queue import Empty

def test() :
    # set up the infrastructure

    import conformance.setup
    trace = conformance.trace() # just to be shorter
    timeout = 0.8

    # pull any early received messages
    conformance.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = conformance.getTargetID(timeout)

    ###########################
    # test sequence starts here
    ###########################
    
    # send a message with bogus MTI to provoke response
    message = Message(MTI.New_Node_Seen, NodeID(conformance.ownnodeid()), destination) # MTI selected to be addressed
    conformance.sendMessage(message)

    while True :
        try :
            received = conformance.getMessage(timeout) # timeout if no entries
            # is this a reply from that node?
            if not received.mti == MTI.Optional_Interaction_Rejected : continue # wait for next
            # this is a OIR message, success

            if destination != received.source : # check source in message header
                print ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)
        
            if NodeID(conformance.ownnodeid()) != received.destination : # check destination in message header
                print ("Failure - Unexpected destination of reply message: {} {}".format(received, received.destination))
                return(3)
            if len(received.data) < 4:
                print ("Failure - Unexpected length of reply message: {} {}".format(received, received.data))
                return(3)

            try :            
                seenMTI = MTI(0x2000|received.data[2]<<8 | received.data[3])
            except ValueError :
                seenMTI = None
            if seenMTI != received.mti :
                print ("Failure - MTI not carried in data: {} {}".format(received, received.data, seenMTI))
                try :
                    earlyMTI = MTI(0x2000|received.data[0]<<8 | received.data[1])
                except ValueError:
                    earlyMTI = None
                if earlyMTI != received.mti :
                    print("    Hint: MTI incorrectly found in first two bytes of OIR reply")
                return(3)
            
            break
        except Empty:
            print ("Failure - Did not receive Optional Interaction Rejected reply")
            return(3)

    if trace >= 10 : print("Passed")
    return 0

if __name__ == "__main__":
    sys.exit(test())