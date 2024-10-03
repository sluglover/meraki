#!/usr/bin/env python3
"""
Written by Christopher Corby, 1/3/22

This script writes a CSV detailing the number of clients for each MX device

History:
 1/3/22 cmc Created and finished working version
 3/20/22 cmc reworked to no longer rely on the database

Requirements: 
python 3, sqlite 3, meraki_functions, sys, opt

Examples:
./clients_per_AP_report.py -k API_KEY -o ORG_NAME

"""
# Imports

import meraki_functions, sys, getopt, sqlite3, csv

# Functions

def databaseRoute(ORG_NAME):
    """
    Pulls the necessary data strictly from the sqlite database. Not used anymore due to the database being a poor concept
    
    :usage: databaseRoute(String of Organization name) -> csv of number of clients per mx
    :param ORG_NAME: Name of the organization to obtain
    :returns: CSV of MX name and number of clients
    :raises:
    """
    con =  sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/meraki2.db')
    cur = con.cursor()
    if ORG_NAME =='/all':
        cur.execute('select Name, Serial from devices where model like ?', ('%MX%',))
        rows = cur.fetchall()
        for row in rows:
            devName = row[0]
            devSerial = row[1]
            cur.execute('select * from clients where devSerial=?', (devSerial,))
            clientRows = cur.fetchall()
            print(devName, len(clientRows))
    else:
        # Obtaining organization ID to pass through devices                             
        cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
        # returns a tuple    
        orgID = cur.fetchone()
        # Obtaining all devices where MX is in the model, and organization matches orgID
        cur.execute('select Name, Serial from devices where orgID=? and model like ?', (orgID[0],'%MX%'))
        rows = cur.fetchall()
        for row in rows:
            devName = row[0]
            devSerial = row[1]
            cur.execute('select * from clients where devSerial=?', (devSerial,))
            clientRows = cur.fetchall() 
            print(devName, len(clientRows))
            global x
            if len(clientRows) > 0 and x == 0:
                x += 1
                for client in clientRows:
                    print(client[3], client[4], client[5])

def pullRoute(ORG_NAME, NET_NAME):
    """ 
    Pulls the necessary data from the dashboard

    :usage: databaseRoute(String of Organization name) -> csv of number of clients per mx         
    :param ORG_NAME: Name of the organization to obtain
    :param NET_NAME: Name of the network to obtain
    :returns: CSV of MX name and number of clients              
    :raises:       
    """
    con =  sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/src/files/meraki2.db')
    cur = con.cursor()
    # essentially get device clients dev.serial for any number of devices
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/clients_per_mx.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Device Name', 'Number of Clients'])
        if ORG_NAME =='/all':
            cur.execute('select Name, Serial from devices where model like ?', ('%MX%',))
            rows = cur.fetchall()
        elif NET_NAME == '':
            cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
            # returns a tuple
            orgID = cur.fetchone()[0]
            cur.execute('select Name, Serial from devices where orgID=? and model like ?', (orgID,'%MX%'))
            rows = cur.fetchall()
        else:
            cur.execute('select ID from networks where Name=?', (NET_NAME,))
            netID = cur.fetchone()[0]
            cur.execute('select Name, Serial from devices where netID=? and model like ?', (netID, '%MX%'))
            rows = cur.fetchall()
        for row in rows:
            devName = row[0]
            devSerial = row[1]
            clients = meraki_functions.getDevClients(devSerial)
            writer.writerow([devName, len(clients)])


def main(argv):
    ORG_NAME = ''
    NET_NAME = ''
    try:
        # obtaining inputs
        opts, args = getopt.getopt(argv, 'hk:o:n:')
    except getopt.GetoptError:
        sys.exit(2)
    # parsing arguments passed through
    for opt, arg in opts:
        if opt == '-k':
            API_KEY = arg
        elif opt == '-o':
            ORG_NAME = arg
        elif opt == '-n':
            NET_NAME = arg
    if API_KEY == '':
        print("-k isn't optional")
        sys.exit(2)
    # default is all organizations
    if ORG_NAME == '':
        ORG_NAME = '/all'
    meraki_functions.createDashboard(API_KEY)
    pullRoute(ORG_NAME, NET_NAME)

if __name__ == '__main__':
    main(sys.argv[1:])
