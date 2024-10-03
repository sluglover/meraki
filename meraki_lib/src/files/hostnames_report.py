#!/usr/bin/env python3
"""
Written by Christopher Corby, 11/27/21

This script writes a CSV detailing the ddns hostnames of MX devices

History:
 11/27/21 cmc Created
 11/27/21 cmc Finished working version
 12/11/21 cmc changed path of csv file and integrated sqlite3

Requirements:
python 3, sqlite 3, meraki_functions, sys, opt

Examples:
 
"""
# Imports

import csv, meraki_functions, sys, getopt, sqlite3

# Functions

##########################################################################
#
# Function: pullRoute
# Description: Creates report of the hostnames through pulling from the database with get requests
# Inputs: Organization name
# Outputs: None
##########################################################################

def pullRoute(ORG_NAME):
    orgDict =  meraki_functions.getOrgs(ORG_NAME)
    if orgDict is None:
        print('Error: No organziations for the sepcified API key')
        sys.exit(2)
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/hostnames.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Device Name', 'Device Model', 'Device Serial', 'Active DDNS Hostname', 'WAN1 Hostname', 'WAN2 Hostname'])
        for org in orgDict.keys():
            orgID = orgDict[org]
            netDict = meraki_functions.getNets(orgID)
            if netDict is not None:
                for net in netDict.keys():
                    netID = netDict[net]
                    devList = meraki_functions.getNetDevs(netID)
                    if devList is not None:
                        for dev in devList:
                            if 'MX' in dev.model:
                                hostDict = meraki_functions.getDDNSConfiguration(dev.serial)
                                writer.writerow([dev.name, dev.model, dev.serial, hostDict['active'], hostDict['wan1'], hostDict['wan2']])

##########################################################################
#
# Function: databaseRoute
# Description: Creates hostnames report through pulling from local sqlite database
# Inputs: Organization name
# Outputs: None
#
##########################################################################

def databaseRoute(ORG_NAME):
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/meraki.db')
    cur = con.cursor()
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/hostnames.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Device Name', 'Device Serial', 'Active DDNS Hostname'])
        if ORG_NAME == '/all':
            # Obtaining all the MX devices through searching if MX is in the model
            cur.execute('select * from devices where model like ?', ('%MX%',))
            rows = cur.fetchall()
            for row in rows:
                writer.writerow([row[2],row[3],row[5]])
        else:
            # Obtaining organization ID to pass through devices
            cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
            # returns a tuple
            orgID = cur.fetchone()
            # Obtaining all devices where MX is in the model, and organization matches orgID
            cur.execute('select * from devices where orgID=? and model like ?', (orgID[0],'%MX%'))
            rows = cur.fetchall()
            for row in rows:
                writer.writerow([row[2],row[3],row[5]])
    con.close()
    
        
def main(argv):
    try:
        # obtaining inputs 
        opts, args = getopt.getopt(argv, 'hk:o:m:')
    except getopt.GetoptError:
        sys.exit(2)
    # parsing arguments passed through 
    for opt, arg in opts:
        if opt == '-k':
            API_KEY = arg
        elif opt == '-o':
            ORG_NAME = arg
    if API_KEY == '':
        print("-k isn't optional")
        sys.exit(2)
    # default is all organizations
    if ORG_NAME == '':
        ORG_NAME = '/all'
    meraki_functions.createDashboard(API_KEY)
    pullRoute(ORG_NAME)

if __name__ == '__main__':
    main(sys.argv[1:])
