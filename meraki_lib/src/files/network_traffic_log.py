"""
Written by Christopher Corby, 12/28/21

This script logs network traffic for a given day. Not currently working

History:
 12/28/21 cmc Created

Requirements:
python 3, sys, getopt, sqlite3

"""

import meraki_functions, sqlite3, sys, getopt

# Classes
# this is a copy of the class in meraki_functions to make copying over into the list easier
class c_Net_Packet2:
    def __init__(self):
        app = ''
        destination = ''
        protocol = ''
        port = ''
        num_sent = ''
        num_received = ''
        clients = ''
        timeActive = ''
        flows = ''
    def __eq__(self, other):
        return self.app == other.app and self.destination == other.destination and self.protocol == other.protocol and self.port == other.port

# Functions

##########################################################################
#
# Function: trafficAnalysis
# Description: Creates a csv report of the network traffic for the day
# Inputs: Network Name
# Outputs: None
#
##########################################################################


def trafficAnalysis(NET_NAME):
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/src/files/meraki2.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    if NET_NAME == 'all':
        cur.execute('select ID from networks')
    else:
        cur.execute('select ID from networks where Name = ?', (NET_NAME,))
    rows = cur.fetchall()
    packetList = []
    i = 0
    for row in rows:
        netID = row[0]
        packets = meraki_functions.getNetTraffic(netID)
        if packets != None:
            for packet in packets:
                if packet not in packetList:
                    # copying over the new packet
                    packetList.append(c_Net_Packet2())
                    packetList[i].app = packet.app
                    packetList[i].destination = packet.destination
                    packetList[i].protocol = packet.protocol
                    packetList[i].port = packet.port
                    packetList[i].num_sent = packet.num_sent
                    packetList[i].num_received = packet.num_received
                    packetList[i].clients = packet.clients
                    packetList[i].timeActive = packet.timeActive
                    packetList[i].flows = packet.flows
                    i += 1
    print(len(packetList))
    con.close()


def main(argv):
    # obtaining inputs
    try:
        opts, args = getopt.getopt(argv, 'hk:o:m:')
    except getopt.GetoptError:
        sys.exit(2)
    # parsing arguments
    for opt, arg in opts:
        if opt == '-k':
            API_KEY = arg
        elif opt == '-o':
            NET_NAME = arg
    if API_KEY == '':
        print("-k isn't optional")
        sys.exit(2)
    # default is all organizations
    if NET_NAME == '':
        NET_NAME = 'all'
    meraki_functions.createDashboard(API_KEY)
    trafficAnalysis(NET_NAME)

if __name__ == '__main__':
    main(sys.argv[1:])
