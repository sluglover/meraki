"""
Written by Christopher Corby, 11/20/21

This file creates and updates a sqlite3 database containing information for the meraki ecosystem: organizations, networks, devices, and clients

History:                                                                               
 11/20/21 cmc Created                                                                  
 11/25/21 cmc Finished create method, update method in the works                       
 12/4/21  cmc Merged create and update method into one function                        
 12/5/21  cmc Finished working version                                                 
 12/11/21 cmc Updated paths for csv and database                                       
 12/18/21 cmc Added columns WAN1_Last_Active and WAN2_Last_Active in device table      
 12/23/21 cmc Added columns WAN1_IP and WAN2_IP in device table                        
 12/28/21 cmc Added column load balancing configuration in network table               
 12/30/21 cmc Added column primary uplink in network table                             
 12/31/21 cmc Added table of subnets                                                  
 1/3/22 cmc Added table of clients
 1/6/22 cmc Added column of Last_Active to device table, removed WAN1 & WAN2 Last Active
 1/7/22 cmc Moved primary uplink column to device table instead of network table 
 2/4/22 cmc Revamped tables to exclusively include what should be static information and allowed for single table to be created/updated

Requirements: 
python 3, meraki_functions, sqlite3, sys, getopt, csv

Global variables:
ORG_NAME -> Name of the organization
NET_NAME -> Name of the network

Examples:
Running the script will create the database if not created. Otherwise, it will update all necessary fields. 

./meraki_database.py -k API_KEY -o ORGANIZATION_NAME -n NETWORK_NAME -> Creates the sqlite database meraki2.db and creates a changelog under the reports directory
"""

import meraki_functions, sqlite3, sys, getopt, csv, datetime

# Global Variables:
ORG_NAME = ''
NET_NAME = ''


# Functions

def createDatabase():
    createOrgs()
    createNets()
    createDevs()

def createOrgs():
    """
    Creates and/or updates the organizations sqlite table. Table is populated with name and ID of each organization.

    :usage: createOrgs()
    :returns: Nothing, but the organizations table is added to the database.
    :raises: Attribute error if dashboard connection isn't initiated
             
    :meta private:
    """
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/src/files/meraki2.db')
    cur = con.cursor()
    cur.execute('create table if not exists organizations (Name, ID)')
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/database_change_log2.csv', 'a', newline='\n') as f:
        writer = csv.writer(f, delimiter=',')
        orgDict = meraki_functions.getOrgs()
        for org in orgDict.keys():
            orgID = orgDict[org]
            cur.execute('select * from organizations where ID=?', (orgID,))
            row = cur.fetchone()
            if row == None:
                cur.execute('insert into organizations values (?,?)', (org, orgID))
                writer.writerow(['%s Organization %s has been added to the database' % (datetime.datetime.now(), org)])
            elif row[0] != org:
                cur.execute('update organizations set Name=? where ID=?', (org, orgID))
                writer.writerow(['%s Organization %s has had its name updated from %s to %s' % (datetime.datetime.now(), orgID, row[0], org)])
    con.commit()
    con.close()

def createNets():
    """
    Creates and/or updates the networks sqlite table. Table is populated with organization ID, network ID, and network name.
    
    :usage: createNets() Run after running createOrgs() for this to work
    :returns: Nothing, but the networks table is added to the database.
    :raises: Nonetype is not iterable if dashboard connection isn't initiated
             sqlite3 error no such table organizations if createOrgs() hasn't been run at least once to create the organizations table
    :meta private:
    """
    global ORG_NAME
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/src/files/meraki2.db')
    cur = con.cursor()
    cur.execute('create table if not exists networks (orgID, Name, ID)')
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/database_change_log2.csv', 'a', newline='\n') as f:
        writer = csv.writer(f, delimiter=',')
        if ORG_NAME == '':
            cur.execute('select ID from organizations')
            rows = cur.fetchall()
        else:
            cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
            rows = cur.fetchall()
        for row in rows:
            orgID = row[0]
            netDict = meraki_functions.getNets(orgID)
            for net in netDict:
                netID = netDict[net]
                cur.execute('select * from networks where ID=?', (netID,))
                netRow = cur.fetchone()
                if netRow == None:
                    cur.execute('insert into networks values (?,?,?)', (orgID, net, netID))
                    writer.writerow(['%s Network %s has been added to the database' % (datetime.datetime.now(), net)])
                else:
                    if netRow[1] != net:
                        cur.execute('update networks set Name=? where ID=?', (net, netID))
                        writer.writerow(['%s Network %s has had its name updated from %s to %s' % (datetime.datetime.now(), netID, netRow[1], net)])
                    if netRow[0] != orgID:
                        cur.execute('update networks set orgID=? where ID=?', (orgID, netID))
                        writer.writerow(['%s Network %s has been moved from organization %s to %s' % (datetime.datetime.now(), net, netRow[0], orgID)])
    con.commit()
    con.close()
            

def createDevs():
    """
    Creates and/or updates the devices sqlite table. Table is populated with organization ID, network ID, name, serial, and model.

    :usage: createDevs() Run after running either createOrgs() or createNets() for this to work
    :returns: Nothing, but the devices table is added to the database.
    :raises: Nonetype is not iterable error if dashboard connection isn't initiated
             sqlite3 error no such table organizations if createOrgs() hasn't been run at least once to create the organizations table if creating all devices or for specific organization
             sqlite3 error no such table networks if createNets() hasn't been run at least once to create networks table if creating devices for a specifc network 
    :meta private:
    """
    global ORG_NAME
    global NET_NAME
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/src/files/meraki2.db')
    cur = con.cursor()
    cur.execute('create table if not exists devices (orgID, netID, Model, Name, Serial)')
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/database_change_log2.csv', 'a', newline='\n') as f:
        writer = csv.writer(f, delimiter=',')
        if NET_NAME == '':
            if ORG_NAME == '':
                cur.execute('select ID from organizations')
                rows = cur.fetchall()
            else:
                cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
                rows = cur.fetchall()
            if rows != None:
                for row in rows:
                    orgID = row[0]
                    devs = meraki_functions.getOrgDevs(orgID)
                    for dev in devs:
                        cur.execute('select * from devices where Serial=?', (dev.serial,))
                        devRow = cur.fetchone()
                        if devRow == None:
                            cur.execute('insert into devices values (?,?,?,?,?)', (orgID, dev.netID, dev.model, dev.name, dev.serial))
                            writer.writerow(['%s Device %s has been added to the database' % (datetime.datetime.now(), dev.name)])
                        else:
                            if devRow[3] != dev.name:
                                cur.execute('update devices set Name=? where Serial=?', (dev.name, dev.serial))
                                writer.writerow(['%s Device %s has had its name updated from %s to %s' % (datetime.datetime.now(), dev.serial, devRow[3], dev.name)])
                            if devRow[0] != orgID:
                                cur.execute('update devices set orgID=? where Serial=?', (orgID, dev.serial))
                                writer.writerow(['%s Device %s has been moved from organization %s to %s' % (datetime.datetime.now(), dev.name, devRow[0], orgID)])
                            if devRow[1] != dev.netID:
                                cur.execute('update devices set netID=? where Serial=?', (dev.netID, dev.serial))
                                writer.writerow(['%s Device %s has been moved from network %s to %s' % (datetime.datetime.now(), dev.name, devRow[1], dev.netID)])
                            if devRow[2] != dev.model:
                                cur.execute('update devices set Model=? where Serial=?', (dev.model, dev.serial))
                                writer.writerow(['%s Device %s has had its model changed from %s to %s' % (datetime.datetime.now(), dev.name, devRow[2], dev.model)])
        else:
            cur.execute('select orgID, ID from networks where Name=?', (NET_NAME, ))
            row = cur.fetchone()
            if row != None:
                netID = row[1]
                orgID = row[0]
                devs = meraki_functions.getNetDevs(netID)
                for dev in devs:
                    cur.execute('select * from devices where Serial=?', (dev.serial,))
                    devRow = cur.fetchone()
                    if devRow == None:
                        cur.execute('insert into devices (?,?,?,?,?)', (orgID, netID, dev.model, dev.name, dev.serial))
                        writer.writerow(['%s Device %s has been added to the database' % (datetime.datetime.now(), dev.name)])
                    else:
                        if row[3] != dev.name:
                            cur.execute('update devices set Name=? where Serial=?', (dev.name, dev.serial))
                            writer.writerow(['%s Device %s has had its name updated from %s to %s' % (datetime.datetime.now(), dev.serial, row[3], dev.name)])
                        if row[0] != orgID:
                            cur.execute('update devices set orgID=? where Serial=?', (orgID, dev.serial))         
                            writer.writerow(['%s Device %s has been moved from organization %s to %s' % (datetime.datetime.now(), dev.name, row[0], orgID)])
                        if row[1] != netID:
                            cur.execute('update devices set netID=? where Serial=?', (netID, dev.serial))       
                            writer.writerow(['%s Device %s has been moved from network %s to %s' % (datetime.datetime.now(), dev.name, row[1], netID)])
                        if row[2] != dev.model: 
                            cur.execute('update devices set Model=? where Serial=?', (dev.model, dev.serial))         
                            writer.writerow(['%s Device %s has had its model changed from %s to %s' % (datetime.datetime.now(), dev.name, row[2], dev.model)])
        con.commit()
        con.close()


def main(argv):
    global ORG_NAME
    global NET_NAME
    API_KEY = ''
    try:
        # obtaining inputs
        opts, args = getopt.getopt(argv, 'k:o:n:')
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
    meraki_functions.createDashboard(API_KEY)
    createDatabase()

if __name__ == '__main__':
    main(sys.argv[1:])
