#!/usr/bin/env python3

"""
Written by Christopher Corby, 11/26/21

This script tracks the status of MX and Z1 devices for an organization and creates and sends a html table and a csv file of the data through an email.

History:  
 11/26/21 cmc Created
 12/11/21 cmc Finished working version
 12/18/21 cmc Updated the log to only track changes between active and inactive and vice versa with time stamp
 12/23/21 cmc Fixed bug of finding the difference between datetime objects for logging time a device was down
 12/29/21 cmc Updated to a correct reflection of changes in state
 1/7/22 cmc Started testing html field
 1/8/22 cmc Finished formatting email table. Need time comparison updated along with legend
 1/12/22 cmc Added time comparison
 1/13/22 cmc Finished pull route and working table email
 1/14/22 cmc Changed table to dropdown
 1/21/22 cmc Finished table formatting (back to table from dropdown) and created CSV
 1/27/22 cmc Added Z1 devices
 1/28/22 cmc Changed table to show WAN1 and WAN2 
 2/26/22 cmc Changed primary uplink to pull from dashboard instead of database
 3/5/22 cmc Changed Not connected from gray to red
 3/11/22 cmc Added option for BLC/HFP in network flag
 3/20/22 cmc Removed blurb about the email
 4/1/22 cmc FINALLY moved csv to a seperate function
 12/4/22 cmc Added network name and wan IPs to the reporting. Additionally, the csv file in the email is finally optinal through a global CSV flag. didn't think of doing this before
 2/24/23 cmc Added public IPs and gateways for WAN1 and 2
 7/21/23 cmc Added error handling for empty networks 
Requirements:
python 3, csv, meraki_functions, sqlite3, datetime, sys, getopt, smtplib, dateutil.parser, email.message.EmailMessage

Global variables:
ORG_NAME -> Name of the organization you wish to run the report on
NET_NAME -> Name of the network you wish to run the report on. Can be a group such as BLC or HFP 

Examples:
Running the script will create and send the email. 

./uplink_log_report.py -k API_KEY -o ORGANIZATION_NAME -n NETWORK_NAME -> -o and -n are oprtional to have a more specific report. default is all for each. 

"""

import csv, meraki_functions, sqlite3, datetime, sys, getopt, smtplib
from dateutil import parser
from email.message import EmailMessage

# Classes:

class c_Dev:
    def __init__(self):
        serial = ''
        name = ''
        net = ''
        wan1Ip = ''
        wan1PubIp = ''
        wan1Gatway = ''
        wan2Ip = ''
        wan2PubIp = ''
        wan2Gateway = ''
        wan1Stat = ''
        wan2Stat = ''
        lastReported = ''
        lastFailover = ''
        primaryUplink = ''
        activeUplink = ''
        wan1Color = ''
        wan2Color = ''
        uplink = ''

# Global Variables:
ORG_NAME = ''
NET_NAME = ''
CSV = False

# Functions


# THIS IS DEPENDENT ON WHEN THE DATABASE WAS UPDATED LAST: run right after updating the database daily if utilizing. This isn't updated to the standard that the pull route is due to the desire to obtain everything straight from the dashboard

def pullRoute():
    """
    Pulls strictly from the dashboard.
    """
    global ORG_NAME
    global NET_NAME
    devList = []
    # maps serial to index in devList 
    devMap = {}
    netList = []
    errorList = []
    orgError, orgDict = meraki_functions.getOrgs(ORG_NAME)
    if orgError != '':
        errorList.append(orgError)
    i = 0
    if orgDict == None or orgDict == []:
        return(errorList, devList)
    for org in orgDict.keys():
        orgID = orgDict[org]
        if NET_NAME == '':
            netError, netDict = meraki_functions.getNets(orgID)
        else:
            netError, netDict = meraki_functions.getNets(orgID, NET_NAME)
        if netError != '':
            errorList.append(netError)
            return(errorList, devList)
        if netDict is not None:
            for net in netDict.keys():
                netID = netDict[net]
                primaryUplink = meraki_functions.getPrimaryUplink(netID)
                allDevs = meraki_functions.getNetDevs(netID)
                if allDevs is not None:
                    for dev in allDevs:
                        if 'MX' in dev.model or 'Z1' in dev.model or 'OOB' in dev.model:
                            devList.append(c_Dev())
                            uplinkSettings = meraki_functions.getDeviceUplinkSettings(dev.serial)
                            devList[i].name = dev.name
                            devList[i].serial = dev.serial
                            devList[i].primaryUplink = primaryUplink
                            devList[i].lastFailover = 'N/A'
                            devList[i].net = net
                            devList[i].uplink = uplinkSettings
                            devMap[dev.serial] = i
                            i+=1
    for org in orgDict.keys():
        orgID = orgDict[org]
        uplinks = meraki_functions.test(orgID)
        for uplink in uplinks:
            if uplink.serial in devMap:
                i = devMap[uplink.serial]
                devList[i].wan1Ip = uplink.wan1_ip
                devList[i].wan2Ip = uplink.wan2_ip
        return(errorList, devList)

def toCSV(errorList, devList):
    """
    Parses the list of objects to create a csv
    
    :usage: toCSV(list of potential errors, list of device objects) -> uplink_log.csv
    :param devList: List of MX device objects
    :returns: CSV containing device names, last reported time, WAN1/WAN2 status, and last failover time
    :raises: 

    """
    if devList != []:
        with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/uplink_test_log.csv', 'w', newline='\n') as f:
            writer = csv.writer(f, delimiter = ',')
            writer.writerow(['Device Name', 'Network Name', 'Uplink1', 'Uplink2', 'Settings'])
            for dev in devList:
                # for some reason, some devices are still not having lastReported even though it is explicitly stated to be N/A in getUplinkStatus
                writer.writerow([dev.name, dev.net, dev.wan1Ip, dev.wan2Ip, dev.uplink])
            time = datetime.datetime.now()
            writer.writerow(['Timestamp', time])
    else:
          with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/uplink_test_log.csv', 'w', newline='\n') as f:
            writer = csv.writer(f, delimiter = ',')
            writer.writerow(['Here are the errors:'] + errorList)
            time = datetime.datetime.now()
            writer.writerow(['Timestamp', time])

def main(argv):
    API_KEY = ''
    global ORG_NAME
    global NET_NAME
    email = False
    global CSV
    # can pick to either pull directly from the dashboard or pull from the local sqlite database. the latter is quicker
    try:
        opts, args = getopt.getopt(argv, 'cek:o:n:')
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
        elif opt == '-e':
            email = True
        elif opt == '-c':
            CSV = True
    # default is all organizations
    if ORG_NAME == '':
        ORG_NAME = '/all'
    if API_KEY == '':
        print('oh no')
        errorList, devList = databaseRoute()
    else:
        meraki_functions.createDashboard(API_KEY)
        errorList, devList = pullRoute()
    if CSV == True:
        toCSV(errorList, devList)
if __name__ == '__main__':
    main(sys.argv[1:])
