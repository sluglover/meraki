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
        wan1Stat = ''
        wan2Stat = ''
        lastReported = ''
        lastFailover = ''
        primaryUplink = ''
        activeUplink = ''
        wan1Color = ''
        wan2Color = ''

# Global Variables:
ORG_NAME = ''
NET_NAME = ''

# Functions


# THIS IS DEPENDENT ON WHEN THE DATABASE WAS UPDATED LAST: run right after updating the database daily if utilizing. This isn't updated to the standard that the pull route is due to the desire to obtain everything straight from the dashboard

def databaseRoute():
    """
    Pulls the necessary data for the report from the sqlite database on disk created by ./meraki_database.py. Needs to be ran immediately after updating the database to ensure that the data is up to date. 
    
    :usage: databaseRoute() -> list[device objects]
    :returns: A list of all the MX devices in the form of dev objects
    :raises: Error on str object if ran on its own without main() due to the organization name not being initialized.
    """
    global ORG_NAME
    global NET_NAME
    # list of device classes because it's easier than having to work with all the rows
    devList = []
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/src/files/meraki.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    if ORG_NAME == '/all':
        cur.execute('select Name, Serial, WAN1_Status, WAN2_Status, Last_Active, Last_Failover, Active_Uplink, Primary_Uplink from devices where model like ? or model like ? or model like ? order by Name asc', ('%MX%', '%Z1%', '%OOB%'))
        rows = cur.fetchall()
    elif NET_NAME == '':
        cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
        row = cur.fetchone()[0]
        cur.execute('select Name, Serial, WAN1_Status, WAN2_Status, Last_Active, Last_Failover, Active_Uplink, Primary_Uplink from devices where (model like ? or model like ? or model like ?) and orgID like ? order by Name asc', ('%MX%', '%Z1%', '%OOB%', row))
        rows = cur.fetchall()
    else:
        rows = []
        NET_NAME = '%' + NET_NAME + '%'
        cur.execute('select ID from networks where Name like ? order by Name asc', (NET_NAME,))
        nets = cur.fetchall()
        for net in nets:
            cur.execute('select Name, Serial, WAN1_Status, WAN2_Status, Last_Active, Last_Failover, Active_Uplink, Primary_Uplink from devices where (model like ? or model like ? or model like ?) and netID like ?', ('%MX%', '%Z1%', '%OOB%', net[0]))
            rows += cur.fetchall()
    i = 0
    for row in rows:
        devList.append(c_Dev())
        devList[i].name = row[0]
        devList[i].serial = row[1]
        devList[i].wan1Stat = row[2]
        devList[i].wan2Stat = row[3]
        devList[i].lastReported = parser.isoparse(row[4])
        devList[i].lastFailover = parser.isoparse(row[5])
        devList[i].activeUplink = row[6]
        devList[i].primaryUplink = row[7]
        # green is online/ready , red is offline, gray is not configured/ not connected
        if devList[i].wan1Stat == 'active' or devList[i].wan1Stat == 'ready':
            devList[i].wan1Color = 'green'
        elif  devList[i].wan1Stat == 'failed' or devList[i].wan1Stat == 'not connected':
            devList[i].wan1Color = 'red'
        elif devList[i].wan1Stat == 'not configured':
            devList[i].wan1Color = 'gray'
        else:
            print(devList[i].name, "WAN1", devList[i].wan1Stat)
        if devList[i].wan2Stat == 'active' or devList[i].wan2Stat == 'ready':
            devList[i].wan2Color = 'green'
        elif  devList[i].wan2Stat == 'failed' or devList[i].wan2Stat == 'not connected':
            devList[i].wan2Color = 'red'
        elif devList[i].wan2Stat == 'not configured':
            devList[i].wan2Color = 'gray'
        else:
            print(devList[i].name, "WAN2", devList[i].wan2Stat)
        i+=1
    con.close()
    return devList


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
    orgDict = meraki_functions.getOrgs(ORG_NAME)
    i = 0
    if orgDict == None or orgDict == []:
        return devList
    for org in orgDict.keys():
        orgID = orgDict[org]
        if NET_NAME == '':
            netDict = meraki_functions.getNets(orgID)
        else:
            netDict = meraki_functions.getNets(orgID, NET_NAME)
        for net in netDict.keys():
            netID = netDict[net]
            primaryUplink = meraki_functions.getPrimaryUplink(netID)
            allDevs = meraki_functions.getNetDevs(netID)
            for dev in allDevs:
                if 'MX' in dev.model or 'Z1' in dev.model or 'OOB' in dev.model:
                    devList.append(c_Dev())
                    devList[i].name = dev.name
                    devList[i].serial = dev.serial
                    devList[i].primaryUplink = primaryUplink
                    devList[i].lastFailover = 'N/A'
                    devMap[dev.serial] = i
                    i+=1
    for org in orgDict.keys():
        orgID = orgDict[org]
        uplinks = meraki_functions.getUplinkStatus(orgID)
        for uplink in uplinks:
            if uplink.serial in devMap:
                i = devMap[uplink.serial]
                devList[i].lastReported = uplink.lastReported
                devList[i].wan1Stat = uplink.wan1_stat
                devList[i].wan2Stat = uplink.wan2_stat
                if devList[i].wan1Stat == 'active' or devList[i].wan1Stat == 'ready':
                    devList[i].wan1Color = 'green'
                elif  devList[i].wan1Stat == 'failed' or devList[i].wan1Stat == 'not connected':
                    devList[i].wan1Color = 'red'
                elif devList[i].wan1Stat == 'not configured':
                    devList[i].wan1Color = 'gray'
                if devList[i].wan2Stat == 'active' or devList[i].wan2Stat == 'ready':
                    devList[i].wan2Color = 'green'
                elif  devList[i].wan2Stat == 'failed' or devList[i].wan2Stat == 'not connected':
                    devList[i].wan2Color = 'red'
                elif devList[i].wan2Stat == 'not configured':
                    devList[i].wan2Color = 'gray'
                netID = uplink.netID
                if netID not in netList:
                    netList.append(netID)
        for net in netList:
            uplinkChangeList = meraki_functions.getUplinkChange(net)
            for event in uplinkChangeList:
                i = devMap[event.devSerial]
                devList[i].lastFailover = event.time
                devList[i].activeUplink = event.uplinkActive
        return devList

def toCSV(devList):
    """
    Parses the list of objects to create a csv
    
    :usage: toCSV(list of device objects) -> uplink_log.csv
    :param devList: List of MX device objects
    :returns: CSV containing device names, last reported time, WAN1/WAN2 status, and last failover time
    :raises: 

    """
    if devList != []:
        with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/uplink_log.csv', 'w', newline='\n') as f:
            writer = csv.writer(f, delimiter = ',')
            writer.writerow(['Device Name', 'Last Reported At', 'WAN1 Status', 'WAN2 Status', 'Last Failover At'])
            for dev in devList:
                # for some reason, some devices are still not having lastReported even though it is explicitly stated to be N/A in getUplinkStatus
                writer.writerow([dev.name, dev.lastReported, dev.wan1Stat, dev.wan2Stat, dev.lastFailover])
            time = datetime.datetime.now()
            writer.writerow(['Timestamp', time])

def toEmail(devList):
    """
    Parses the list of objects to create the html table, csv, and send the email through outlook.
    
    :usage: toEmail(list of device objects) -> outlook email
    :param devList: List of MX device objects
    :returns: Email containing html table and csv file
    :raises: _ object has no attribute color if the list isn't populated with device objects with the respective attributes/ a list isn't given. 
    """
    msg = EmailMessage()
    msg['Subject'] = 'Daily Uplink Report'
    msg['From'] = 'ccorby@chiutility.com'
    recipients = ['engineering@baillie.com']
    msg['To'] = ','.join(recipients)
    tableCells = []
    tableRows = ''
    if devList != []:
        for dev in devList:
            row = f"""
            <tr>
            <td>{dev.name}</td>
            <td bgcolor={dev.wan1Color}>{dev.wan1Stat}</td>
            <td bgcolor={dev.wan2Color}>{dev.wan2Stat}</td>
            </tr>
            """
            tableRows += row
    time = datetime.datetime.now()
    msg.add_alternative(f"""
        <html>
          <head>
           <style>
            table, th, td {{
            border: 1px solid black;
            border-collapse:collapse;
            border-style:solid;}}
          </style>
          </head>
          <body>
            <table>
              <tr><th colspan='3'>Status Report of Uplinks for Security Devices</th></tr>
              <tr>
                 <th>Device</th>
                 <th>WAN1</th>
                 <th>WAN2</th>
              {tableRows}
              <tr>
                <td>Timestamp</td>
                <td colspan='2'>{time}</td>
              </tr>
            </table>
            <br>
            <table>
              <tr><th colspan='2'>Legend</th></tr>
              <tr>
                <td bgcolor='green'>Green</td>
                <td>Online</td>
              </tr>
              <tr>
                <td bgcolor='red'>Red</td>
                <td>Offline</td>
              </tr>
              <tr>
                <td bgcolor='gray'>Gray</td>
                <td>Not Configured</td>
              </tr>
            </table>
          </body>
       </html>
    """, subtype='html')
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/uplink_log.csv', 'rb') as f:
        msg.add_attachment(f.read(), maintype='text',subtype='text/csv', filename='uplink_log.csv')
    s = smtplib.SMTP('baillie-com.mail.protection.outlook.com')
    s.send_message(msg)
    s.quit()

def main(argv):
    API_KEY = ''
    global ORG_NAME
    global NET_NAME
    email = False
    csv = False
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
            csv = True
    # default is all organizations
    if ORG_NAME == '':
        ORG_NAME = '/all'
    if API_KEY == '':
        print('oh no')
        devList = databaseRoute()
    else:
        meraki_functions.createDashboard(API_KEY)
        devList = pullRoute()
    if csv == True:
        toCSV(devList)
    if email == True:
        toEmail(devList)
        a=1
if __name__ == '__main__':
    main(sys.argv[1:])
