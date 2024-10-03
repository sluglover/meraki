# -*- mode: python; python-indent-offset: 4; -*-

"""
Written by Christopher Corby, 4/8/22

This script writes a CSV of all the meraki devices' firmware version and whether or not it's up to date.

History:
4/8/22 cmc Created

Requirements:
python 3, meraki_functions, csv, sys, getopt

Examples:

"""

import csv, meraki_functions, sys, getopt

def pullRoute(ORG_NAME, NET_NAME):
    """
    """
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/firmware_status.csv', 'w', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow(['Network', 'Device', 'Model', 'Serial', 'MAC', 'Firmware Version', 'Same as network',  'Latest Version'])
        orgDict = meraki_functions.getOrgs(ORG_NAME)
        for org in orgDict.keys():
            orgID = orgDict[org]
            if NET_NAME == '':
                netDict = meraki_functions.getNets(orgID)
            else:
                netDict = meraki_functions.getNets(orgID, NET_NAME)
            for net in netDict.keys():
                netID = netDict[net]
                firmwareInfo = meraki_functions.getNetDevsFirmwareInfo(netID)
                devs = meraki_functions.getNetDevs(netID)
                for dev in devs:
                    product = firmwareInfo[dev.productType]
                    if product.currentFirmware == product.newestFirmware:
                        latest = 'Yes'
                    else:
                        latest = 'No'
                    if product.currentFirmware == dev.firmware:
                        sameAsNet = 'Yes'
                    else:
                        sameAsNet = 'No'
                    writer.writerow([net, dev.name, dev.model, dev.serial, dev.mac, dev.firmware, sameAsNet, latest])

def verboseRoute(ORG_NAME, NET_NAME):
    """                                                                                 
    """
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/firmware_status.csv', 'w', newline='\n') as f:
        with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/firmware_status_verbose.csv', 'w', newline='\n') as g:
            writer = csv.writer(f, delimiter = ',')
            writer2 = csv.writer(g, delimiter = ',')
            writer.writerow(['Network', 'Device', 'Model', 'Serial', 'MAC', 'Firmware Version', 'Same as network',  'Latest Version'])
            writer2.writerow(['Network', 'Device', 'Model', 'Serial', 'MAC', 'Firmware Version', 'Network Firmware Version', 'Latest Firmware Version', 'Same as network',  'Latest Version'])
            orgDict = meraki_functions.getOrgs(ORG_NAME)
            for org in orgDict.keys():
                orgID = orgDict[org]
                if NET_NAME == '':
                    netDict = meraki_functions.getNets(orgID)
                else:
                    netDict = meraki_functions.getNets(orgID, NET_NAME)
                for net in netDict.keys():
                    netID = netDict[net]
                    firmwareInfo = meraki_functions.getNetDevsFirmwareInfo(netID)
                    devs = meraki_functions.getNetDevs(netID)
                    for dev in devs:
                        product = firmwareInfo[dev.productType]
                        if product.currentFirmware == product.newestFirmware:
                            latest = 'Yes'
                        else:
                            latest = 'No'
                        if product.currentFirmware == dev.firmware:
                            sameAsNet = 'Yes'
                        else:
                            sameAsNet = 'No'
                        writer.writerow([net, dev.name, dev.model, dev.serial, dev.mac, dev.firmware, sameAsNet, latest])
                        writer2.writerow([net, dev.name, dev.model, dev.serial, dev.mac, dev.firmware, product.currentFirmware, product.newestFirmware, sameAsNet, latest])

def main(argv):
    API_KEY = ''
    ORG_NAME = ''
    NET_NAME = ''
    try:
        # obtaining inputs    
        opts, args = getopt.getopt(argv, 'k:o:n')
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
    verboseRoute(ORG_NAME, NET_NAME)

if __name__ == '__main__':
    main(sys.argv[1:])
