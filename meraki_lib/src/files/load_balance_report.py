"""
Written by Christopher Corby, 12/18/21

This scripts writes a CSV of network names and their load balancing status

History:
12/28/21 cmc Created and finished working version
3/20/22 cmc Updated to not rely solely on the database, now relies on the dashboard

Requirements:
python 3, meraki_database, meraki_functions, csv, sys, getopt, sqlite3

Examples:
./load_balance_report.py -k API_KEY -o ORG_NAME

"""

import csv, meraki_functions, sys, getopt, sqlite3

# Functions

def sqliteRoute(ORG_NAME):
    """
    Creates a report on load balancing settings for each network on the organization

    :usage: sqliteRoute(ORG_NAME) -> load_balancing.csv
    :param ORG_NAME: Name of the organization to pull load balancing settings for
    :returns: load_balancing.csv in reports directory
    :raises:

    """
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib//src/files/meraki2.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/load_balancing.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Network Name', 'Load Balancing Configuration'])
        if ORG_NAME == '/all':
            # Obtaining all networks
            cur.execute('select Name, ID from networks')
            rows = cur.fetchall()
        else:
            # Obtaining organization ID to pass through to networks
            cur.execute('select ID from organizations where Name=?',(ORG_NAME,))
            # returns a tuple
            orgID = cur.fetchone()[0]
            # Obtaining all networks with that orgID
            cur.execute('select Name, ID from networks where orgID=?', (orgID,))
            rows = cur.fetchall()
        for row in rows:
            net = row[0]
            netID = row[1]
            stat = meraki_functions.getLoadBalancingStatus(netID)
            writer.writerow([net, stat])
    con.close()

def pullRoute(ORG_NAME):
     with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/load_balancing.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Network Name', 'Load Balancing Configuration'])
        orgDict = meraki_functions.getOrgs(ORG_NAME)
        for org in orgDict:
            orgID = orgDIct[org]
            netDict = meraki_functions.getNets(orgID)
            for net in netDict:
                netID = netDict[net]
                stat = meraki_functions.getLoadBalancingStatus(netID)
                writer.writerow([net, stat])

def main(argv):
    ORG_NAME = ''
    try:
        # obtaining inputs                                                               
        opts, args = getopt.getopt(argv, 'k:o:')
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
