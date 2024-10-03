# -*- mode: python; python-indent-offset: 4; -*-

# Remove that top line if not using emacs. Emacs hated this script and turned indents into spaces

"""
Written by Christopher Corby, 11/27/21

This file creates a csv of all the SNMP settings of an organization

History:
 11/27/21 cmc Created
 11/27/21 cmc Finished working version
 12/11/21 cmc Integrated sqlite3 database to improve execution time
 4/8/22 cmc Fixed the issue of having net flow capitialized when it shouldn't be

Requirements:
python 3, csv, sqlite3, getopt, sys, meraki_functions

Examples
"""
# Imports

import csv, meraki_functions, sys, getopt, sqlite3

# Functions

def pullRoute(ORG_NAME):
    """
    Pulls data directly from the dashboard and writes to a csv.

    :usage: pullRoute(String of ORG_NAME) -> SNMP_settings.csv
    :param ORG_NAME: Name of the organziation. Default is all
    :returns: SNMP_settings.csv in the reports directory
    :raises: Error on str object if dashboard key isn't initialized

    """
    orgDict =  meraki_functions.getOrgs(ORG_NAME)
    if orgDict is None:
        print('Error: No organziations for the sepcified API key')
        sys.exit(2)
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/SNMP_settings.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Organization', 'Network', 'V1/V2', 'V3', 'Community String', 'Network Traffic Reporting' 'Netflow Collector IP', 'Netflow Collector Port'])
        for org in orgDict.keys():
            orgID = orgDict[org]
            SNMP_dict = meraki_functions.getOrgSNMP(orgID)
            netDict = meraki_functions.getNets(orgID)
            if netDict is None:
                print("No networks for organization %s" % org.name)
            else:
                for net in netDict:
                    netID = netDict[net]
                    communityString = meraki_functions.getNetCommunityString(netID)
                    netFlowDict = meraki_functions.getNetflow(netID)
                    writer.writerow([org, net, SNMP_dict['v2'], SNMP_dict['v3'], communityString, netFlowDict['trafficReporting'], netFlowDict['collectorIP'], netFlowDict['collectorPort']])

def sqliteRoute(ORG_NAME):
    """
    Creates the report from pulling exclusively from the sqlite database. Do not use without running the database first, as this one hasn't been updated in a while.

    """
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/meraki.db')
    cur = con.cursor()
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/SNMP_settings.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Network', 'V1/V2', 'V3', 'Community String', 'Network Traffic Reporting' 'Netflow Collector IP', 'Netflow Collector Port'])
        if ORG_NAME == '/all':
            cur.execute('select * from organizations')
            orgs = cur.fetchall()
            # v2 and v3 SNMP setting are at organization level
            for org in orgs:
                orgID = org[1]
                v2 = org[2]
                v3 = org[3]
                cur.execute('select * from networks where orgID=?', (orgID,))
                nets = cur.fetchall()
                for net in nets:
                    writer.writerow([net[1], v2, v3, net[3], net[4], net[5], net[6]])
        else:
            cur.execute('select * from organizations where Name=?', (ORG_NAME,))
            org = cur.fetchone()
            orgID = org[1]
            v2 = org[2]
            v3 = org[3]
            cur.execute('select * from networks where orgID=?',(orgID,))
            nets = cur.fetchall()
            for net in nets:
                writer.writerow([net[1], v2, v3, net[3], net[4], net[5], net[6]])
    con.close()

def main(argv):
    # obtaining inputs
    try:
        opts, args = getopt.getopt(argv, 'k:o:')
    except getopt.GetoptError:
        sys.exit(2)
    # parsing arguments
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
