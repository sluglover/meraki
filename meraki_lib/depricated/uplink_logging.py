# OUTDATED
# DO NOT USE AS IT INACCURATELY TRACKS THE STATUS DEPENDING ON HOW OFTEN IT'S SCHEDULED


##########################################################################
#
# Author: Christopher Corby
# Date: 11/26/21
# Program: uplink_logging                                                               
# Description: Logs a change in the uplink status for MX devices
#
##########################################################################
#
# History:
# 11/26/21 cmc Created
# 12/11/21 cmc Finished working version
# 12/18/21 cmc Updated the log to only track changes between active and inactive and vice versa with time stamp
# 12/23/21 cmc Fixed bug of finding the difference between datetime objects for logging time a device was down
#
##########################################################################
#
# Prerequisites: python 3, meraki_functions, sqlite3, datetime, csv, sys
#
##########################################################################  

import meraki_functions, sqlite3, datetime, csv, sys, getopt


# Functions

##########################################################################
#
# Function: deviceCheck
# Description: Checks the wan status of all MX devices against the database and logs changes in a CSV file
# Inputs: Organization name
# Outputs: None
#
##########################################################################

def deviceCheck(ORG_NAME):
    # allows datetime/timestamp conversion
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/meraki.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/uplink_log.csv', 'a', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        if ORG_NAME == '/all':
            # obtaining all organization IDs because uplink status is attached to organization
            cur.execute('select ID from organizations')
            # list of tuple IDs in form [(ID,), (ID,)]
            orgs = cur.fetchall()
            for org in orgs:
                orgID = org[0]
                # list of device objects with serial, wan1 status, and wan2 status
                devList = meraki_functions.getUplinkStatus(orgID)
                if devList != None:
                    for dev in devList:
                        cur.execute('select Name, WAN1_Status, WAN1_Last_Active as "w1 [timestamp]", WAN2_Status, WAN2_Last_Active as "w2 [timestamp]" from devices where Serial=?', (dev.serial,))
                        row = cur.fetchone()
                        if row == None:
                            print('New device with serial %s, model %s from network %s. It will be added with the next database update.' % (dev.serial, dev.model, dev.netID))
                        else:
                            # WAN status can be active, ready, not connected, not configured, or failed
                            # change in WAN1 status
                            if row[1] != dev.wan1_stat:
                                # only want to log active to failed and vice versa, but update all status changes 
                                cur.execute('update devices set WAN1_Status=? where Serial=?', (dev.wan1_stat, dev.serial))
                                # wan1 is going from active/ready to failed, not connected, or not configured
                                if (row[1] == 'active' or row[1] == 'ready') and (dev.wan1_stat != 'ready' and dev.wan1_stat != 'active'):
                                    cur.execute('update devices set WAN1_Last_Active=? where Serial=?', (datetime.datetime.now(), dev.serial))
                                    writer.writerow(['Device %s WAN1 went down at %s and is now %s' % (row[0], datetime.datetime.now(), dev.wan1_stat)])
                                # wan1 is going from failed, not connected, or not configured, to active/ready
                                elif (row[1] != 'active' and row[1] != 'ready') and (dev.wan1_stat == 'ready' or dev.wan1_stat == 'active'):
                                    cur.execute('update devices set WAN1_Last_Active=? where Serial=?', (datetime.datetime.now(), dev.serial))
                                    down_time = datetime.datetime.now() - row[2]
                                    writer.writerow(['Device %s WAN1 went up at %s and is now %s. It was inactive for %s' % (row[0], datetime.datetime.now(), dev.wan1_stat, down_time)])
                                    # change in WAN2 status
                            if row[3] != dev.wan2_stat:
                                # only want to log active to failed and vice versa, but update all status changes
                                cur.execute('update devices set WAN2_Status=? where Serial=?', (dev.wan2_stat, dev.serial))
                                # wan2 is going from active/ready to failed, not connected, or not configured
                                if (row[3] == 'active' or row[3] == 'ready') and (dev.wan2_stat != 'ready' and dev.wan2_stat != 'active'):
                                    cur.execute('update devices set WAN2_Last_Active=? where Serial=?', (datetime.datetime.now(), dev.serial))
                                    writer.writerow(['Device %s WAN2 went down at %s and is now %s' % (row[0], datetime.datetime.now(), dev.wan2_stat)])
                                # wan2 is going from failed, not connected, or not configured, to active/ready
                                elif (row[3] != 'active' and row[3] != 'ready') and (dev.wan2_stat == 'ready' or dev.wan2_stat == 'active'):
                                    cur.execute('update devices set WAN2_Last_Active=? where Serial=?', (datetime.datetime.now(), dev.serial))
                                    down_time = datetime.datetime.now() - row[4]
                                    writer.writerow(['Device %s WAN2 went up at %s and is now %s. It was inactive for %s' % (row[0], datetime.datetime.now(), dev.wan2_stat, down_time)])
        else:
            cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
            org = cur.fetchone()
            orgID = org[0]
            devList = meraki_functions.getUplinkStatus(orgID)
            if devList != None:
                for dev in devList:
                    cur.execute('select Name, WAN1_Status, WAN1_Last_Active as "[timestamp]", WAN2_Status, WAN2_Last_Active as "[timestamp]" from devices where Serial=?', (dev.serial,))
                    row = cur.fetchone()
                    if row == None:
                        print('New device with serial %s, model %s from network %s. It will be added with the next database update.' % (dev.serial, dev.model, dev.netID))
                    else:
                        # WAN status can be active, ready, not connected, not configured, or failed
                        # change in WAN1 status
                        if row[1] != dev.wan1_stat:
                            # only want to log active to failed and vice versa, but update all status changes
                            cur.execute('update devices set WAN1_Status=? where Serial=?', (dev.wan1_stat, dev.serial))
                            # wan1 is going from active/ready to failed, not connected, or not configured
                            if (row[1] == 'active' or row[1] == 'ready') and (dev.wan1_stat != 'ready' and dev.wan1_stat != 'active'):
                                cur.execute('update devices set WAN1_Last_Active=? where Serial=?', (datetime.datetime.now(), dev.serial))
                                writer.writerow(['Device %s WAN1 went down at %s and is now %s' % (row[0], datetime.datetime.now(), dev.wan1_stat)])
                            # wan1 is going from failed, not connected, or not configured, to active/ready             
                            elif (row[1] != 'active' and row[1] != 'ready') and (dev.wan1_stat == 'ready' or dev.wan1_stat == 'active'):
                                cur.execute('update devices set WAN1_Last_Active=? where Serial=?', (datetime.datetime.now(), dev.serial))
                                down_time = datetime.datetime.now() - row[2]
                                writer.writerow(['Device %s WAN1 went up at %s and is now %s. It was inactive for %s' % (row[0], datetime.datetime.now(), dev.wan1_stat, down_time)])
                        # change in WAN2 status
                        if row[3] != dev.wan2_stat:
                            # only want to log active to failed and vice versa, but update all status changes
                            cur.execute('update devices set WAN2_Status=? where Serial=?', (dev.wan2_stat, dev.serial))
                            # wan2 is going from active/ready to failed, not connected, or not configured
                            if (row[3] == 'active' or row[3] == 'ready') and (dev.wan2_stat != 'ready' and dev.wan2_stat != 'active'):
                                cur.execute('update devices set WAN2_Last_Active=? where Serial=?', (datetime.datetime.now(), dev.serial))
                                writer.writerow(['Device %s WAN2 went down at %s and is now %s' % (row[0], datetime.datetime.now(), dev.wan2_stat)])
                                # wan2 is going from failed, not connected, or not configured, to active/ready
                            elif (row[3] != 'active' and row[3] != 'ready') and (dev.wan2_stat == 'ready' or dev.wan2_stat == 'active'):
                                cur.execute('update devices set WAN2_Last_Active=? where Serial=?', (datetime.datetime.now(), dev.serial))
                                down_time = datetime.datetime.now() - row[4]
                                writer.writerow(['Device %s WAN2 went up at %s and is now %s. It was inactive for %s' % (row[0], datetime.datetime.now(), dev.wan2_stat, down_time)])
        con.commit()    
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
            ORG_NAME = arg
    if API_KEY == '':
        print("-k isn't optional")
        sys.exit(2)
    # default is all organizations                                                          
    if ORG_NAME == '':
        ORG_NAME = '/all'
    meraki_functions.createDashboard(API_KEY)
    deviceCheck(ORG_NAME)

if __name__ == '__main__':
    main(sys.argv[1:])
