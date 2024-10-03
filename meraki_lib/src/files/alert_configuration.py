"""
Written by Christopher Corby, 11/27/21

This script creates two csv files -> one of the all the alerts available and their recipients, and another of just the enabled alerts

History:
 11/27/21 cmc Created and finished working version

Requirements: python 3, csv, meraki_functions, sys, getopt

Examples:
Running this script will create the report in the reports directory.
 
./alert_configuration.py -k API_KEY -o ORGANIZATION_NAME 
"""

import csv, meraki_functions, sys, getopt

def main(argv):
     try:
        opts, args = getopt.getopt(argv, 'hk:o:m:')
     except getopt.GetoptError:
        sys.exit(2)
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
     orgDict =  meraki_functions.getOrgs(ORG_NAME)
     if orgDict is None:
          print('Error: No organziations for the sepcified API key')
          sys.exit(2)
     with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/all_alert_settings.csv', 'w', newline='\n') as f, open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/configured_alert_settings.csv', mode='w', newline='\n') as g:
          writer = csv.writer(f, delimiter = ',')
          writer2 = csv.writer(g, delimiter = ',')
          writer.writerow(['Network Name', 'Alert Type', 'Enabled Status', 'Default Recipients', 'Specific Recipients'])
          writer2.writerow(['Network Name', 'Alert Type', 'Default Recipients', 'Specific Recipients'])
          for org in orgDict.keys():
               orgID = orgDict[org]
               netDict = meraki_functions.getNets(orgID)
               for net in netDict.keys():
                    netID = netDict[net]
                    alertList = meraki_functions.getAlertsandRecipients(netID)
                    for alert in alertList:
                         if alert.enabled ==  'Enabled':
                              writer2.writerow([net, alert.alertType, alert.default, alert.emails])
                         writer.writerow([net, alert.alertType, alert.enabled, alert.default, alert.emails])

if __name__ == '__main__':
    main(sys.argv[1:])
