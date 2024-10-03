#!/usr/bin/env python3
# need firmware_status and firmware_status_verbose
import meraki, meraki_functions, sqlite3, time, requests, smtplib, datetime, csv, json, random
from email.message import EmailMessage

if [] == None:
    print('Suc')
else:
    print('No')
#con = sqlite3.connect('/home/ccorby/meraki/project1_ccorby/meraki_lib/src/files/meraki2.db')
#cur = con.cursor()
#meraki_functions.createDashboard('fc24863c03b8db18a94ce4b8833859b79e864534')
#cur.execute('select ID from organizations where Name=?', ('Baillie Network',))
#orgID = cur.fetchone()[0]
#cur.execute('select Name, ID from networks where orgID=?', (orgID,))
#nets = cur.fetchone()
#netID = nets[1]
#print(meraki_functions.getConnectDestinations(netID))
#con.close()
# r = meraki_functions.getActionBatches(orgID)
# print(r)
#a = datetime.datetime.now().isoformat(timespec='seconds') + '_backup'
#print(a)
# spec = requests.get('https://api.meraki.com/api/v1/openapiSpec', headers={'X-Cisco-Meraki-API-Key': 'fc24863c03b8db18a94ce4b8833859b79e864534'}).json()
# for path in spec['paths']:
#     function = spec['paths'][path]
#     if 'get' in function and ('post' in function or 'put' in function) and 'parameters' in function['get']:
#         if 'History' not in function['get']['operationId'] and 'Usage' not in function['get']['operationId']:
#             paramList = []
#             for p in function['get']['parameters']:
#                 if 'required' in p:
#                     paramList.append(p['name'])
#             if len(paramList) == 2:
#                 if 'ssid' in path:
#                     print(path)
#                     print(function['get']['operationId'])
#                     for p in paramList:
#                         print(p['name'])
#                     print('-------')

