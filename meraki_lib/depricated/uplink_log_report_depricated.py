"""
Written by Christopher Corby, 11/26/21

This script tracks the status of MX devices for an organization and creates and sends a html table and a csv file of the data through an email.

History:  
 11/26/21 cmc Created
 12/11/21 cmc Finished working version
 12/18/21 cmc Updated the log to only track changes between active and inactive and vice versa with time stamp
 12/23/21 cmc Fixed bug of finding the difference between datetime objects for logging time a device was down
 12/29/21 cmc Updated to a correct reflection of changes in state
 1/7/22 cmc Started testing html field
 1/8/22 Finished formatting email table. Need time comparison updated along with legend
 1/12/22 Added time comparison
 1/13/22 Finished pull route and working table email
 1/14/22 Changed table to dropdown
 1/21/22 Finished table formatting and created CSV
 1/27/22 Added Z1 devices

Requirements:
python 3, csv, meraki_functions, sqlite3, datetime, sys, getopt, smptlin, dateutil.parser, email.message.EmailMessage

Global variables:
ORG_NAME -> Name of the organization you wish to run the report on
NET_NAME -> Name of the network you wish to run the report on 

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
        color = ''

# Global Variables:
ORG_NAME = ''
NET_NAME = ''

# Functions


# BAILLIE AS AN ORGANIZATION PULLS HFP IN ADDITION TO BLC

##########################################################################
#
# Function: databaseRoute
# Description: Parses the necessary data from the database to format in the email
# Inputs: None
# Outputs: List of device objects
#
##########################################################################

# THIS IS DEPENDENT ON WHEN THE DATABASE WAS UPDATED LAST: run right after updating the database daily if utilizing

def databaseRoute():
    """
    Pulls the necessary data for the report from the sqlite database on disk created by ./meraki_database.py. Needs to be ran immediately after updating the database to ensure that the data is up to date. 
    
    :usage: databaseRoute() -> list[device objects]
    :returns: A list of all the MX devices in the form of dev objects
    :raises: Error on str object if ran on its own without main() due to the organization name not being initialized.
    """
    global ORG_NAME
    global NET_NAME
    # green is good, yellow means it's on the secondary uplink, and red means it's offline
    g = 'green'
    y = 'yellow'
    r = 'red'
    # list of device classes because it's easier than having to work with all the rows
    devList = []
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/meraki.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    if ORG_NAME == '/all':
        cur.execute('select Name, Serial, WAN1_Status, WAN2_Status, Last_Active, Last_Failover, Active_Uplink, Primary_Uplink from devices where model like ? or model like ? or model like ? order by Name asc', ('%MX%', '%Z1%', '%OOB%'))
        rows = cur.fetchall()
    elif NET_NAME == '':
        cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
        row = cur.fetchone()
        cur.execute('select Name, Serial, WAN1_Status, WAN2_Status, Last_Active, Last_Failover, Active_Uplink, Primary_Uplink from devices where (model like ? or model like ? or model like ?) and orgID like ? order by Name asc', ('%MX%', '%Z1%', '%OOB%', row[0]))
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
        # last active is less than the time if it precedes the time
        now = datetime.datetime.now()
        timeDelta = datetime.timedelta(minutes = 5)
        now = now - timeDelta
        # Making the datetime object timezone aware to localized time
        now = now.astimezone(tz = None)
        # checking if the last active was more than 5 minutes ago
        if devList[i].lastReported < now:
            devList[i].color = r
        # this checks if primary uplink == active uplink given that there's two uplinks
        elif devList[i].primaryUplink != devList[i].activeUplink and devList[i].primaryUplink != 'None' and devList[i].activeUplink != 'None':
            if devList[i].activeUplink == 'WAN1' and devList[i].wan1Stat != 'active':
                devList[i].color = y
            elif devList[i].activeUplink == 'WAN2' and devList[i].wan2Stat != 'active':
                devList[i].color = y
            else:
                print (devList[i].name, devList[i].activeUplink, devList[i].wan1Stat, devList[i].wan2Stat)
        else:
            devList[i].color = g
        i+=1
    con.close()
    return devList


##########################################################################
#
# Function: pullRoute
# Description: Parses the data directly from the dashboard. Requires API key to initiate, unlike the database. It is independent of the database's last update though
# Inputs: Organization name
# Outputs: List of device objects
#
##########################################################################

def pullRoute():
    """                                                                                    
    Pulls the necessary data for the report from the meraki dashboard. Takes significantly more time than the databaseRoute, but is independent of running the database. 

    :usage: pullRoute() -> list[device objects]
    :returns: A list of all the MX devices in the form of dev objects
    :raises: Error on str object if ran on its own without main() due to the dashboard key and organization name not being initalized.
    """

    global ORG_NAME
    global NET_NAME
    g = 'green'
    y = 'yellow'
    r = 'red'
    devList = []
    # maps serial to index in devList
    devMap = {}
    netList = []
    # quicker method is to pull some info from sqlite table as shown. If wanting to purely pull from the dashboard, use getOrgs to obtain the organization IDs, getNets to obtain the network IDs getOrgDevs to get device names, and getPrimaryUplink for primary uplink
    con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/meraki.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    if ORG_NAME == '/all':
        rows = cur.execute('select ID from organizations')
        # move all this out of the if/else if going back to organizations
        orgs = cur.fetchall()
        i = 0
        for org in orgs:
            # sqlite returns a tuple if indivdual column pulled 
            orgID = org[0]
            cur.execute('select Name, Serial, Primary_Uplink from devices where orgID=? and (model like ? or model like ? or model like ?)', (orgID,'%MX%', '%Z1%', '%OOB%'))
            devs = cur.fetchall()
            for dev in devs:
                devList.append(c_Dev())
                devList[i].name = dev[0]
                devList[i].serial = dev[1]
                devList[i].primaryUplink = dev[2]
                devList[i].color = g
                devList[i].lastFailover = 'N/A'
                devMap[dev[1]] = i
                i+=1
    elif NET_NAME == '':
        rows = cur.execute('select ID from organizations where Name=?', (ORG_NAME))
        orgs = cur.fetchall()
        i = 0
        for org in orgs:
            orgID = org[0]
            cur.execute('select Name, Serial, Primary_Uplink from devices where orgID=? and (model like ? or model like ? or model like ?)', (orgID,'%MX%', '%Z1%', '%OOB%'))
            devs = cur.fetchall()
            for dev in devs:
                devList.append(c_Dev())
                devList[i].name = dev[0]
                devList[i].serial = dev[1]
                devList[i].primaryUplink = dev[2]
                devList[i].color = g
                devList[i].lastFailover = 'N/A'
                devMap[dev[1]] = i
                i+=1
    else:
        # allowing net_name to be substring in sqlite search
        NET_NAME = '%' + NET_NAME + '%'
        # just going by organization leads to all the HFP networks too
        cur.execute('select ID from organizations where Name=?', (ORG_NAME,))
        orgs = cur.fetchall()
        # quick fix is to just pull all devices for networks that contain BLC. can be done for HFP too as an option instead of organization name??
        cur.execute('select ID from networks where Name like ? order by Name asc', (NET_NAME,))
        rows = cur.fetchall()
        i = 0
        for row in rows:
            cur.execute('select Name, Serial, Primary_Uplink from devices where (model like ? or model like ? or model like ?) and netID=? order by Name asc', ('%MX%', '%Z1%', '%OOB%', row[0]))
            devs = cur.fetchall()
            for dev in devs:
                devList.append(c_Dev())
                devList[i].name = dev[0]
                devList[i].serial = dev[1]
                devList[i].primaryUplink = dev[2]
                devList[i].color = g
                devList[i].lastFailover = 'N/A'
                devMap[dev[1]] = i
                i+=1
    for org in orgs:
        # sqlite returns a tuple if indivdual column pulled
        orgID = org[0]
        uplinks = meraki_functions.getUplinkStatus(orgID)
        now = datetime.datetime.now()
        timeDelta = datetime.timedelta(minutes = 5)
        now = now - timeDelta
        # Making the datetime object timezone aware to localized time
        now = now.astimezone(tz = None)
        for uplink in uplinks:
            if uplink.serial in devMap:
                index = devMap[uplink.serial]
                devList[index].lastReported = uplink.lastReported
                if uplink.lastReported < now:
                    devList[index].color = r
                devList[index].wan1Stat = uplink.wan1_stat
                devList[index].wan2Stat = uplink.wan2_stat
                netID = uplink.netID
                if netID not in netList:
                    netList.append(netID)
        for net in netList:
            uplinkChangeList = meraki_functions.getUplinkChange(net)
            for event in uplinkChangeList:
                index = devMap[event.devSerial]
                devList[index].lastFailover = event.time
                devList[index].activeUplink = event.uplinkActive
                if devList[index].primaryUplink != devList[index].activeUplink and devList[index].primaryUplink != 'None' and devList[index].activeUplink != 'None':
                    if devList[index].primaryUplink == 'WAN1' and devList[index].wan1Stat != 'active':
                        devList[index].color = y
                    elif devList[index].primaryUplink == 'WAN2' and devList[index].wan2Stat != 'active':
                        devList[index].color = y
                    else:
                        print(devList[index].name, devList[index].primaryUplink, devList[index].wan1Stat, devList[index].wan2Stat)
        return devList



##########################################################################
#
# Function: sendEmail
# Description: Formats HTML table and sends a SMTP email containing the table
# Inputs: List of device objects and mapping of device serial to its index in the list and designated color
# Outputs: Email if that counts. Nothing local
#
##########################################################################

# as of right now, there are 64 MX devices in total for baillie network (organization)
# 33 MX devices for BLC

def sendEmail(devList):
    """
    Parses the list of objects to create the html table, csv, and send the email through outlook.
    
    :usage: sendEmail(list of device objects) -> outlook email
    :param devList: List of MX device objects
    :returns: Email containing html table and csv file
    :raises: _ object has no attribute color if the list isn't populated with device objects with the respective attributes/ a list isn't given. 
    """
    msg = EmailMessage()
    msg['Subject'] = 'Daily Uplink Report'
    msg['From'] = 'ccorby@chiutility.com'
    msg['To'] = 'ccorby@baillie.com'
    tableCells = []
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/uplink_log.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Device Name', 'Last Reported At', 'WAN1 Status', 'WAN2 Status', 'Last Failover At'])
        tableRows = ''
        time = datetime.datetime.now()
        for dev in devList:
            row = f"""
            <tr>
            <td>{dev.name}</td>
            <td>{dev.wan1Stat}</td>
            <td>{dev.wan2Stat}</td>
            </tr>
            """
            tableRows += row
            writer.writerow([dev.name, dev.lastReported, dev.wan1Stat, dev.wan2Stat, dev.lastFailover])
        writer.writerow([f"Timestamp:{time}"])
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
            <p>This is an automated report sent by Christopher Corby.</p>
            <p>The attached csv file contains the specifics for each device.</p>
            <table>
              <tr><th colspan='3'>Status Report of Uplinks for MX Devices</th></tr>
              <tr>
                 <th>Device</th>
                 <th>WAN1</th>
                 <th>WAN2</th>
              {tableRows}
              <tr>
                <td colspan='3'>Timestamp:{time}</td>
              </tr>
            </table>
            <table>
              <tr><th colspan='2'>Legend</th></tr>
              <tr>
                <td bgcolor='green'>Green</td>
                <td>Online</td>
              </tr>
              <tr>
                <td bgcolor='red'; style='color:white'>Red</td>
                <td>Offline</td>
              </tr>
              <tr>
                <td bgcolor='gray'; style='color:white'>Gray</td>
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
    # can pick to either pull directly from the dashboard or pull from the local sqlite database. the latter is quicker
    try:
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
    # default is all organizations
    if ORG_NAME == '':
        ORG_NAME = '/all'
    if API_KEY == '':
        devList = databaseRoute()
    else:
        meraki_functions.createDashboard(API_KEY)
        devList = pullRoute()
    sendEmail(devList)

if __name__ == '__main__':
    main(sys.argv[1:])
