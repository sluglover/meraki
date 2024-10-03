#!/usr/bin/env python3
"""
Written by Christopher Corby, 4/16/22

This is a script to back up the dashboard

History:
4/16/22 cmc Created
4/29/22 cmc Added most of network/organization functionality. Need to fix the directories though
5/1/22 cmc Added most of device functionality
5/4/22 cmc Realized object attribute issue was that wireless wasn't in path
5/6/22 cmc Added thread sleeping algorithm
5/6/22 cmc Added check to make sure that no devices have a '/' in the name (BALT WASH)
5/26/22 cmc Added ssid and client functionality. Considered finished (for now)

Requirements:
python 3, meraki, datetime, sys, getopt, meraki.aio, json, os, requests, asyncio

Global Variables:
MAIN_PATH -> Essentially the back up directory for each async event to base off of. I personally like having it here to ease things

Examples:

"""
# TODO: restore backup through storing the update functions in a csv and then reading them


# framework
# Start by creating a backup directory
# Go async by organziation, network, device, etc
# If path doesn't exist, create path
# Populate destination with respective json files in form YYYYMMDD-HHMMSS_FILENAME
# Where filename will be something like org_baillie_network or net_blc_allegany_NY_potter or MX_deviceName

# Imports

import asyncio, meraki.aio, sys, getopt, meraki, datetime, json, os, requests, csv, random

# Global variables

MAIN_PATH = ''
AIOMERAKI = ''

# Classes

class c_Function:
    def __init__(self, path, name, parameters):
        self.path = path
        self.name = name
        self.parameters = parameters

# I proabably want an external function for creating a file/path, 

# each organization is a thread
# each network and organization function is a thread that can run once the original organization thread is done (children of original thread)
# each device is then a child of the network thread

# requests is easier to obtain the openapi spec due to the python module requiring an organization id (both have the exact same output. tested through putting both responses to CSVs and running diff)

# essentially this sets up all the async calls. i need a respective function for each async call I want to do
async def initAsync(API_KEY, orgList, netList, devList, ssidList, clientList):
    """
    Initializes the async instance and waits for all the async functions
    """
    global AIOMERAKI
    async with meraki.aio.AsyncDashboardAPI(API_KEY, base_url='https://api.meraki.com/api/v1', suppress_logging=True, maximum_concurrent_requests=10, maximum_retries=3) as aiomeraki:
        AIOMERAKI = aiomeraki
        orgs = await AIOMERAKI.organizations.getOrganizations()
        for org in orgs:
            # It's easiest to just pass along the organization name due to the ID being what's stored in the lower level objects. Note that this backup directory branches by names 
            orgName = org['name'].replace(' ', '_')
            await objBackup(org)
            orgTasks = [objFunction(org, function) for function in orgList]
            for task in asyncio.as_completed(orgTasks):
                await task
            print(f'all org tasks completed for {orgName}')
            nets = await aiomeraki.organizations.getOrganizationNetworks(org['id'])
            for net in nets:
                netName = net['name'].replace(' ' , '_')
                netID = net['id']
                await objBackup(net, orgName)
                netTasks = [objFunction(net, function, orgName = orgName) for function in netList]
                for task in asyncio.as_completed(netTasks):
                    await task
                print(f'all net tasks completed for {netName}')
                unnamedAcc = 0
                devs = await aiomeraki.networks.getNetworkDevices(netID)
                for dev in devs:
                    # MX in HFP-Balt-Wash is named BALT/WASH-MO-MX01. Recovery for this will be difficult
                    if 'name' in dev and dev['name'] != None:
                        devName = dev['name'].replace(' ', '_').replace('/', '-')
                    else:
                        devName = 'Unnamed_Device_' + str(unnamedAcc)
                        unnamedAcc += 1
                    await objBackup(dev, orgName, netName, unnamedAcc = unnamedAcc)
                    devTasks = [objFunction(dev, function, orgName, netName, unnamedAcc = unnamedAcc) for function in devList]
                    for task in asyncio.as_completed(devTasks):
                        await task
                    print(f'all dev tasks completed for {devName}')
                os.mkdir(f'{MAIN_PATH}/{orgName}/{netName}/clients')
                # reinitializing for clients
                unnamedAcc = 0
                clients = await aiomeraki.networks.getNetworkClients(netID)
                for client in clients:
                    if 'description' in client and client['description'] != None:
                        clientName = client['description'].replace(' ', '_').replace('/', '-')
                    else:
                        clientName = 'Unnamed_Client_' + str(unnamedAcc)
                        unnamedAcc += 1
                    await objBackup(client, orgName, netName, True, unnamedAcc = unnamedAcc)
                    clientTasks = [objFunction(client, function, orgName, netName, netID, True, unnamedAcc = unnamedAcc) for function in clientList]
                    for task in asyncio.as_completed(clientTasks):
                        await task
                    print(f'all client tasks completed for {clientName}')
                try:
                    ssids = await aiomeraki.wireless.getNetworkWirelessSsids(netID)
                    os.mkdir(f'{MAIN_PATH}/{orgName}/{netName}/ssids')
                    unnamedAcc = 0
                    for ssid in ssids:
                        if 'name' in ssid and ssid['name'] != None:
                            sName = ssid['name'].replace(' ', '_').replace('/', '-')
                        else:
                            sName = 'Unnamed_SSID_' + str(unnamedAcc)
                            unnamedAcc += 1
                        await objBackup(ssid, orgName, netName, ssid = True, unnamedAcc = unnamedAcc)
                        sTasks = [objFunction(ssid, function, orgName, netName, netID, ssid = True, unnamedAcc = unnamedAcc) for function in ssidList]
                        for task in asyncio.as_completed(sTasks):
                            await task
                        print(f'all ssid tasks completed for {sName}')
                except:
                    # ssids don't work for all networks
                    print(f'No ssids for {netName}. Onto next network')

async def objBackup(obj, orgName = None, netName = None, client = False, ssid = False, unnamedAcc = 0):
    """
    Creates the ecosystem in which each object's backup will be created
    """
    # When orgName is None, assume it's an organization as the name is included in the object itself.
    if client == False:
        if 'name' in obj and obj['name'] != None:
            objName = obj['name'].replace(' ', '_').replace('/', '-')
        elif ssid == False:
            objName = 'Unnamed_Device_' + str(unnamedAcc)
        else:
            objName = 'Unnamed_SSID_' + str(unnamedAcc)
    else:
        if 'description' in obj and obj['description'] != None:
            objName = obj['description'].replace(' ', '_').replace('/', '-')
        else:
            objName = 'Unnamed_Client_' + str(unnamedAcc)
    if orgName == None:
        path = objName
    elif netName == None:
        path = f'{orgName}/{objName}'
    elif client == False and ssid == False:
        path = f'{orgName}/{netName}/{objName}'
    elif client == True:
        path = f'{orgName}/{netName}/clients/{objName}'
    elif ssid == True:
        path = f'{orgName}/{netName}/ssids/{objName}'
    if os.path.isdir(f'{MAIN_PATH}/{path}') == False:
        os.mkdir(f'{MAIN_PATH}/{path}')
    os.chdir(f'{MAIN_PATH}/{path}')
    time = datetime.datetime.now().isoformat(timespec='seconds')
    # f strings with strings in them is a pain, so i'm assigning variables to circumvent that
    with open(f'{MAIN_PATH}/{path}/{time}_{objName}.json', 'w') as f:
        json.dump(obj, f, indent=4)
    #print(f'finished making {objName} dir')

# Doesn't necessarily need the client functionality as the only thing stored in clients at the moment is the client itself.
async def objFunction(obj, function, orgName = None, netName = None, netID = None, client = False, ssid = False, unnamedAcc = 0):
    """
    Takes care of processing a function
    """
    # When orgName is None, assume it's an organization as the name is included in the object itself.              
    if client == False:
        if 'name' in obj and obj['name'] != None:
            objName = obj['name'].replace(' ', '_').replace('/', '-')
        elif ssid == False:
            objName = 'Unnamed_Device_' + str(unnamedAcc)
        else:
            objName = 'Unnamed_SSID_' + str(unnamedAcc)
    else:
        if 'description' in obj and obj['description'] != None:
            objName = obj['description'].replace(' ', '_').replace('/', '-')
        else:
            objName = 'Unnamed_Client_' + str(unnamedAcc)
    #print(f'starting processing for {function.name}')
    if 'id' in obj:
        objID = obj['id']
    elif 'serial' in obj:
        objID = obj['serial']
    else:
        objID = obj['number']
    # This is fine because it will create something along the lines of 'AIOMERAKI.wireless.whateverFunction(orgID)'
    if netID == None:
        functionName = 'AIOMERAKI.' + function.path + '.' + function.name + '(objID)'
    else:
        functionName = 'AIOMERAKI.' + function.path + '.' + function.name + '(netID, objID)'
    path = ''
    if orgName == None:
        path = objName
    elif netName == None:
        path = f'{orgName}/{objName}'
    elif client == False and ssid == False:
        path = f'{orgName}/{netName}/{objName}'
    elif client == True:
        path = f'{orgName}/{netName}/clients/{objName}'
    elif ssid == True:
        path = f'{orgName}/{netName}/ssids/{objName}'
    os.chdir(f'{MAIN_PATH}/{path}')
    fileName = createFilename(function.name)
    # This means that the function was something like getOrganization, which is stored in objBackup already
    if fileName == None:
        return(None)
    retry = True
    timerList = [5]
    maxTime = 5
    while retry == True:
        retry = False
        try:
            response = await eval(functionName)
        except meraki.AsyncAPIError as e:
            # Attempt at making thread sleep when 429- too many requests is received
            # Sleep time is calculated by networking algorithm (can't remember the name) where every time failure is reached, the maximum wait time grows and then the time to wait is randomly picked from a list of possible wait times
            # This may fail as there is a minimum wait time? Meraki's python library is kind of weird about this as the return value doesn't contain such; 429 is automatically reinstiated 
            if e.status == 429:
                # making sure that an infinite loop isn't reached. 10 minutes seems reasonable atm
                if maxTime >= 600:
                    print(f'Error: {e}. Maximum allotted time has been reached. Not retrying.')
                else:
                    retry = True
                    index = random.randint(0, len(timerList)-1)
                    #print(f'Error: {e}. Trying again in {timerList[index]} seconds')
                    await asyncio.sleep(timerList[index])
                    maxTime*=2
            elif e.status != 400:
                print(f'Error: {e}')
                return(None)
            else:
                return(None)
        except Exception as e:
            print(f'Error: {e}')
            return(None)
    if response == None or response == []:
        return(None)
    with open(f'{MAIN_PATH}/{path}/{fileName}.json', 'w') as f:
        json.dump(response, f, indent=4)
        

def createFilename(operationId):
    oldName = operationId.replace('getOrganization', '').replace('getNetwork', '').replace('getDevice', '').replace('WirelessSsid', '')
    if len(oldName) == 0:
        return(None)
    newName = datetime.datetime.now().isoformat(timespec='seconds')
    for char in oldName:
        if char.isupper():
            newName += '_' + char.lower()
        else:
            newName += char
    return(newName)

def initBackup(API_KEY):
    """
    Parses the json of all the meraki requests to obtain what to run and initializes async
    """
    spec = requests.get('https://api.meraki.com/api/v1/openapiSpec', headers={'X-Cisco-Meraki-API-Key': API_KEY}).json()
    orgList, netList, devList, clientList, ssidList = [], [], [], [], []
    for path in spec['paths']:
        functions = spec['paths'][path]
        # this filters out functions that are monitoring something
        # regarding repeats, the get request is always the multiple if available (thankfully). tested 4/20 with looking at the operation ID of each
        if 'get' in functions and ('post' in functions or 'put' in functions) and 'parameters' in functions['get']:
            if 'History' not in functions['get']['operationId'] and 'Usage' not in functions['get']['operationId']:
                paramList = []
                for param in functions['get']['parameters']:
                    if 'required' in param:
                        paramList.append(param['name'])
                if len(paramList) == 1 and 'getNetworkDevices' not in functions['get']['operationId'] and 'getOrganizationNetworks' not in functions['get']['operationId']:
                    if 'getNetworkWirelessSsids' in functions['get']['operationId']:
                        print('1')
                    # figuring out the dashboard.x.functionName where path is x
                    functionPath = ''
                    if '/appliance' in path:
                        functionPath = 'appliance'
                    elif '/cellularGateway' in path:
                        functionPath = 'cellularGateway'
                    elif '/camera' in path:
                        functionPath = 'camera'
                    elif '/switch' in path:
                        functionPath = 'switch'
                    elif '/insight' in path:
                        functionPath = 'insight'
                    elif '/sm' in path:
                        functionPath = 'sm'
                    elif '/wireless' in path:
                        functionPath = 'wireless'
                    elif '/sensor' in path:
                        functionPath = 'sensor'
                    elif '/devices' in path:
                        functionPath = 'devices'
                    elif '/networks' in path:
                        functionPath = 'networks'
                    elif '/organizations' in path:
                        functionPath = 'organizations'
                    # there is only one parameter
                    paramName = paramList[0]
                    if paramName == 'serial':
                        devList.append(c_Function(functionPath, functions['get']['operationId'], paramName))
                    elif paramName == 'networkId':
                        if 'getNetworkWirelessSsids' in functions['get']['operationId']:
                            print(functionPath, functions['get']['operationId'], paramName)
                        netList.append(c_Function(functionPath, functions['get']['operationId'], paramName))
                    elif paramName == 'organizationId':
                        orgList.append(c_Function(functionPath, functions['get']['operationId'], paramName))
                elif len(paramList) == 2 and '/ssid' in path:
                    if 'getNetworkWirelessSsids' in functions['get']['operationId']:
                        print('2')
                    functionPath = 'wireless'
                    ssidList.append(c_Function(functionPath, functions['get']['operationId'], paramList))
                elif len(paramList) == 2 and '/clients' in path:
                    functionPath = 'networks'
                    clientList.append(c_Function(functionPath, functions['get']['operationId'], paramList))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initAsync(API_KEY, orgList, netList, devList, ssidList, clientList))
                
def main(argv):
    """
    Parses arguments to get the API key and initialize the backup directory
    """
    global MAIN_PATH
    API_KEY = ''
    try:
        opts, args = getopt.getopt(argv, 'k:p:o:')
    except getopt.GetoptError:
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-k':
            API_KEY = arg
        if opt == '-p':
            MAIN_PATH = arg
    if API_KEY == '':
        sys.exit(2)
    if MAIN_PATH == '':
        # should probably just be os.getcwd() (same as pwd in bash) but for now I'm just going to have it be in files
        # MAIN_PATH = os.getcwd()
        # THIS NEEDS TO BE ALTERED
        MAIN_PATH = '/home/ccorby/meraki/project1_ccorby/meraki_lib/src/files'
    # doing isoformat to have it as a string
    mainBackupDir = datetime.datetime.now().isoformat(timespec='seconds') + '_backup' 
    MAIN_PATH = os.path.join(MAIN_PATH, mainBackupDir)
    try:
        os.mkdir(MAIN_PATH)
    except OSError as e:
        print(e)
        print('Backup directory could not be created')
        sys.exit(2)
    os.chdir(MAIN_PATH)
    initBackup(API_KEY)

if __name__ == '__main__':
    main(sys.argv[1:])
