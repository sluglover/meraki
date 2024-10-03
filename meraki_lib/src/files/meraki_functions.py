"""
Written by Christopher Corby, 11/20/21.

This file is a compilation of functions that are useful in pulling data from a meraki dashboard. 
It is NOT meant to be executed by itself, rather imported and utilized by other scripts.

History:
 11/20/21 cmc Created
 11/20/21 cmc Completed working version
 11/25/21 cmc Changed error output to dictionary of null values in getOrgSNMP, getWanStatus, and getNetFlow
 11/27/21 cmc Fixed object issue (don't use hostnames v2). Added new organization-level functions
 12/11/21 cmc Changed error output to not supported on API error (essentially when it shouldn't be called) and error on exception (generally syntax error)
 12/23/21 cmc Added IPs to device class; pulled from organization uplinks
 12/28/21 cmc Added a few test functions (network policies, network topology, network traffic apps) that write json output to a csv, updated WAN1 & WAN2 IPs to public IPs, and started monitoring network traffic
 12/29/21 cmc Added event tracking test functions and uplink status change
 12/30/21 cmc Added primary uplink selection function seperate from load balancing and updated error handling in a few functions where not every device can be pulled (API error) 
 12/31/21 cmc Added a function to obtain MX device subnets
 1/3/22 cmc Added a function and client class for obtaining clients of a device
 1/6/22 cmc Changed uplinkChange events to only return the last event for each device, added last reported attribute to uplink status pull
 1/10/22 cmc Added docstring 
 1/20/22 cmc Continued chipping away at the docstrings
 2/5/22 cmc Started adding functionality to all functions within meraki api
 2/11/22 cmc Changed organizations and networks to have objects, encapsulated timezone conversion function
 2/18/22 cmc Continued adding functionality to every API call, altered classes to have more appropriate formatting of default values on creation
 2/24/22 cmc Added more funcitonality, specifically working on organization section
 3/12/22 cmc Fixed error handling for some networks that only worked for MXs 
 3/20/22 cmc Fixed case where empty handling was failing; some json store '' for a field
 3/26/22 cmc Added additional check for MX-related network errors where stderr isn't printed for known issues in getPrimaryUplink
 4/8/22 cmc Updated getNetDevsFirmwareInfo to actually parse the json, along with adding more attributes to devices to account for firmware
 4/15/22 cmc Fixed incorrect error parsing in load balancing
 4/23/22 cmc Added VLAN functions
 2/24/23 cmc Added wan1/2 gateway to device class. pulled from getUplinkStatus 
 7/21/23 cmc Added better error handling for functions used in uplink log report
 2/16/24 cmc Added getNetCellGateway and getNetFirewallNatRules
Requirements:
python 3, getopt, meraki, datetime
csv and requests for functions still in development


Global variables:
DASHBOARD -> Authentication into the dashboard using the API Key

Examples:
This example obtains all the organization IDs
  
  createDashboard(API_key) -> creates the connection to the dashboard
  getOrgs('/all') -> returns a dictionary of all the organizations mapping to their ids

This example obtains all the devices in a list
 
  devList = []
  createDashboard(API_key) -> creates the connection to the dashboard
  orgDict = getOrgs('/all') -> returns a dictionary of all the organizations mapping to their ids
  for org in OrgDict.keys():
    orgID = orgDict[org]
    netDict = getNets(orgID) -> returns a dictionary of all the networks in the organization mapping to their ids
    for net in netDict.keys():
      netID = netDict[net]
      devs = getNetDevs(netID) -> returns a list of the devices with serial, model, and name
      devList += devs

Alternatively, one could use getOrgDevs to skip the network iteration using the orgID and obtain all devices for an organization.  
"""

# csv and requests aren't necessary other than for the test functions
# datetime is only necessary for event tracking (uplink status change)
import meraki, getopt, csv, requests, datetime 


# Global variables:                                                                     
# This does ofc create a security concern. Should it be passed on each
# request instead of one single authentication?
DASHBOARD = '' #authenticates requests for the dashboard 

# Classes:

# IP is the private IP, which is used on LAN rather than WAN

#reasoning behind making some have the different formatting with self.attr is default values are easier this way

class c_Org:
    def __init__(self):
        name = ''
        ID = ''

class c_Net:
    def __init__(self):
        name = ''
        ID = ''
        orgID = ''
        productTypes = []
        tz = ''
        tags = ''
        enrollmentString = ''
        url = ''
        notes = ''
    
class c_Dev:
    def __init__(self):
        serial = ''
        name = ''
        model = ''
        netID = ''
        wan1_ip = ''
        wan1_pub_ip = ''
        wan1_stat = ''
        wan2_ip = ''
        wan2_pub_ip = ''
        wan2_stat = ''
        lastReported = ''
        tags = []
        mac = ''
        order = ''
        pub_ip = ''
        status = ''
        lan_ip = ''
        mac = ''
        wan1_gateway = ''
        wan2_gateway = ''
        gateway = '' #TODO (probably) assimilate this field to wan1/2 gateway fields
        firmware = ''
        productType = ''

class c_Alert:
    def __init__(self):
        alertType = ''
        enabled = ''
        default = ''
        emails = ''

class c_Net_Packet:
    def __init__(self, app='None', destination='None', protocol='None', port='None', num_sent='None', num_received='None', clients='None', timeActive='None', flows='None'):
        self.app = app
        self.destination = destination
        self.protocol = protocol
        self.port = port
        self.num_sent = num_sent
        self.num_received = num_received
        self.clients = clients
        self.timeActive = timeActive
        self.flows = flows
    def __eq__(self, other):
        return self.app == other.app and self.destination == other.destination and self.protocol == other.protocol and self.port == other.port

class c_Uplink_Event:
    def __init__(self):
        devName = ''
        devSerial = ''
        uplinkActive = ''
        time = ''

class c_Client:
    def __init__(self, ID='not configured', description='not configured', mac='not configured', ip='not configured', vlan = 'not configured', hostname='not configured'):
        self.ID = ID
        self.description = description
        self.mac = mac
        self.ip = ip
        self.vlan = vlan
        self.hostname = hostname

class c_Bluetooth_Client:
    def __init__(self):
        ID = ''
        name = ''
        mac = ''
        netID = ''
        tags = ''

class c_SSID:
    def __init__(self):
        number = ''
        isAuthorized = ''
        authorizedAt = ''
        expiresAt = ''
        
class c_User:
    def __init__(self):
        ID = ''
        email = ''
        name = ''
        createdAt = ''
        userType = ''
        authorizations = []

class c_MQTT:
    def __init__(self):
        ID = ''
        name = ''
        host = ''
        port = ''
        security = ''
        username = ''

class c_Syslog:
    def __init__(self):
        host = ''
        port = ''
        roles = ''

class c_Data_Usage:
    """
    Misc class that's used to make some client data get requests easier to sort through
    """
    def __init__(self):
        timestamp = ''
        app = ''
        port = ''
        sent = ''
        received = ''

class c_Action_Batch:
    def __init__(self):
        ID = ''
        status = ''
        errors = []
        createdResources = []
        actions = []

class c_Action:
    def __init__(self):
        resource = ''
        operation = ''
        body = ''

class c_Dev_Firmware:
    def __init__(self):
        productType = ''
        currentFirmware = ''
        newestFirmware = ''

class c_Vlan:
    def __init__(self):
        ID = ''
        name = ''
        subnet = ''
        # also has netID, appliance IP, group policy ID, fixed Ip assignments, reserved IP ranges, and DHCP settings as per get vlans request

# Helper functions

def UTCtoEST(ISOString):
    """
    Converts a UTC string to an EST datetime object 
    
    :usage: UTCtoEST(string of ISO formatted UTC time) -> datetime object in EST
    :param utcString: ISO formatted string of UTC time
    :returns: Datetime object in EST
    :raises:

    """
    if 'T' in ISOString:
        if ISOString[19] == 'Z':
            utc = datetime.datetime.strptime(ISOString + '+0000', '%Y-%m-%dT%H:%M:%SZ%z')
        else:
            utc = datetime.datetime.strptime(ISOString + '+0000', '%Y-%m-%dT%H:%M:%S.%fZ%z')
    else:
        # in format year-month-day hour-minute-second UTC
        utc = datetime.datetime.strptime(ISOString, '%Y-%m-%d %H:%M:%S UTC')
    est = utc.astimezone(tz=None)
    return est

def deviceType(devModel):
    """
    Distinguishes which product type a device is given its model

    :usage: deviceType(String of device model) -> String of product type
    :param devModel: Device model
    :returns: String of product type
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initalized through createDashboard
    """
    if 'MR' in devModel:
        return('wireless')
    elif 'MS' in devModel:
        return('switch')
    elif 'MV' in devModel:
        return('camera')
    elif 'MG'in devModel:
        return('cellularGateway')
    elif 'MX' in devModel or 'Z1' in devModel:
        return('appliance')

# Functions:

# TODO: sort by organization, network, device, client, other
# Possible TODO: all the webhook stuff. i'm pretty sure it's not configured atm so i'm skipping the functions
# Possible TODO: Combine every multiple/single requests/posts with an extra parameter in the function to make it more user-friendly
# cloneOrg exists as a get request, but not implementing for now

def createDashboard(key):
    """
    Sets the dashboard request key to use in other requests.
    
    :usage: createDashboard(String of API key)
    :param key: This is the API key used for authentication
    :returns: nothing. The dashboard key is stored as a global variable.
    :raises: No error if key is wrong, but all other functions will display Unauthorized: Invalid API Key
    """
    
    global DASHBOARD
    # set output_log and print_console to true to displau every request from the dashboard
    DASHBOARD = meraki.DashboardAPI(key, output_log=False, print_console=False,suppress_logging=True)

def getOrgs(name = '/all'):
    """
    Compiles a dictionary of organization name to ID for requested organization(s)from the dashboard 
    
    :usage: getOrgs(String of Name) -> dictonary{String of Name: String of ID}
    :param name: Optional organization name. Default is all
    :returns: Dictionary mapping organization name to ID
    :raises: API error if the organization doesn't have requests enabled or the API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
             
    """
    # TODO figure out if you want this as a list of objects instead. might be better
    try:
        response = DASHBOARD.organizations.getOrganizations()
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(e.message, None)
    except Exception as e:
        print(e, 'Error: %s' % e)
        return(None)
    # response also contains id, url, api info (enabled or not), and licnesing info
    orgDict = {}
    if name == '/all':
        for org in response:
            if 'id' in org and 'name' in org:
                orgDict[org['name']] = org['id'] 
    else:
        for org in response:
            if 'id' in org and 'name' in org:
                if org['name'] == name:
                    orgDict[org['name']] = org['id']
    return('', orgDict)

def getOrg(orgID):
    """
    Obtains the information for an organization given its ID
    
    :usage: getOrg(string of organization ID) -> String of organization name
    :param orgID: ID of the organziation
    :returns: String of the name of the organization
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        response = DASHBOARD.organizations.getOrganization(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(e.message, None)
    except Exception as e:
        print('Error: %s' % e)
        return(e, None)
    # response also contains id, url, api info (enabled or not), and licnesing info
    return('', response['name'])

def createOrg(orgName):
    """
    Creates an organization with the provided name
    
    :usage: createOrg(String of organization name) 
    :param orgName: Name of the organization to be created
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        response = DASHBOARD.organizations.createOrganization(orgName)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateOrg(orgID, name=None, apiEnabled=None):
    """
    Updates the name and/or whether or not the meraki api is enabled for the network
    
    :usage: updateOrg(string of organization ID, string of org name, boolean of api enabled)
    :param orgID: ID of the organization
    :param name: Name that you wish to change the organization to
    :param apiEnabled: Boolean for whether or not meraki API should be enabled
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        if apiEnabled == None:
            response = DASHBOARD.organizations.updateOrganization(orgID, name=name)
        elif name == None:
            response = DASHBOARD.organizations.updateOrganization(orgID, Api={enabled:apiEnabled})
        else:
            response = DASHBOARD.organizations.updateOrganization(orgID, name=name, Api={enabled:apiEnabled})
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def deleteOrg(orgID):
    """
    Deletes an organization from the dashboard
    
    :usage: deleteOrg(string of organization ID)
    :param orgID: ID of the organization to be deleted
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.deleteOrganization(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getActionBatches(orgID, batchID=None):
    """
    Obtains the action batches for an organization. Optional: put batch ID as second parameter to obtain information for a specific action batch
    
    :usage: getActionBatches(string of organization ID, string of batch ID) -> List of action batch objects
    :param orgID: ID of the organization
    :param batchID: ID of the batch
    :returns: List of action batch object(s)
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        if batchID == None:
            response = DASHBOARD.organizations.getOrganizationActionBatches(orgID)
        else:
            response = DASHBOARD.organizations.getOrganizationActionBatch(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    batchList = []
    i = 0
    if isinstance(response, list):
        for batch in response:
            batchList.append(c_Action_Batch())
            batchList[i].ID = batch['id']
            if batch['status']['completed'] == True:
                batchList[i].status = 'completed'
            elif batch['status']['failed'] == True:
                batchList[i].status = 'failed'
            else:
                print('Weird batch status edge case:')
                print(batch['status'])
            batchList[i].errors = batch['status']['errors']
            batchList[i].createdResources = batch['status']['createdResources']
            actionList = []
            j = 0
            for action in batch['actions']:
                actionList.append(c_Action())
                actionList[j].resource = action['resource']
                actionList[j].body = action['body']
                actionList[j].operation = action['operation']
                j += 1
            batchList[i].actions = actionList
            i += 1
    else:
        batchList.append(c_Action_Batch())
        batchList[i].ID = batch['id']
        if batch['status']['completed'] == True:
            batchList[i].status = 'completed'
        elif batch['status']['failed'] == True:
            batchList[i].status = 'failed'
        else:
            print('Weird batch status edge case:')
            print(batch['status'])
        batchList[i].errors = batch['status']['errors']
        batchList[i].createdResources = batch['status']['createdResources']
        actionList = []
        j = 0
        for action in batch['actions']:
            actionList.append(c_Action())
            actionList[j].resource = action['resource'] 
            actionList[j].body = action['body'] 
            actionList[j].operation = action['operation'] 
            j += 1
        batchList[i].actions = actionList
    return(batchList)


def createActionBatch(orgID, actions, confirmed, synchronous):
    """
    Creates an action batch for an organization
    
    :usage: createActionBatch(string of organization ID, list of actions, boolean of confirmed, boolean of synchronous)
    :param orgID: ID of the organization
    :param actions: List of actions as dictionaries containing resource, operation, and body
    :param confirmed: Boolean as to whether or not the batch should execute immediately
    :param synchronous: Boolean as to whether or not the batch should run synchronously. If true, at most 20 actions can run
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.createOrganizationActionBatch(orgID, actions, confirmed=confirmed, synchronous=synchronous)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateActionBatch(orgID, batchID, confirmed=None, synchronous=None):
    """
    Updates an action batch for an organization

    :usage: updateActionBatch(string of organization ID)
    :param orgID: ID of the organization
    :param batchID: ID of the batch you wish to update
    :param confirmed: Boolean as to whether or not the batch should execute immediately
    :param synchronous: Boolean as to whether or not the batch should run synchronously. If true, at most 20 actions can run
    :returns: N/A    
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        if confirmed == None:
            response = DASHBOARD.organizations.updateOrganizationActionBatch(orgID, batchID,  synchronous=synchronous)
        elif synchronous == None:
            response = DASHBOARD.organizations.updateOrganizationActionBatch(orgID, batchID,  confirmed=confirmed)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def deleteActionBatch(orgID, batchID):
    """
    Deletes an action batch
    
    :usage: deleteActionBatch(string of orgID, string of batchID)
    :param orgID: ID of the organization
    :param batchID: ID of the batch you wish to delete
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized

    """
    try:
        response = DASHBOARD.organizations.deleteOrganizationActionBatch(orgID,batchID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgAdaptivePolicyOverview(orgID):
    """
    Doesn't work
    """
    try:
        response = DASHBOARD.organizations.getOrganizationAdaptivePolicyOverview(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgAdaptivePolicy(orgID, policyID=None):
    """
    Obtains the adaptive polciy acls for an organization. Use policy ID if only a single ID is desired
    
    :usage: getOrgAdaptivePolicy(string of organization ID, string of policy ID) ->
    :param orgID: ID of the organization
    :param policyID: ID of the policy if only a single policy is desired
    :returns:
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    # empty lists for everything. don't use atm
    try:
        if policyID == None:
            response = DASHBOARD.organizations.getOrganizationAdaptivePolicyAcls(orgID)
        else:
            response = DASHBOARD.organizations.getOrganizationAdaptivePolicyAcl(orgID, policyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if isinstance(response, list):
        for policy in response:
            print(policy)
    else:
        print(response)

def createOrgAdaptivePolicyAcl(orgID, name, rules, ipVersion):
    """
    Creates an adaptive policy for an organization
    
    :usage: createOrgAdaptivePolicy(string of organization ID)
    :param orgID: ID of the organization
    :returns: N/A
    :raises:API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.organizations.createOrganizationAdaptivePolicyAcl(orgID, name, rules, ipVersion)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateOrgAdaptivePolicyAcl(orgID, policyID, name, description, rules, ipVersion):
    """
    Updates an adaptive policy

    Because there's no adaptive policies I can access rn, I'm not bothering with this function
    """
    try:
        response = DASHBOARD.organizations.updateOrganizationAdaptivePolicyAcl(orgID, policyID, name=name, description=description, rules=rules, ipVersion=ipVersion)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def deleteOrgAdaptivePolicyAcl(orgID, policyID):
    """
    Deletes an adaptive policy
    """
    try:
        response = DASHBOARD.organizations.deleteOrganizationAdaptivePolicyAcl(orgID, policyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgAdaptivePolicyGroup(orgID, groupID=None):
    """
    Obtains the active policy group(s) for an organization. Baillie doesn't seem to heave it enabled/configured as a 404 error is returned. not creating the create/update/delete functions for this.
    """
    response = requests.get('https://api.meraki.com/api/v1/organizations/%s/adaptivePolicy/groups' % (orgID), headers={'X-Cisco-Meraki-API-Key': 'fc24863c03b8db18a94ce4b8833859b79e864534', 'Content-Type': 'application/json', 'Accept': 'application/json'})
    print(response)
    try:
        if groupID == None:
            response = DASHBOARD.organizations.getOrganizationAdaptivePolicyGroups(orgID)
        else:
            response = DASHBOARD.organizations.getOrganizationAdaptivePolicyGroup(orgID, groupID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if isinstance(response, list):
        for policy in response:
            print(policy)
    else:
        print(response)
    
def getOrgAdaptivePolicies(orgID, policyID=None):
    """
    Again, it doesn't seem to be configured, so I'm skipping the create/update/delete functions
    """
    try:
        if policyID == None:
            response = DASHBOARD.organizations.getOrganizationAdaptivePolicyPolicies(orgID)
        else:
            response = DASHBOARD.organizations.getOrganizationAdaptivePolicyPolicy(orgID, policyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if isinstance(response, list):
        for policy in response:
            print(policy)
    else:
        print(response)

def getOrgAdaptivePolicySettings(orgID):
    """
    Obtains a list of network IDs with adaptive policy enabled
    
    :usage: getOrgAdaptivePolicySettings(String of organizaton ID) -> List[String of network IDs]
    :param orgID: ID of the organization
    :returns: List of network IDs
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        response = DASHBOARD.organizations.getOrganizationAdaptivePolicySettings(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if 'enabledNetworks' in response:
        return(response['enabledNetworks'])
    else:
        return(None)

def updateOrgAdaptivePolicySettings(orgID, netIDs):
    """
    Updates which networks have adaptive policy enabled
    
    :usage: updateOrgAdaptivePolicySettings(String of organization ID, list of network IDs)
    :param orgID: ID of the organization
    :param netIDs: List of network IDs in the form of strings
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.updateOrganizationAdaptivePolicySettings(orgID, enabledNetworks=netIDs)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgAdmins(orgID):
    """
    Obtains the admins for the organization's dashboard
    
    :usage: getOrgAdmins(String of organization ID) -> 
    :param orgID: ID of the organization
    :returns:
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    # contains admin's ID, name, email, organization access, account status, 2FA enabled, API key enabled, last active, networks with respective IDs and type of access in a list, and tags
    try:
        response = DASHBOARD.organizations.getOrganizationAdmins(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    for r in response:
        print(r)

def createOrgAdmin(orgID, email, name, orgAccess, tags=None, networks=None, authMethod=None):
    """
    Creates an admin for an organization's dashboard
    
    :usage: createOrgAdmin(String of organization ID, string of email, string of name, string of organziation access, list of tags, list of networks, string of authentication method)
    :param orgID: ID of the organziation
    :param email: Email of the admin
    :param name: Name of the admin
    :param orgAccess: Organization privilege. Either none, full, read-only, or enterprise
    :param tags: List of tags that admin has privilege on, each a dictionary of tag and access
    :param nets: List of networks admin has privilege on, each a dictionary of netID and access
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        response = DASHBOARD.organizations.createOrganizationAdmin(orgID, email, name, orgAccess, tags=tags, networks=networks, authenticationMethod=authMethod)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateOrgAdmin(orgID, adminID, name=None, orgAccess=None, tags=None, nets=None):
    """
    Updates an admin for an organization's dashboard
    
    :usage: updateOrgAdmin(String of organization ID, string of admin ID, string of name, string of organziation access, list of tags, list of networks)
    :param orgID: ID of the organziation
    :param adminID: ID of the admin you wish to update
    :param name: Updated name of admin
    :param orgAccess: Updated organization privilege. Either none, full, read-only, or enterprise
    :param tags: List of tags that admin has privilege on, each a dictionary of tag and access
    :param nets: List of networks admin has privilege on, each a dictionary of netID and access
    :returns: N/A
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        # might not accept none and networks might be different case as it's not in the example
        response = DASHBOARD.organizations.updateOrganizationAdmins(orgID, adminID, name=name, orgAccess=orgAccess, tags=tags, networks=nets)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgAlertProfiles(orgID,key):
    """
    Another function that doesn't seem to be enabled/configured for the organization (yields 404 response). Skipping the respective create/update/delete functions
    """
    response = requests.get('https://api.meraki.com/api/v1/organizations/{%s}/alerts/profiles' % (orgID), headers={'Content-Type':'application/json', 'Accept':'application/json', 'X-Cisco-Meraki-API-Key':key})
    print(response)
    try:
        response = DASHBOARD.organizations.getOrganizationAlertsProfiles(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgBrandingPolicy(orgID, policyID=None):
    """
    Organization doesn't support dashboard branding at the moment, so an error is returned. not creating create/update/delete function for this reason. There's also branding policy priorities (get/update), which will also not be implemented for now
    """
    # this returns policy id, name, admin settings(who it applies to and respective networks), and a bunch of help settings
    try:
        if policyID == None:
            response = DASHBOARD.organizations.getOrganizationBrandingPolicies(orgID)
        else:
            response = DASHBOARD.organizations.getOrganizationBrandingPolicy(orgID, policyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if isinstance(response, list):
        for policy in response:
            print(policy)
    else:
        print(response)

def addToOrg(orgID, orders=None, serials=None, licenses=None):
    """
    Adds devices, licenses, and/or orders to an organization
    
    :usage: addToOrg(String of organization ID, list of orders, list of serials, list of licenses)
    :param orgID: ID of the organization
    :param orders: List of order numbers to add(strings)
    :param serials: List of device serials to add(strings)
    :param licenses: List of licenses to add in the form {key:String, mode:String}. Mode can be either renew or addDevices. Defaults to addDevices
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    """
    try:
        response = DASHBOARD.organizations.claimIntoOrganization(orgID, orders=orders, serials=serials, licenses=licenses)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgConfigTemplate(orgID, templateID=None):
    """
    Obtains the configuration tempalte(s) for an organization. 
    
    :usage: getOrgConfigTemplates(string of organization ID) -> 
    :param orgID: ID of the organization
    :param tempalteID: ID of the specific template desired
    :returns:
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    # only one test template exists at the moment
    try:
        if templateID == None:
            response = DASHBOARD.organizations.getOrganizationConfigTemplates(orgID)
        else:
            response = DASHBOARD.organizations.getOrganizationConfigTemplate(orgID, templateID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def createOrgConfigTemplate(orgID, name, tz, copyID=None):
    """
    Creates a new configuration template for an organization
    
    :usage: createOrgConfigTemplate(String of organization ID, string of name, string of timezone, string of copy ID)
    :param orgID: ID of the organization
    :param name: Name of the template to create
    :param tz: String of the timezone. Must be acceptable tz database timezone. 
    :param copyID: ID of the network or configuration template to copy from
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        # unsure about copyID parameter of post request
        response = DASHBOARD.organizations.createOrganizationConfigTemplate(orgID, name, timeZone=tz, copyId=copyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateOrgConfigTemplate(orgID, templateID, name=None, tz=None):
    """
    Updates a configuration template for an organization
    
    :usage: updateOrgConfigTemplate(String of organization ID, string of template ID, string of name, string of timezone)
    :param orgID: ID of the organization
    :param templateID: ID of the configuration template to change
    :param name: Name of the template to create
    :param tz: String of the timezone. Must be acceptable tz database timezone.
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        response = DASHBOARD.organizations.updateOrganizationConfigTemplate(orgID, templateID, name, timeZone=tz)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def deleteOrgConfigTemplate(orgID, templateID):
    """
    Deletes a configuration template
    
    :usage: deleteOrgConfigTempalte(String of organization ID, string of template ID)
    :param orgID: ID of the organization
    :param templateID: ID of the configuration template to delete
    :returns: N/A
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.deleteOrganizationConfigTemplate(orgID, templateID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgDevInventory(orgID, devSerial=None):
    """
    Get inventory for all the devices on an organization. (just the order number and licensing, better to use orgDevs in most instances)
    
    :usage: getOrgDevInventory(string of organization ID, string of device serial) -> list[device objects]
    :param orgID: ID of the organization
    :param devSerial: ID of the specific device you wish to get inventory for
    :returns: List of device objects
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    # each device has mac, serial, name, model, netID, orderNumber, claimedAt, licenseExpirationDate, tags, and productType
    try:
        if devSerial == None:
            response = DASHBOARD.organizations.getOrganizationInventoryDevices(orgID)
        else:
            response = DASHBOARD.organizations.getOrganizationInventoryDevice(orgID, devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    devList = []
    i = 0
    if isinstance(response, list):
        for dev in response:
            devList.append(c_Dev())
            devList[i].serial = dev['serial']
            devlist[i].name = dev['name']
            devlist[i].netID = dev['networkID']
            devlist[i].tags = dev['tags']
            devList[i].model = dev['model']
            devList[i].order = dev['orderNumber']
            devList[i].mac = dev['mac']
            devList[i].tags = dev['tags']
            i += 1
    else:
        devList.append(c_Dev())
        devList[i].serial = dev['serial']
        devlist[i].name = dev['name']
        devlist[i].netID = dev['networkID']
        devlist[i].tags = dev['tags']
        devList[i].model = dev['model']
        devList[i].order = dev['orderNumber']
        devList[i].mac = dev['mac']
        devList[i].tags = dev['tags']
    return(devList)

def getOrgLicenses(orgID):
    """
    Obtains the licenses for an organization. not supported for Baillie, so not going to create the assign, move, renew, and update functions.
    
    :usage: getOrgLicenses(string of organziation ID)
    :param orgID: ID of the organization
    :returns:
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.getOrganizationLicenses(orgID, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgLoginSecuritySettings(orgID):
    """
    Obtains the login settings for an organization
    
    :usage: getOrgLoginSecuritySettings(String of organization ID) -> Dictionary of settings
    :param orgID: ID of the organziation
    :returns: Dictionary with boolean or ints for the corresponding enforcePasswordExpiration, passwordExpirationDays, enforceDifferentPasswords, numDifferentPasswords, enforceStrongPasswords, enforceAccountLockout, accountLockoutAttempts, enforceIdleTimeout, idleTimeoutMinutes, enforceTwoFactorAuth, enforceLoginIpRanges, loginIpRanges
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.getOrganizationLoginSecurity(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    
def updateOrgLoginSecuritySettings(orgID, settings):
    """
    Updates the login settings for an organization
    
    :usage: updateOrgLoginSecuritySettings(string of organization ID, dictionary of settings)
    :param orgID: ID of the organization
    :param settings: Dictionary with boolean or ints for the corresponding enforcePasswordExpiration, passwordExpirationDays, enforceDifferentPasswords, numDifferentPasswords, enforceStrongPasswords, enforceAccountLockout, accountLockoutAttempts, enforceIdleTimeout, idleTimeoutMinutes, enforceTwoFactorAuth, enforceLoginIpRanges, loginIpRanges
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.getOrganizationLoginSecurity(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgSaml(orgID):
    """
    Returns whether or not SAML SSO is enabled for an organization
    
    :usage: getOrgSaml(string of organziation ID) -> Boolean
    :param orgID: ID of the organziation
    :returns: Boolean
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard

    """
    try:
        response = DASHBOARD.organizations.getOrganizationSaml(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if 'enabled' in response:
        return(response['enabled'])
    else:
        return(False)

def updateOrgSaml(orgID, enabled):
    """
    Updates whether or not SAML SSO is enabled
    
    :usage: updateOrgSaml(String of organization ID, boolean for enabled)
    :param orgID: ID of the organization
    :param enabled: Boolean for enabled or disabled
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.updateOrganizationSaml(orgID, enabled=enabled)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgSamlIdp(orgID):
    """
    Obtains SAML IDPs for the organization. Each contains ID, consumer URL, x509certSha1Fingerprint, and sloLogoutUrl. Should probably create an object
    """
    try:
        response = DASHBOARD.organizations.getOrganizationSamlIdps(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgSamlRoles(orgID):
    """
    Obtains SAML roles for the organization. Returns ID, role, and orgAccess for each.
    """
    try:
        response = DASHBOARD.organizations.getOrganizationSamlRoles(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getOrgConfigChanges(orgID):
    """
    Returns the change log for the organization
    
    """
    # each change has timestamp, admin name/email/ID, page, label, old and new value
    try:
        response = DASHBOARD.organizations.getOrganizationConfigurationChanges(orgID, total_pages=3)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    


def getNets(orgID, netName=None):
    """
    Compiles a dictionary of network name to ID for requested organization and network(s) from the dashboard
    
    :usage: getNets(String of organization ID, String of network Name) -> dictionary{String of Name: String of ID} 
    :param orgID: ID of the organization that the network is under
    :param netName: Optional name of network. Default is none, which pulls all networks
    :returns: Dictionary mapping network name to ID
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
   
    """
    # TODO figure out if you want this as a list of objects instead. might be better
    # each network has ID, orgID, name, timezone, tags, product types, enrollment string, and notesgithub.com/meraki/dashboard-api-python/
    try:
        response = DASHBOARD.organizations.getOrganizationNetworks(orgID, total_pages = 'all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(e.message, None)
    except Exception as e:
        print('Error: %s' % e)
        return(e, None)
    netDict = {}
    if netName is not None:
        for net in response:
            if 'id' in net and 'name' in net:
                if netName in net['name']:
                    netDict[net['name']] = net['id']
    else:
        #add all networks
        for net in response:
            if 'id' in net and 'name' in net:
                netDict[net['name']] = net['id'] 
    return('', netDict)

def createNet(orgID, name, productTypes=None, tags=None, tz=None, notes=None):
    """
    Creates a network on the given organziation
    
    :usage: createNet(String of network ID, string of name, list of product types, list of tags, stirng of timezone, string of notes)
    :param orgID: ID of the organziation
    :param name: Name of the network
    :param productTypes: List of the types of products on the network
    :param tags: List of tags for the network
    :param notes: String of notes for the network
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.createOrganizationNetwork(orgID, name, productTypes, tags=tags, timeZone=tz, notes=notes)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)

def combineNets(orgID, name, netIDs, enrollmentString=None):
    """
    Combines networks into a single network
    
    :usage: combineNets(String of organizaton ID, string of name, list of network IDs) -> object of resulting network
    :param orgID: ID of the organization
    :param name: Name of the new combined network
    :param netIDs: List of the IDs of the networks to combine
    :returns: Network object of new network
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.combineOrganizationNetworks(orgID, name, netIDs)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    net = c_Net()
    result = response['resultingNetwork']
    net.ID = result['id']
    net.orgID = result['organizationId']
    net.name = result['name']
    net.tz = result['timeZone']
    net.tags = result['tags']
    net.productTypes = result['productTypes']
    net.notes = result['notes']
    net.enrollmentString = result['enrollmentString']
    return(net)


def getNetTraffic(netID):
    """
    Obtains all the network traffic for the day from the dashboard and compiles them into net_packet classes
    
    :usage: getNetTraffic(String of network ID) -> list[packet objects]
    :param netID: ID of the network that you wish to get the traffic of
    :returns: List of net packet objects for the past day that contain destination, protocol, number sent/received, and other data
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized at all
             
    """
    try:
        # 86400 seconds in a day
        # timespan is measured in seconds
        # minimum of 2 hours -> 7200 seconds
        response = DASHBOARD.networks.getNetworkTraffic(netID, timespan=86400)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return('Nope')
    except Exception as e:
        print('Error: %s' % e)
        return('Nope')
    return('Worked')
    packetList = []
    i = 0
    for packet in response:
        packetList.append(c_Net_Packet())
        if 'application' in packet:
            packetList[i].app = packet['application']
        if 'destination' in packet:
            packetList[i].destination = packet['destination']
        if 'protocol' in packet:
            packetList[i].protocol = packet['protocol']
        if 'port' in packet:
            packetList[i].port = packet['port']
        if 'sent' in packet:
            packetList[i].num_sent = packet['sent']
        if 'recv' in packet:
            packetList[i].num_received = packet['recv']
        if 'numClients' in packet:
            packetList[i].clients = packet['numClients']
        if 'activeTime' in packet:
            packetList[i].timeActive = packet['activeTime']
        if 'flows' in packet:
            packetList[i].flows = packet['flows']
        i+=1
    return packetList

# not useful as of yet due to it being the settings
def getNetTrafficAnalysis(netID):
    """
    Obtains a json of the traffic settings for the network. Still in development because there is no current use for it.
    
    :usage: getNetTrafficAnalysis(String of network ID) -> printed json of traffic settings
    :param netID: ID of the network that you wish to get the settings for
    :returns: Printed json of the traffic settings
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    """
    # contains mode: basic or detailed, and then customPieChartItems with a list of dictionaries each containing name, type, host, and value. most are empty
    try:
        response = DASHBOARD.networks.getNetworkTrafficAnalysis(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateNetTrafficAnalysis(netID, mode, items):
    """
    Updates the network traffic analysis settings for a network
    
    :usage: updateNetTrafficAnalysis(string of network ID, string of mode, list of items)
    :param netID: ID of the network
    :param mode: String of the mode. Can be either disabled, basic, or detailed
    :param items: List of items for the pie chart on the dashboard. Each must be a dictionary of name, type, and value. type can be either host, port, or ipRange
    :reutrns: N/A
    :raises: API error if API key is faulty
             Error on str object if dahsboard key isn't initialized

    """
    # types of modes: {disabled: do not collect traffic types, basic: collect categories, detailed: collect destination hostnames}

    try:
        response = DASHBOARD.networks.updateNetworkTrafficAnalysis(netID, mode=mode, customPieChartItems=items)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

# For some reason, it doesn't seem to work for the networks. Gives error for everything
def getNetAlerts(netID):
    """
    not functional currently. Incompatible with current networks.
    
    :usage: getNetAlerts(String of network ID) -> printed json
    :param netID: ID of the network
    :returns: json
    :raises: Error on any given network ID
    """
    try:
        response = DASHBOARD.networks.getNetworkHealthAlerts(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getNetDevs(netID):
    """
    Compiles a list of device objects for a given network with name, serial, and model attributes
    
    :usage: getNetDevs(String of network ID) -> list[device objects]
    :param netID: ID of the network you wish to obtain the devices for 
    :returns: List of device objects with name, serial, and model for each
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    # also contains lat, lng, address, notes, lanIP, tags, firmware, floorplanID, and beaconIDparams
    
    try:
        response = DASHBOARD.networks.getNetworkDevices(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    devList = []
    i = 0
    for dev in response:
        # for some reason, there's devices still in the system even though they've been "removed": says "Dead: has been removed" for name
        devList.append(c_Dev())
        if 'name' in dev and dev['name'] != '':
            devList[i].name = dev['name']
        else:
            devList[i].name = "Unnamed device"
        devList[i].serial = dev['serial']
        devList[i].model = dev['model']
        devList[i].firmware = dev['firmware']
        devList[i].productType = deviceType(dev['model'])
        devList[i].mac = dev['mac']
        i+=1
    return(devList)

def getNetClients(netID):
    # this pull also obtains the usage, user, switchport, adaptive policy group, ip6, first/last seen, manufacturer, os, device type predicition, recent device(serial, name, mac, and connection), ssid, status, notes, ip6local, sm installed, and group policy 8021x 
    
    # device clients has hostname, where this does not
    """
    Compiles a list of client objects for a given network with attributes ID, description, mac, IP, vlan, and dhcp hostname 

    :usage: getNetClients(String of network ID) -> list[client objects]
    :param netID: ID of the network
    :returns: List of client objects
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """  
    try:
        response = DASHBOARD.networks.getNetworkClients(netID, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    clientList = []
    i = 0
    for client in response:
        clientList.append(c_Client())
        clientList[i].ID = client['id']
        clientList[i].mac = client['mac']
        clientList[i].description = client['description']
        clientList[i].ip = client['ip']
        clientList[i].vlan = client['vlan']
        i += 1
    return(clientList)

def getNetClient(netID, clientID):
    """
    Obtains the information for a client on a network
    
    :usage: getNetClient(string of network ID, string of client ID) -> Client object
    :param netID: ID of the network
    :param clientID: ID of the client
    :returns: Client object
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.getNetworkClient(netID, clientID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    client = c_Client()
    client.ID = response['id']
    client.mac = response['mac']
    client.description = response['description']
    client.ip = response['ip']
    client.vlan = response['vlan']
    return(clientList)

def getNetClientsAppUsage(netID, clients):
    """
    Obtains the application usage for the provided clients on a network. Seems to only return for one cleint regardless of the list size though. Best option is to just do a list of one ID and it'll return for that specific client
    
    :usage: getNetClientsAppUsage(string of network ID, list of clients) -> data usage object
    :param netID: ID of the network
    :param clients: List of clients' id, mac, or ip
    :returns: Data usage object containing application, sent, and received
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    # pull also contains client ID, mac, and IP
    try:
        response = DASHBOARD.networks.getNetworkClientsApplicationUsage(netID, clients, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    r = response[0]['applicationUsage']
    app = c_Data_Usage()
    app.app = r['application']
    app.received = r['recv']
    app.sent = r['sent']
    return(app)

def getNetClientsBandwidth(netID, key):
    """
    Obtains the total bandwidth usage for all clients on a network
    
    :usage: getNetClientsBandwidth(string of network ID) ->
    :param netID: ID of the network
    :returns:
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             Error: networks object has no attribute getNetworrkClientsBandwidthUsageHistory for literally everything

    """

    # can include starting before/after or timespan in the query
    # doesn't appear to work for some reason, might have to go through get request
    try:
        response = DASHBOARD.networks.getNetworkClientsBandwidthUsageHistory(netID, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    #try:
    #    r = requests.get(('https://api.meraki.com/api/v1/networks/%s/clients/bandwidthUsageHistory') % (netID), headers={'X-Cisco-Meraki-API-Key': key, 'Content-Type': 'application/json', 'Accept': 'application/json'})
    #    print(r)
    #except:
    #    print('Error')
    #    return(None)
    #if r.status_code != requests.codes.ok:
    #    print('processing incorrectly. code %s', (r.status_code)
    #rjson = r.json()
    #print(rjson)
    
    

def getNetClientsOverview(netID):
    """
    Obtains an overview of the clients' statistics
    
    :usage: getNetClientsOverview(string of the network ID) -> {counts:{total int, withHeavyUsage int}, usages:{average int, withHeavyUsageAverage int}}
    :param netID: ID of the network
    :returns: Dictionary of counts and usages, each a dictionary partitioned into average and with heavy usage. 
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.getNetworkClientsOverview(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    return(response)

def getNetClientsUsage(netID, clients):
    """
    Obtains data usage for clients on a network
    
    :usage: getNetClientsUsage(string of netID, list of clients) -> list[data usage objects]
    :param netID: ID of the network
    :param clients: List of client IDs, MACs, or IPs
    :returns: List of data usage objects containing timestamp, sent, and received
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    # probably want to remove timestamp
    try:
        response = DASHBOARD.networks.getNetworkClientsUsageHistories(netID, clients, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    r = response[0]['usageHistory']
    data = c_Data_Usage()
    data.timestamp = r['ts']
    data.received = r['recv']
    data.sent = r['sent']
    return(data)

def getNetClientUsage(netID, clientID):
    """
    Obtains the data usage for a specific client on a network
    
    :usage: getNetClientUsage(string of network ID, string of client ID) -> data usage object
    :param netID: ID of the network
    :param clientID: ID of the client
    :returns: Data usage object
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    # better function than clients usage imo. might want to combine all of these get multiple/single in the future tho
    try:
        response = DASHBOARD.networks.getNetworkClientsUsageHistory(netID, clientID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    r = response[0]
    data = c_Data_Usage()
    data.timestamp = r['ts']
    data.received = r['recv']
    data.sent = r['sent']
    return(data)

def getNetClientTraffic(netID, clientID):
    """
    Obtains a client's network traffic data
    
    :usage: getNetClientTraffic(string of network ID, string of client ID) -> list[data usage objects] 
    :param netID: ID of the network
    :param clientID: ID of the client
    :returns: List of data usage objects containing application, port, received, sent, and timestamp
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    # pull also contains destination, protocol, numflows(?), and active seconds
    try:
        response = DASHBOARD.networks.getNetworkClientTrafficHistory(netID, clientID, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    trafficList = []
    i = 0
    for r in response:
        trafficList.append(c_Data_Usage())
        trafficList[i].app = r['application']
        trafficList[i].port = r['port']
        trafficList[i].received = r['recv']
        trafficList[i].sent = r['sent']
        trafficList[i].timestamp = r['ts']
        i += 1
    return(trafficList)

def getDevClients(devSerial):
# this pull also obtains the aggregate usage of the client (sent/received), its user, switchport, adaptive policy group, and mdns name. Adapt class to account for these if need be by adding attributes          
# 400 bad request if used on a camera 
    """
    Compiles a list of client objects for a given device with attributes ID, description, mac, IP, vlan, and dhcp hostname (doesn't work for cameras)
    
    :usage: getDevClients(String of device serial) -> list[client objects]
    :param devSerial: Serial of the device that you want to obtain the clients for
    :returns: List of client objects 
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             400 bad request if used on a camera
    """
    try:
        response = DASHBOARD.devices.getDeviceClients(devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    clientList = []
    i = 0
    for client in response:
        clientList.append(c_Client())
        if 'id' in client:
            clientList[i].ID = client['id']
        if 'description' in client:
            clientList[i].description = client['description']
        if 'mac' in client:
            clientList[i].mac = client['mac']
        if 'ip' in client:
            clientList[i].ip = client['ip']
        if 'vlan' in client:
            clientList[i].vlan = client['vlan']
        if 'dhcpHostname' in client:
            clientList[i].hostname = client['dhcpHostname']
        i += 1
    return clientList

# Doesn't have the DC IPs 
def getNetPolicies(netID):
    """
    Compiles the policies of the network such as scheduling, bandwidth settings, firewall, and traffic shaping settings into a csv for testing.
    
    :usage: getNetPolicies(String of network ID) -> csv[json format of policies]
    :param netID: ID of the network
    :returns: CSV file in the reports directory 
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    # contains group policy ID, name, scheduling, bandwidth with settings and limits, firewall and traffic shaping (used for this function), and splash authentication settings, which contain vlan tagging and bounjour forwarding
    try:
        response = DASHBOARD.networks.getNetworkGroupPolicies(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/networkPoliciesTest.csv', 'a', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        for r in response:
            if 'firewallAndTrafficShaping' in r:
                traffic = r['firewallAndTrafficShaping']
                if 'trafficShapingRules' in traffic:
                    writer.writerow([traffic['trafficShapingRules']])

def getDevLLDP(devSerial):
# LLDP/ CDP doesn't appear to be useful yet in that it is all the ports of each protocol and the cdp and/or lldp at each port, device, ID, address, and source
    """
    Compiles LLDP and CDP information for a device in a CSV file
    
    :usage: getDevLLDP(String of device serial) ->csv[json format of ports for the protocols]
    :param devSerial: Seriial of the device
    :returns: CSV file in the reports directory
    :raise: API error if API key is faulty
            Error on str object if dashboard key isn't initialized
    """
    try:
        response = DASHBOARD.devices.getDeviceLldpCdp(devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/lldpTest.csv', 'a', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow([response])

def getNetTopology(key, netID):
# Device nodes of the network, configurable into a graph 
    """
    Still in development due to the pull from meraki being unavailable through their API currently; it needs to be done through get requests
    Obtains a json of the network topology for a given network in the form of graph nodes.
    :usage: getNetTopology(String of API key, String of network ID) -> printed json of nodes
    :param key: API key
    :param netID: ID of the network
    :returns: Printed json of the network topology nodes
    :raises: API error if API key is faulty
    """

# not configured for meraki python library yet. need to use get requests
   # try:
   #     response = DASHBOARD.networks.getNetworkTopologyLinkLayer(netID)
   # except meraki.APIError as e:
   #     print('Error: %s' % e.message)
   #     return(None)
   # except Exception as e:
   #     print('Error: %s' % e)
   #     return(None)
   # with open('topologyTest.csv', 'a', newline='\n') as f:
   #     writer = csv.writer(f, delimiter = ',')
   #     for r in response:
   #         writer.writerow([r])
    try:
        r = requests.get(('https://api.meraki.com/api/v1/networks/%s/topology/linkLayer') % (netID), headers={'X-Cisco-Meraki-API-Key': key, 'Content-Type': 'application/json', 'Accept': 'application/json'})
    except:
        print('Error')
        return(None)
    if r.status_code != requests.codes.ok:
        print('processing incorrectly')
    rjson = r.json()
    print(rjson)


def getNetTrafficApps(netID):
# nothing I want currently. It appears to be returning all the apps on meraki/ downloaded through meraki. Examples: Instagram, Playstation, Facebook
    """
    Compiles all apps downloaded through meraki/ on meraki into a csv.
    
    :usage: getNetTrafficApps(String of network ID) -> csv[json format of apps]
    :param netID: ID of the network
    :returns: CSV file in reports directory
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    """
    try:
        response = DASHBOARD.networks.getNetworkTrafficShapingApplicationCategories(netID, total_pages = 'all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    with open('/home/ccorby/meraki/project1_ccorby/meraki_lib/reports/trafficTest.csv', 'a', newline='\n') as f:
        writer = csv.writer(f, delimiter = ',')
        writer.writerow([response])

# Similar json pull of orgDevsStats has status and last reported at fields of the device, along with dns numbers, lanIP, and gateway number
def getOrgDevs(orgID):
    """
    Compiles a list of device objects for a given organization with name, serial, model, and network ID attributes

    :usage: getOrgDevs(String of organziation ID) -> list[device objects]
    :param orgID: ID of the organziation you wish to obtain devices for
    :returns: list of device objects with name, serial, model, and network ID
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    """
    try:
        response = DASHBOARD.organizations.getOrganizationDevices(orgID, total_pages = 'all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    devList = []
    i = 0
    for dev in response:
        # for some reason, there's devices still in the system even though they've been "removed": says "Dead: has been removed" for name                                               
        devList.append(c_Dev())
        if 'name' in dev and dev['name'] != '':
            devList[i].name = dev['name']
        else:
            devList[i].name = "Unnamed device"
        devList[i].serial = dev['serial']
        devList[i].model = dev['model']
        devList[i].netID = dev['networkId']
        devList[i].firmware = dev['firmware']
        devList[i].productType = dev['productType']
        i+=1
    return(devList)

def getOrgDevStats(orgID):
    """
    """
    # also includes primary/secondary dns, product type, and components
    try:
        response = DASHBOARD.organizations.getOrganizationDevicesStatuses(orgID, total_pages = 'all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    devList = []
    i = 0
    for dev in response:
        devList.append(c_Dev())
        if 'name' in dev and dev['name'] != '' and dev['name'] != '':
            devList[i].name = dev['name']
        else:
            devList[i].name = "Unnamed device"
        devList[i].serial = dev['serial']
        devList[i].model = dev['model']
        devList[i].netID = dev['networkId']
        devList[i].pub_ip = dev['publicIp']
        if 'lastReportedAt' in dev:
            devList[i].lastReorted = dev['lastReportedAt']
        else:
            devList[i].lastReorted = 'N/A'
        if 'lanIp' in dev:
            devList[i].lan_ip = dev['lanIp']
        else:
            devList[i].lan_ip = 'not configured'
        #devList[i].gateway = dev['gateway']
        i+=1
    return(devList)

def getOrgClient(orgID, clientMac):
    """
    Obtain the details for a client on an organization.
    
    :usage: getOrgClient(string of organization ID, string of client MAC) -> client object
    :param orgID: ID of the organization
    :param clientMac: MAC address of the client
    :returns: Client object containing details for the desired client
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized

    """
    try:
        response = DASHBOARD.organizations.getOrganizationClientsSearch(orgID, clientMac, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    client = c_Client()
    client.ID = response['clientId']
    client.mac = response['mac']
    # also contains manufacturer, and records. records contains the network with all its respective info, and then the rest of the client data like description, switchport, wirelesscapabilities, smInstalled, ssid, etc
    # records is a list of these though so parsing and figuring out which info is desired will be a pain
    return(client)

def getOrgClientsOverview(orgID):
    """
    Doesn't work. No attribute for it on the organziations object
    """
    try:
        response = DASHBOARD.organizations.getOrganizationClientsOverview(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    
def getOrgClientsBandwidth(orgID):
    """ 
    Obtains the total bandwidth usage for all clients on an organziation

    :usage: getOrgClientsBandwidth(string of organization ID) ->
    :param orgID: ID of the organization
    :returns:
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    # should return timestamp, total, upstream, and downstream
    # doesn't appear to work for some reason, might have to go through get request
    try:
        response = DASHBOARD.organizations.getOrganizationClientsBandwidthUsageHistory(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

# Only applicable to MX devices
# Pull also gives vlanID and usedCount/freeCount
def getDeviceDHCPSubnets(devSerial):
    """
    Compiles a list of subnets for a given MX device. Incompatible with other devices
    
    :usage: getDeviceSubnets(String of device Serial) -> list[subnets]
    :param devSerial: Serial of the MX device
    :returns: List of subnets
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             400 bad request if not used on an MX device
    """
    try:
        response = DASHBOARD.appliance.getDeviceApplianceDhcpSubnets(devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    subnetList = []
    for r in response:
        if 'subnet' in r and r['subnet']:
            subnetList.append(r['subnet'])
    return subnetList

def getDeviceUplinkSettings(devSerial):
    try:
        response = DASHBOARD.appliance.getDeviceApplianceUplinksSettings(devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    return response

def getNetVlans(netID):
    try:
        response = DASHBOARD.appliance.getNetworkApplianceVlans(netID)
    except meraki.APIError as e:
        if 'VLANs are not enabled for this network' not in e.message['errors'] and 'This endpoint only supports MX networks' not in e.message['errors']:
            print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    vlanList = []
    i = 0
    for r in response:
        vlanList.append(c_Vlan())
        vlanList[i].ID = r['id']
        vlanList[i].name = r['name']
        vlanList[i].subnet = r['subnet']
        i += 1
    return vlanList

def getConnectDestinations(netID):
    """
    dashboard.appliance.getnetworkapplianceconnectivitymonitoringdestinations(netid)
    """
    try:
        response = DASHBOARD.appliance.getNetworkApplianceConnectivityMonitoringDestinations(netID)
    except meraki.APIError as e:
        if 'This network does not support connectivity monitoring destinations' not in e.message['errors']:
            print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if 'destinations' in response:
        return(response['destinations'])
    else:
        return(None)


def getNetVPNSitetoSite(netID):
    """
    VPN site-to-site settings like hub id and subnets. additionally, whether or not local subnet is true
    """
    try:
        response = DASHBOARD.appliance.getNetworkApplianceVpnSiteToSiteVpn(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getUplinkStatus(orgID):
    """
    Compiles a list of device objects for a given organization with network ID, serial, model, WAN status and WAN IP attributes
    
    :usage: getUplinkStatus(String of organziation ID) -> list[device objects]
    :param orgID: ID of the organziation you wish to obtain devices for
    :returns: list of device objects with serial, model, WAN status, WAN IP, and network ID attributes
    :raises: API error if key is bad
             Error on str object if dashboard key isn't initialized
    """
    try:
        response = DASHBOARD.organizations.getOrganizationUplinksStatuses(orgID, total_pages = 'all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    devList = []
    i = 0
    for dev in response:
        devList.append(c_Dev())
        devList[i].netID = dev['networkId']
        devList[i].serial = dev['serial']
        devList[i].model = dev['model']
        devList[i].lastReported = 'N/A'
        if 'lastReportedAt' in dev and dev['lastReportedAt'] != None:
            est = UTCtoEST(dev['lastReportedAt'])
            devList[i].lastReported = est
        uplinks = dev['uplinks']
        for uplink in uplinks:
            wan = uplink['interface']
            if wan == 'wan1':
                devList[i].wan1_stat = uplink['status']
                devList[i].wan1_ip = uplink['ip']
                devList[i].wan1_pub_ip = uplink['publicIp']
                devList[i].wan1_gateway = uplink['gateway']
            elif wan == 'wan2':
                devList[i].wan2_stat = uplink['status']
                devList[i].wan2_ip = uplink['ip']
                devList[i].wan2_pub_ip = uplink['publicIp']
                devList[i].wan2_gateway = uplink['gateway']
        if not hasattr(devList[i], 'wan1_ip'):
            devList[i].wan1_ip = 'not configured'
        if not hasattr(devList[i], 'wan2_ip'):
            devList[i].wan2_ip = 'not configured'
        if not hasattr(devList[i], 'wan1_pub_ip'):
            devList[i].wan1_pub_ip = 'not configured'
        if not hasattr(devList[i], 'wan2_pub_ip'):
            devList[i].wan2_pub_ip = 'not configured'
        if not hasattr(devList[i], 'wan1_stat'):
            devList[i].wan1_stat = 'not configured'
        if not hasattr(devList[i], 'wan2_stat'):
            devList[i].wan2_stat = 'not configured'
        if not hasattr(devList[i], 'wan1_gateway'):
            devList[i].wan1_gateway = 'not configured'
        if not hasattr(devList[i], 'wan2_gateway'):
            devList[i].wan2_gateway = 'not configured'
        i+=1
        
    return(devList)

def test(orgID):
    try:
        response = DASHBOARD.organizations.getOrganizationUplinksStatuses(orgID, total_pages = 'all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    devList = []
    i = 0
    for dev in response:
        devList.append(c_Dev())
        devList[i].netID = dev['networkId']
        devList[i].serial = dev['serial']
        devList[i].model = dev['model']
        devList[i].lastReported = 'N/A'
        if 'lastReportedAt' in dev and dev['lastReportedAt'] != None:
            est = UTCtoEST(dev['lastReportedAt'])
            devList[i].lastReported = est
        uplinks = dev['uplinks']
        for uplink in uplinks:
            wan = uplink['interface']
            if wan == 'wan1':
                devList[i].wan1_ip = uplink
            elif wan == 'wan2':
                devList[i].wan2_ip = uplink
        if not hasattr(devList[i], 'wan1_ip'):
            devList[i].wan1_ip = ''
        if not hasattr(devList[i], 'wan2_ip'):
            devList[i].wan2_ip = ''
        i+=1

    return(devList)


def getNetCellGateway(netID):
    """
    Compiles a list of gateway IPs for a network

    :usage: getNetCellGateway(String of network ID) -> list of IPs
    """
    try:
        response = DASHBOARD.cellularGateway.getNetworkCellularGatewayConnectivityMonitoringDestinations(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    ipList = []
    for ip in response['destinations']:
        ipList.append(ip['ip'])
    return(ipList)

def getNetFirewallNatRules(netID):
    """                                                                                                                                                                                                                                    Compiles a list of network firewall rules

    :usage: getNetFirewallNatRules(String of network ID) -> list of rules
    """
    try:
        response = DASHBOARD.appliance.getNetworkApplianceFirewallOneToOneNatRules(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    return(response)

def getNetFirewallPortForwardingRules(netID):
    """
    Compiles a list of network firewall port forwarding rules

    :usage: getNetFirewallPortForwardingRules(String of network ID) -> list of rules   
    """
    try:
        response = DASHBOARD.appliance.getNetworkApplianceFirewallPortForwardingRules(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    return(response)

# 400 bad request if used on a camera
def getDDNSConfiguration(devSerial):
    # format of json is ddnsHostnames, wan1, wan2
    # ddnshostnames has active, wan1, wan2
    # wan1 has wanEnabled, usingStaticIp, staticIp, staticSubnetMask, staticGatewayIp, staticDns, vlan
    # wan2 has wanEnabled, usingStaticIp, vlan

    """
    Compiles a dictonary of ddns hostnames for the device and its WANs. Incompatible with cameras
    
    :usage: getDDNSConfiguration(String of device serial) -> dictionary{String of active or wan: String of hostname}
    :param devSerial: Device Serial
    :returns: Dictionary mapping active, wan1, and wan2 to their hostnames
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialzied
             400 bad request if used on a camera

    """
    hostDict = {'active':'not supported', 'wan1':'not supported', 'wan2':'not supported'}
    try:
        response = DASHBOARD.devices.getDeviceManagementInterface(devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return({'active':'not supported', 'wan1':'not supported', 'wan2':'not supported'})
    except Exception as e:
        print('Error: %s' % e)
        return({'active':'Error', 'wan1':'Error', 'wan2':'Error'})
    hostDict = {'active':'not configured', 'wan1':'not configured', 'wan2':'not configured'}
    if 'ddnsHostnames' in response:
        hostDict['active'] = response['ddnsHostnames']['activeDdnsHostname']
        hostDict['wan1'] = response['ddnsHostnames']['ddnsHostnameWan1']
        hostDict['wan2'] = response['ddnsHostnames']['ddnsHostnameWan2']
    return(hostDict)

def getDevManagementInterface(devSerial):
    try:
        response = DASHBOARD.devices.getDeviceManagementInterface(devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getEventTypes(netID):
    """
    Compiles a list of event types for a network
    
    :usage: getEventTypes(String of network ID) -> list[Event type]
    :param netID: ID of the network 
    :returns: List of event types
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    """
    # each event has category, type, and description
    try: 
        response = DASHBOARD.networks.getNetworkEventsEventTypes(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    eventList = []
    for r in response:
        if r['type'] not in eventList:
            eventList.append(r['type'])
    return(eventList)

# Can filter by time, date, event type, device
# Can only do starting before OR ending before for some reason
# TYPE IS FAILOVER EVENT FOR PRIMARY UPLINK CHANGE
def getNetEvents(netID):
    """
    Prints all the events for a given network
    
    :usage: getNetEvents(String of network ID) -> printed events for the network
    :param netID: ID of the network
    :returns: Printed events in json format
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    # each event has time occurred, type, description, client info, device info, ssid info, and event data: channel, radio, vap, rssi, aid, etc
    try:
        # appliance is a MX
        # range for pages is 3-1000. default is 10
        # Time needs to be ISO 8601: YYYY-MM-DDThh:mm:ss where T is actually in the string
        response = DASHBOARD.networks.getNetworkEvents(netID, productType='appliance', includedEventTypes='failover_event', total_pages=10)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    events = response['events']
    for event in events:
        print(event)
        
# Starting after/ ending before doesn't work in the pull. Lots of overhead but oh well
def getUplinkChange(netID):
    """
    Obtains the primary uplink status change events for a network
    
    :usage: getUplinkChange(String of network ID) -> list[Uplink event objects]
    :param netID: ID of the network
    :returns: List of uplink event objects
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.getNetworkEvents(netID, productType='appliance', includedEventTypes='failover_event', total_pages=3)
    except meraki.APIError as e:
        # two common errors that are pretty self explainatory: can't be used on x network
        if 'productType is not applicable to this network' not in e.message['errors'] and 'This endpoint only supports MX networks' not in e.message['errors']:
            print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('oops here')
        print('Error: %s' % e)
        return(None)
    eventList = []
    events = response['events']
    i = 0
    # dictonary mapping device serial to list of time and place in event List so that the list is only storing the last event for each device
    devices = {}
    if events != None:
        for event in events:
            if 'deviceSerial' in event:
                devSerial = event['deviceSerial']
                est = UTCtoEST(event['occurredAt'])
                if devSerial in devices.keys():
                    time = devices[devSerial][0]
                    index = devices[devSerial][1]
                    # older events are considered less in time
                    if est > time:
                        # updating event in event list
                        if 'uplink' in event['eventData']:
                            if event['eventData']['uplink'] == '0':
                                eventList[index].uplinkActive = 'WAN1'
                            elif event['eventData']['uplink'] == '1':
                                eventList[index].uplinkActive = 'WAN2'
                            elif event['eventData']['uplink'] == '2':
                                eventList[index].uplinkActive = 'CELLULAR'
                        else:
                            eventList[index].uplinkActive = 'N/A'
                        eventList[index].time = est
                        devices[devSerial] = [est, index]
                else:
                    eventList.append(c_Uplink_Event())
                    eventList[i].devName = event['deviceName']
                    eventList[i].devSerial = devSerial
                    if 'uplink' in event['eventData']:
                        if event['eventData']['uplink'] == '0':
                            eventList[i].uplinkActive = 'WAN1'
                        elif event['eventData']['uplink'] == '1':
                            eventList[i].uplinkActive = 'WAN2'
                        elif event['eventData']['uplink'] == '2':
                            eventList[i].uplinkActive = 'CELLULAR'
                    else:
                        eventList[i].uplinkActive = 'N/A'
                    eventList[i].time = est
                    devices[devSerial] = [est, i]
                    i += 1
    return eventList

def getOrgSNMP(orgID):
    """
    Compiles a dictonary of the status of what SNMP version is active for the organization
    
    :usage: getOrgSNMP(String of organization ID) -> dictionary{String of v2/v3: Enabled/Disabled}
    :param orgID: ID of the organization that the network is under
    :reutrns: Dictionary mapping v2/v3 to status
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    # easier to return a dictionary of null in exception handling to give a visual in the database
    try:
        response = DASHBOARD.organizations.getOrganizationSnmp(orgID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return({'v2':'not supported','v3':'not supported'})
    except Exception as e:
        print('Error: %s' % e)
        return({'v2':'Error', 'v3':'Error'})
    # initialize both to disabled and only change to enabled if conditions are met
    # leads to less nested if statements
    SNMPdict = {'v2':'Disabled', 'v3':'Disabled'}
    if 'v2cEnabled' in response:
        # enabled status is a boolean, need to change to a string
        if response['v2cEnabled']:
            SNMPdict['v2'] = 'Enabled'
    if 'v3Enabled' in response:
        # enabled status is a boolean                                                   
        if response['v3Enabled']:
            SNMPdict['v3'] = 'Enabled'
    return(SNMPdict)

def updateOrgSNMP(orgID, v2c=None, v3=None, v3Auth=None, v3Priv=None, IPs=None):
    """
    Updates the SNMP settings for an organziation
    
    :usage: updateOrgSNMP(String of organziation ID, boolean of v2c, boolean of v3, string of v3Auth, string of v3Priv, list of IPs)
    :param orgID: ID of the organziation
    :paran v2c: Boolean for whether or not v2c is enabled
    :param v3: Boolean for whether or not v3 is enabled
    :param v3Auth: Either MD5 or SHA. v3 Authentication mode
    :param v3Priv: Either DES or AES128. v3 Privacy mode
    :param IPs: List of IPs that can access SNMP server
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initalized through createDashboard
    
    """
    try:
        response = DASHBOARD.organizations.updateOrganizationSnmp(orgID, v2cEnabled=v2c, v3Enabled=v3, v3AuthMode=v3Auth, v3PrivMode=v3Priv, peerIps=IPs)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)


def getNetCommunityString(netID):
    """
    Obtains the community string for a network

    :usage: getNetCommunityString(String of netID) -> String of community string
    :param netID: ID of the network
    :returns: Community string or none if error/nonexistent 
    :raises: API error if API key is faulty
             Error ons tr object if dashboard key isn't iniitalized
    
    """
    # also contains the type of access as key accesses
    try:
        response = DASHBOARD.networks.getNetworkSnmp(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if 'communityString' in response:
        return(response['communityString'])
    else:
        return(None)

def getNetSNMP(netID):
    """                                                                                  
    Obtains the SNMP information for a network
                                                                                         
    :usage: getNetCommunityString(String of netID) -> dict{access: String, communityString:String, users:list}. communityString is given if access is community, users is given if access is users
    :param netID: ID of the network                                                      
    :returns: Type of access and user log in info/ community string in a dictionary. user log in info is a list of dictionaries containing username and passphrase
    :raises: API error if API key is faulty                                                 
             Error on str object if dashboard key isn't initialized                      
    
    """
    try:
        response = DASHBOARD.networks.getNetworkSnmp(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    return(response)

def updateNetSNMP(netID, access=None, communityString=None, users=None):
    """
    Updates the SNMP information for a network
    
    :usage: updateNetSNMP(String of netID, string of access, string of community string, list of users)
    :param netID: ID of the network
    :param access: Can be either users or community
    :param communityString: SNMP community string. Only applicable if access is community
    :param users: List of dictionaries: {username:String, passphrase:String} for each user. Only applicable if access is users
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        # need to know if users and community string are ignored if not relevant or if it needs to be a simple condiitonal of if _ is None etc
        response = DASHBOARD.networks.updateNetworkSnmp(netID, access=access, communityString=communityString, users=users)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    return(response)

def getNetflow(netID):
    """
    Compiles a dictonary of the status of traffic reporting and the collector port/IP for a network
    
    :usage: getNetflow(String of netID) -> dictionary{traffic reporting, collectorIP, collectorPort}
    :param netID: ID of the network
    :returns: Dictionary of traffic reporting and collector port/IP
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    """
    netflowDict = {'trafficReporting':'not supported','collectorIP':'None','collectorPort':'None'}
    try:
        response = DASHBOARD.networks.getNetworkNetflow(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(netflowDict)
    except Exception as e:
        print('Error: %s' % e)
        return({'trafficReporting':'Error','collectorIP':'Error','collectorPort':'Error'})
    # boolean as to whether or not the reporting is enabled.
    # if it's not true, there's no IP/Port
    enabled = response['reportingEnabled']
    if enabled:
        netflowDict['trafficReporting'] = 'Enabled'
        netflowDict['collectorIP'] = response['collectorIp']
        netflowDict['collectorPort'] = response['collectorPort']
    else:
        netflowDict['trafficReporting'] = 'Disabled'
    return(netflowDict)

# This also pulls default uplink and traffic preferences like filtering a cidr or protocol over WAN and vpn
# returns bad request if network doesn't have failover capable MX or routed mode enabled
def getLoadBalancingStatus(netID):
    """
    Obtains whether or not load balancing is enabled for a network
    
    :usage: getLoadBalancingStatus(String of network ID) -> String saying enabled or disabled
    :param netID: ID of the network
    :returns: Enabled or disabled
    :rasies: API error if API key is faulty
            Error on str object if dashboard key isn't initialized
            400 bad request if network doesn't have failover capable MX or routed mode enabled

    """
    try:
        response = DASHBOARD.appliance.getNetworkApplianceTrafficShapingUplinkSelection(netID)
    except meraki.APIError as e:
        if 'Unsupported for networks without a failover capable MX' in e.message['errors'][0] or 'Unsupported for networks without routed mode (NAT) enabled' in e.message['errors'][0]:
            return('not supported or not configured')
        else:
            print('Error: %s' % e.message)
            return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if 'loadBalancingEnabled' in response:
        if response['loadBalancingEnabled'] == True:
            return 'Enabled'
    # Disabled if there's no json or the json is false
    return 'Disabled'

def getNetUplinkUsage(netID):
    """
    Obtains the usage history for a network's uplinks.

    :usage: getNetUplinkUsage(String of network ID) -> 
    :param netID: ID of the network
    :returns: 
    :raises:
    
    """
    try:
        response = DASHBOARD.appliance.getNetworkApplianceUplinksUsageHistory(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

# Same dashboard pull as load balancing status function. can also pull traffic destination preferences/ filtering
def getPrimaryUplink(netID):
    """
    Obtains whether WAN1 or WAN2 is the primary uplink
    
    :usage: getPrimaryUplink(String of network ID) -> String of WAN1, WAN2, or not configured
    :param netID: ID of the network
    :returns: WAN1, WAN2, or not supported or not configured
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             400 bad request if network doesn't have failover capable MX
    """
    try:
        response = DASHBOARD.appliance.getNetworkApplianceTrafficShapingUplinkSelection(netID)
    except meraki.APIError as e:
        # These are two known errors that just mean I'm running it on a network that has no valuable info
        if 'Unsupported for networks without a failover capable MX' in e.message['errors'] or 'Unsupported for networks without routed mode (NAT) enabled' in e.message['errors'] or 'This endpoint only supports MX networks' in e.message['errors']:
            return('not supported or not configured')
        else:
            print('Error: %s' % e.message)
            return('Error')
    except Exception as e:
        print('Error: %s' % e)
        return('Error')
    if 'defaultUplink' in response:
        # wan1 and wan2 are lowercase in the json, and I simply prefer it to be upper case
        return response['defaultUplink'].upper()
    return('not supported or not configured')

def getAlertsandRecipients(netID):
    """
    Compiles a list of alert settings for a network, with each alert having the type, if it's enabled, and the recipients
    
    :usage: getAlertsandRecipients(String of network ID) -> list[alert objects]
    :param netID: ID of the network
    :returns: List of alert objects
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    """
    # default destinations contains emails list, allAdmins, snmp, httpServerIds
    # alerts contains type, enabled, alertDestinations, and filters dictionary
    #alert destinations contains the same as default dest
    try:
        response = DASHBOARD.networks.getNetworkAlertsSettings(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    alertList = []
    i = 0
    if 'defaultDestinations' in response and 'alerts' in response:
        alerts = response['alerts']
        if not response['defaultDestinations']['emails']:
            default_emails = 'None'
        else:
            default_emails = response['defaultDestinations']['emails']
        for a in alerts:
            alertList.append(c_Alert())
            alertList[i].enabled = 'Disabled'
            alertList[i].alertType = a['type']
            if 'enabled' in a and a['enabled'] != '':
                if a['enabled'] == True:
                    alertList[i].enabled = 'Enabled'
            if not a['alertDestinations']['emails']:
                alertList[i].emails = 'None'
            else:
                alertList[i].emails = a['alertDestinations']['emails']
            alertList[i].default = default_emails
            i += 1
    return(alertList)
            
def getDev(devSerial):
    """
    Compiles a device object for the given serial with model, name, and serial.

    :usage: getDev(String of Serial) -> device object
    :param devSerial: Serial of the device you wish to obtain the information for
    :returns: Device object
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    # this json contains name, lat, lng, serial, mac, model, address, notes, lanIP, tags, netID, beaconIDs, firmware, and floorplan ID
    
    try:
        response = DASHBOARD.devices.getDevice(devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if 'name' in response:
        dev = c_Dev()
        dev.name = response['name']
        dev.serial = response['serial']
        dev.model = response['model']
        return(dev)

def updateDev(devSerial):
    """
    Sets attributes of a device
    """
    #form is as follows:
    #response = DASHBOARD.devices.updateDevice(devSerial, name=x, tags=[x], lat=x, lng=x...)
    return(None)


def updateManagementInterface(devSerial):
    """
    Sets wan configurations. Doesn't seem to do ddns hostnames though. TODO: investigate once test is set up
    """
    # form is as follows:
    # response = DASHBOARD.devices.updateDeviceManagementInterface(devSerial, wan1={staticIp, staticSubnetMask, staticGatewayIp, staticDns}, wan2={wanEnabled=x, usingStaticIp=x, vlan=x})
    return(None)

def blinkDevLEDs(devSerial, duration=None, period=None, duty=None):
    """
    Blinks the LEDs of a device

    :usage: blinkDevLEDs(String of device serial, optional numbers for duration, period, and duty) -> N/A
    :param devSerial: Serial of the device you want to turn the LEDs on for
    :param duration: How long blinking lasts in seconds between 5 and 120. default 20/
    :param period: How long lights are on in milliseconds between 100 and 1000. default 160
    :param duty: As per meraki's docs, the duty cycle as percent active. Somewhere between 10 & 90. Default is 50.
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             I assume some sort of error on incompatible devices
    """
    DASHBOARD.devices.blinkDeviceLeds(serial)
    #TODO allow for the duration, period, and duty to be incorportated. Unecessary atm

def createDevPing(devSerial):
    """
    Makes device ping a desired host
    """
    # Should probably be set as parameters. Again, not necessary atm.
    target = '' # IP of host
    count = 2 # Number of pings
    # might do the get portion too? not sure, have to check out. TODO
    DASHBOARD.devices.createDeviceLiveToolsPing(devSerial, target, count)

def getDevPing(devSerial):
    """
    Returns the results of a ping. Might want to put in one function with the create ping function
    """
    
    try:
        # not sure why it needs blank ID in the example. Probably the id of the target host. idk. can also be the ping ID
        response = DASHOARD.devices.getDeviceLiveToolsPing(devSerial, id_='')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    # response should have the ping ID, url, what the ping request was, the status & results, and any replies

def rebootDev(devSerial):
    """
    Reboots a device and returns if it was successful
    """
    try:
        response = DASHOARD.devices.rebootDevice(devSerial, id_='')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getDevLoss(devSerial, ip):
    """
    Obtains the loss and latency history of a device
    """
    try:
        # can also include timespan, resolution, and uplink (defaulted to WAN1 if not specified)
        response = DASHOARD.devices.getDeviceLossAndLatencyHistory(devSerial, ip)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getNet(netID):
    """
    Returns a network object for the given ID containing ...

    :usage: getNet(String of network ID) -> Network Object
    :param netID: ID of the network
    :returns: Network Object
    :raises: API error if API key is faulty
             Error on str object if dashsboard key isn't initialized

    """
    # contains id, orgID, name, productTypes list, timezone, tags, enrollmentString, url, notes
    try:
        response = DASHBOARD.networks.getNetwork(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    net = c_Net()
    net.ID = response['id']
    net.orgID = response['organizationId']
    net.name = response['name']
    net.tz = response['timeZone']
    net.tags = response['tags']
    net.productTypes = response['productTypes']
    net.enrollmentString = response['enrollmentString']
    net.notes = response['notes']
    return(net)

def updateNet(netID, name, timezone, tags, notes):
    """
    Sets attributes of a network
    """
    # all are strings other than tags which is list of strings
    response = DASHBOARD.networks.updateNetwork(netID, name=name, timeZone=timezone, tags=tags, notes=notes)
    # response will be the updated json for a network. maybe return this?

def deleteNet(netID):
    """ 
    Deletes a network from the dashboard
    
    :usage: deleteNet(String of network ID) -> success or failure as a string?
    :param netID: ID of the network
    :returns: Success or failure string
    :raises: API error if API key is faulty
             Error on str object if dashsboard key isn't initialized
 
    """
    try:
        response = DASHBOARD.networks.deleteNetwork(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    
def updateNetworkAlertSettings(netID, default, alerts):
    """
    Updates the alert settings for a network
    """
    
    # default destinations is a json dict of emails list, allAdmins, snmp, httpServerIds list
    # alerts is list of json dict of type, enabled, alertDestinations, filters
    # alertDestinations is json dict containingthe same as default destinations
    
    try:
        response = DASHBOARD.networks.updateNetworkAlertsSettings(netID, defaultDestinations=default, alerts=alerts)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def bindNet(netID, template):
    """
    Binds a network to a config template, which is recognized by ID?
    """
    # autobind defaults to off and automatically binds to same model switch networks
    # confused by this. look into
    try:
        response = DASHBOARD.networks.bindNetwork(netID, config_template_id, autoBind=False)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def provisionClients(netID, clients, devPolicy, groupPolicyID=None):
    """
    Sets a policy to the given list of clients
    
    :usage: provisionClients(string of network id, list of client objects, string of device policy, optional string of group policy id)
    :param netID: ID of the network
    :param clients: list of client objects requiring mac, clientID, and name
    :param devPolicy: String of the policy. Either Group policy, Allowed, Blocked, Per connection, or Normal
    :param groupPolicyID: String of the group policy ID if devPolicy is Group Policy
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    """
    # group policy id is apparently ignored if devPolicy isn't group policy. need to test whether or not it can be passed as none
    # clients needs to be turned into a list of dictionaries from a list of objects
    jsonClients = []
    for client in clients:
        # check whether or not description == name. i think it is
        clientDict = {'mac':client.mac, 'clientId':client.ID, 'name':client.description}
        jsonClients.append(clientDict)
    try:
        response = DASHBOARD.networks.provisionNetworkClients(netID, jsonClients, devPolicy, groupPolicyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getNetClientPolicy(netID, clientID):
    """
    Obtains the policy for a client on a given network
    
    :usage: getNetClientPolicy(string of network ID, string of client ID) -> Dictionary{mac:String, device policy:String, group policy ID:String}
    :param netID: ID of the network
    :param clientID: ID of the client
    :returns: Dictionary of mac, device policy string, and group policy ID
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.getNetworkClientPolicy(netID, clientID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateNetClientPolicy(netID, clientID, devPolicy, groupPolicyID=None):
    """
    Updates the policy for a client on a given network
    
    :usage: provisionClients(string of network id, string of client id, string of device policy, optional string of group policy id)
    :param netID: ID of the network
    :param clientID: ID of the network
    :param devPolicy: String of the policy. Either Group policy, Whitelisted, Blocked, or Normal
    :param groupPolicyID: String of the group policy ID if devPolicy is Group Policy
    :returns: N/A
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.updateNetworkClientPolicy(netID, clientID, devPolicy, groupPolicyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getClientSplashAuthorization(netID, clientID):
    """
    Obtains the splash authorization for a client for each SSID
    
    :usage: getClientSplashAuthorization(string of network id, string of client id) -> List[SSID objects]
    :param netID: ID of the network
    :param clientID = ID of the client
    :returns: List of SSID objects 
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    # Everything seems to return false. Guess SSID isn't enabled?
    try: 
        response = DASHBOARD.networks.getNetworkClientSplashAuthorizationStatus(netID, clientID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    ssidList = []
    i = 0
    ssids = response['ssids']
    for key in ssids:
        ssidList.append(c_SSID())
        ssidList[i].number = key
        ssidList[i].isAuthorized = ssids[key]['isAuthorized']
        if ssidList[i].isAuthorized == True:
            ssidList[i].authorizedAt = UTCtoEST(ssids[key]['authorizedAt'])
            ssidList[i].expiresAt = UTCtoEST(ssids[key]['expiresAt'])
        else:
            ssidList[i].authorizedAt = 'N/A'
            ssidList[i].expiresAt = 'N/A'
        i += 1
    return(ssidList)
    

def updateClientSplashAuthorization(netID, clientID, ssids):
    """
    Since SSID appears to be disabled, I didn't bother with this.
    """
    #ssids has to be in the format {"Number": {"isAuthorized": True/False}} 
    # Authorized/Expires time is automatically set
    response = dashboard.networks.updateNetworkClientSplashAuthorizationStatus(netID, clientID, ssids)
    

def claimNetDevs(netID, devSerials):
    """
    Claims devices to a network
    
    :usage: claimNetDevs(String of network ID, List of device serials)
    :param netID: ID of the network you wish to claim the devices for
    :param devSerials: List of the device serials to claim
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             Probably something if the devices are already claimed

    """
    
    try:
        response = DASHBOARD.networks.claimNetworkDevices(netID, devSerials)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)

def claimvMXdev(netID, size):
    """
    Claims a vMX device to a network
    
    :usage: claimvMXdev(String of network ID, String of vMX size)
    :param netID: ID of the network you wish to claim the device for
    :param size: Size of the vMX device. Can be either small, medium, large, or 100
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             Probably something if the devices are already claimed
    
    """
    try:
        response = DASHBOARD.networks.vmxNetworkDevicesClaim(netID, devSerials)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)

def removeNetDev(netID, devSerial):
    """
    Removes a device from a network
    
    :usage: removeNetDev(String of network ID, string of device serial)
    :param netID: ID of the network the device is under
    :param devSerial: Serial of the device you wish to remove
    :returns: N/A
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.removeNetDev(netID, devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)


def getNetDevsFirmwareInfo(netID):
    """
    Obtains the firmware update information for a network
    
    :usage: getNetDevsFirmwareInfo(String of network ID)
    :param netID: ID of the network
    :returns: Dictionary mapping product type to its custom class
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    # this holds the update information for each product on a network such as switches and cameras
    # products each contain current version, last upgrade which include the time and from and to version, next upgrade with the time and to version, a list of available versions and if it's participating in beta updates
    productDict = {}
    i = 0
    try:
        response = DASHBOARD.networks.getNetworkFirmwareUpgrades(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    if 'products' in response:
        for product in response['products']:
            productDict[product] = c_Dev_Firmware()
            productDict[product].productType = product
            productDict[product].currentFirmware = productDict[product].newestFirmware = response['products'][product]['currentVersion']['firmware']
            currentVersionDate = UTCtoEST(response['products'][product]['currentVersion']['releaseDate'])
            for version in response['products'][product]['availableVersions']:
                if version['releaseType'] != 'beta':
                    versionDate = UTCtoEST(version['releaseDate'])
                    # with datetime, NEWER dates are BIGGER
                    if versionDate > currentVersionDate:
                        productDict[product].newestFirmware = version['firmware']
    return(productDict)

def updateNetUpgrades(netID, products):
    """
    Changes the next update for devices on a network
    
    :usage: updateNetUpgrades(string of network ID, dictionary of products)
    :param netID: ID of the network
    :param products: Dictionary of products such as switches, cameras, appliances, cellular gateways, etc. Each product needs to be as follows - product:{optional participateInNextBetaRelease:True/False, nextUpgrade:{optional time, toVersion:{id:ID number as a string}
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized 
                               
    """
    try:
        response = DASHBOARD.networks.updateNetworkFirmwareUpgrades(netID, products)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def rollbackNetUpgrades(netID, reasons, product, time, version):
    """
    Returns a device back to an older version
    
    :usage: rollbackNetUpgrades(string of netID, list of reasons, string of product, string of time, dictionary of version)
    :param netID: ID of the network
    :param reasons: List of dictionaries containing category and comment regarding rollback
    :param product: String of the product, such as switch or camera
    :param time: String scheduled time of the rollback in ISO 8601 format
    :param version: Dictionary of the version product is being switched to {'id':'###'}
    :returns: N/A
    :raises: API error if API key is faulty  
             Error on str object if dashboard key isn't initialized
                                                                      
    """
    try:
        response = DASHBOARD.networks.createNetworkFirmwareUpgradesRollback(netID, reasons, product=product, time=time, toVersion=version)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    

def getNetFloorPlans(netID):
    """
    Obtains the floor plans for a network
    
    :usage: getNetFloorPlans(string of network ID) -> json of the plans
    :param netID: ID of the network
    :returns: Json of the floor plans
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    """
    # very few networks have a floor plan
    # for the few that exist, this returns the ID, imageURL, expiration, extension, Md5, name, list of devices (same stuff as usual), width, height, center (dict of lat and lng), and then each corner with its lat and lng in a dict too.
    try:
        response = DASHBOARD.networks.getNetworkFloorPlans(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getNetFloorPlan(netID, floorID):
    """                  
    Obtains a single floor plan for a network

    :usage: getNetFloorPlan(string of network ID, string of floor ID) -> json of the plans
    :param netID: ID of the network
    :param floorID: ID of the floor plan
    :returns: Json of the floor plan
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initialized

    """
    # very few networks have a floor plan   
    # for the few that exist, this returns the ID, imageURL, expiration, extension, Md5, name, list of devices (same stuff as usual), width, height, center (dict of lat and lng), and then each corner with its lat and lng in a dict too.          
    try:
        response = DASHBOARD.networks.getNetworkFloorPlan(netID, floorID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def createNetFloorPlan(netID, name, image):
    """
    Creates a network floor plan on the dashboard
    
    :usage: createNetFloorPlans(string of network ID, string of name, string of image)
    :param netID: ID of the network
    :param name: Desired name of the floor plan
    :param image: base 64 encoded string of image file
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.createNetworkFloorPlan(netID, name, image)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateNetFloorPlan(netID, floorID, image=None, plan=None):
    """
    Updates a network floor plan
    
    :usage: updateNetFloorPlan(string of network ID, string of floor ID, string of image, string of name, list of plan)
    :param netID: ID of the network
    :param floorID: ID of the floor plan
    :param image: Do not submit if submitting the plan. Base 64 encoded string of the image file to be used
    :param plan: If using the image, do not submit the plan too. Dictionary mapping the name of the plan as a string to a dictionary of the plan including center, bottom left corner, etc 
    :returns: N/A
    :raises: API error if API key is faulty    
             Error on str object if dashboard key isn't initialized
                         
    """
    if image == None and plan == None:
        print('Need to have something to update with')
        return(None)
    elif image == None:
        try:
            response = DASHBOARD.networks.updateNetworkFloorPlan(netID, floorID, plan)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:   
            print('Error: %s' % e)
            return(None)
    elif plan == None:
        try:
            response = DASHBOARD.networks.updateNetworkFloorPlan(netID, floorID, image)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
    print(response)

def deleteNetFLoorPlan(netID, floorID):
    """
    Deletes a network floor plan
    
    :usage: deleteNetFloorPlan(string of network ID, string of floor ID)
    :param netID: ID of the network
    :param floorID: ID of the floor plan
    :returns: N/A
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initialized 
                                                                   
    """
    try:
        response = DASHBOARD.networks.deleteNetworkFloorPlan(netID, floorID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:   
        print('Error: %s' % e)
        return(None)
    print(response)

def createNetGroupPolicy(netID, name, scheduling=None, bandwidth=None, firewallAndTrafficShaping=None, contentFilter=None, splashSettings=None, vlan=None, bonjourForwarding=None):
    """
    Creates a network group policy

    :usage createNetGroupPolicy(string of network ID, string of name, dictionary of scheduling, dictionary of bandwidth, dictionary of firewall and traffic shaping, dictionary of content filtering, string of splash authentication setttings, dictionary of vlan tagging, dictionary of bounjour forwarding)
    :param netID: ID of the network
    :param name: Name of the group policy to be created
    :param scheduling: Dictionary containing whether or not it's enabled and the days which are each dictionaries of active, from, and to time
    :param bandwidth: Dictionary containing settings and limits
    :param firewallAndTrafficShaping: Dictionary containing settings and dictionary of rules
    :param contentFilter: Dictionary containing allowed and blocked url patterns/categories
    :param splashSettings: String of splash authentication settings
    :param vlan: Dictionary containing vlan tagging settings and vlanID
    :param bonjourForwading: Dictionary containing settings and dictionary of rules
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.createNetworkGroupPolicy(netID, name, scheduling=scheduling, bandwidth=bandwidth, firewallAndTrafficShaping=firewallAndTrafficSHaping, contentFiltering=contentFilter, splashAuthSettings=splashSettings, vlanTagging=vlan, bonjourForwarding=bonjourForwarding)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getNetPolicy(netID, policyID):
    """ 
    Obtains a group policy for a network
    
    :usage: getNetPolicy(string of network ID, string of policy ID) -> json of the polciy
    :param netID: ID of the network
    :param policyID: ID of the group policy requested
    :returns: json of the group policy
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized 
             400 bad request if group policy ID isn't an integer within a string
             Error no group policy if group policy ID doesn't exist

    """
    try:
        response = DASHBOARD.networks.getNetworkGroupPolicy(netID, policyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)


def updateNetPolicy(netID, policyID, name, scheduling, bandwidth, firewallAndTrafficShaping, contentFilter, splashSettings, vlan, bonjourForwarding):
    """
    Updates a network group policy

    :usage createNetGroupPolicy(string of network ID, string of group policy ID, string of name, dictionary of scheduling, dictionary of bandwidth, dictionary of firewall and traffic shaping, dictionary of content filtering, string of splash authentication setttings, dictionary of vlan tagging, dictionary of bounjour forwarding)
    :param netID: ID of the network
    :param policyID: ID of the group policy you wish to change
    :param name: Name of the group policy
    :param scheduling: Dictionary containing whether or not it's enabled and the days which are each dictionaries of active, from, and to time
    :param bandwidth: Dictionary containing settings and limits
    :param firewallAndTrafficShaping: Dictionary containing settings and dictionary of rules
    :param contentFilter: Dictionary containing allowed and blocked url patterns/categories
    :param splashSettings: String of splash authentication settings
    :param vlan: Dictionary containing vlan tagging settings and vlanID
    :param bonjourForwading: Dictionary containing settings and dictionary of rules
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.createNetworkGroupPolicy(netID, policyID, name, scheduling=scheduling, bandwidth=bandwidth, firewallAndTrafficShaping=firewallAndTrafficSHaping, contentFiltering=contentFilter, splashAuthSettings=splashSettings, vlanTagging=vlan, bonjourForwarding=bonjourForwarding)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def deleteNetPolicy(netID, policyID):
    """
    Deletes a network group policy
    
    :usage: deleteNetPolicy(string of network ID, string of policy ID)
    :param netID: ID of the network
    :param policyID: ID of the group policy you wish to delete
    :returns: N/A
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.deleteNetworkGroupPolicy(netID, policyID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)


def getUsers(netID):
    """
    Obtains all the authenticated users for a network
    
    :usage: getUsers(string of network ID) -> list of user objects
    :param netID: ID of the network
    :returns: List of user objects containing user ID, email, name, account type, and authorizations
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.getNetworkMerakiAuthUsers(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    userList = []
    i = 0
    for user in response:
        userList.append(c_User())
        userList[i].ID = user['id']
        userList[i].email = user['email']
        userList[i].name = user['name']
        userList[i].createdAt = user['createdAt']
        userList[i].userType = user['accountType']
        userList[i].authorizations = user['authorizations']
        i += 1
    return(userList)

def createUser(netID, email, name, password, emailPassword, authorizations, userType='802.1X'):
    """
    Creates a new authenticated user for the network
    
    :usage: createUser(string of network ID, string of email, string of name, string of password, string of user, boolean of emailPassword, list of authorizations)
    :param netID: String of network ID
    :param email: String of user's email
    :param name: String of user's name
    :param password: String of password. Might want to randomly generate within function instead?
    :param emailPassword: Boolean on whether or not password should be sent to the user's email
    :param authorizations: List of user's authorizations, each of which is a dictionary containing the ssid number and expiration date
    :param userType: Optional string of account type. Defaults to 802.1X
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.createNetworkMerakiAuthUser(netID, email, name, password, userType, emailPassword, authorizations)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getUser(netID, userID):
    """
    Obtains the information of a user for a network

    :usage: getUsers(string of network ID, string of user ID) -> User object    
    :param netID: ID of the network
    :param userID: ID of the user
    :returns: User object containing user ID, email, name, account type, and authorizations                                                                                   
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.getNetworkMerakiAuthUser(netID, userID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    user = c_User()
    user.ID = response['id']
    user.email = response['email']
    user.name = response['name']
    user.createdAt = response['createdAt']
    user.userType = response['accountType']
    user.authorizations = response['authorizations']
    return(user)

def updateUser(netID, userID, name=None, password=None, authorizations=None):
    """
    Updates information of a user for a network
    
    :usage: updateUser(string of network ID, string of user ID, string of name, string of password, list of authorizations)
    :param netID: ID of the network
    :param userID: ID of the the user 
    :param name: New name for user
    :param password: New password for user
    :authorizations: List of user's authorizations, each of which is a dictionary containing ssid number and expiration date
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized 
                             
    """
    try:
        response = DASHBOARD.networks.updateNetworkMerakiAuthUser(netID, userID, name, password, authorizations)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)


def deleteUser(netID, userID):
    """
    Deletes a user from a network

    :usage: deleteUser(string of network ID, string of user ID) 
    :param netID: ID of the network
    :param userID: ID of the user
    :returns: N/A
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.getNetworkMerakiAuthUser(netID, userID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getNetMQTTbrokers(netID):
    """ 
    Obtains MQTT brokers for a network
    
    :usage: getNetMQTTbrokers(string of network ID) -> list of MQTT broker objects 
    :param netID: ID of the network
    :returns: list of MQTT broker objects containing ID, name, host, port, authentication, and security
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             Bad request if not used on a camera or MT network                
    """
    # Every network is either an error of returns an empty list. not worth processing the json into classes yet because of this
    try:
        response = DASHBOARD.networks.getNetworkMqttBrokers(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getNetMQTTbroker(netID, brokerID):
    """
    Obtains the information of a MQTT broker for a network
    :usage: getNetMQTTbrokers(string of network ID) -> MQTT broker object
    :param netID: ID of the network
    :param brokerID: ID of the broker
    :returns: MQTT broker object containing ID, name, host, port, authentication, and security 
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
             Bad request if not used on a camera or MT network

    """
    # Every network is either an error of returns an empty list, so not processing json yet                      
    try:
        response = DASHBOARD.networks.getNetworkMqttBroker(netID, brokerID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def createNetMQTTbroker(netID):
    """
    not necessary yet
    """
    #response = DASHBOARD.networks.createNetworkMqttBroker(netID, name, host, port, security={}, authentication={})
                                        
def updateNetMQTTbroker(netID):
    """
    not necessary yet 
    """
    #response = DASHBOARD.networks.updateMqttBroker(netID, brokerID, name, host, port, security={}, authentication={})

def deleteNetMQTTbroker(netID, brokerID):
    """
    Deletes a MQTT broker on a network (none exist yet to my knowledge)

    :usage: getNetMQTTbrokers(string of network ID) 
    :param netID: ID of the network
    :param brokerID: ID of the broker
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.getNetworkMqttBroker(netID, brokerID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def updateNetflow(netID, reporting, ip, port, eta, etaPort):
    """
    Updates the netflow settings for a network
    
    :usage: updateNetflow(string of network ID, boolean of reporting, string of ip, int of port, boolean of eta, int of etaPort)
    :param netID: ID of the network
    :param reporting: Boolean for whether or not reporting is enabled
    :param ip: String of collector IP
    :param port: int of collector port
    :param eta: Boolean for whether or not encrypted traffic analytics is enabled
    :param etaPort: int of encrypted traffic analytics port
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.updateNetflow(netID, reportingEnabled=reporting, collectorIp=ip, collectorPort=port, etaEnabled=eta, estDstPort=etaPort)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getPIIkeys(ID, level):
    """
    Obtains the keys to access personally identifiable information for an organization or network. Kind of confused and have not tested this in fear that it's information I shouldn't look at.
    
    :usage: getPIIkeys(string of organization or network ID, string of level) -> json of PII keys
    :param ID: ID of the organization or network
    :param level: Either 'org' or 'net' to convey that you want organization or network keys
    :returns: Printed out json of the keys
    :raises: API error if API key is faulty             
             Error on str object if dashboard key isn't initialized
    
    """
    # Should contain the macs, emails, usernames, serials, imeis(?), and bluetoothMacs in each PII, with each being a key to a list within the PII's dictionary
    if level == 'org':
        try:
            # this might need to be a get request instead
            response = DASHBOARD.organizations.getPiiPiiKeys(ID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        print(response)
    elif level == 'net':
        try:
            response = DASHBOARD.networks.getNetworkPiiPiiKeys(ID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        print(response)
    else:
        print('level must be either org or net')
        return(None)

def getPIIrequests(ID, level):
    """
    Obtains the personally identifiable information requests for an organization or a network
    
    :usage: getPIIrequests(string of organization or network ID, string of level) -> json of PII requests
    :param ID: ID of the organization or network
    :param level: Either 'org' or 'net'
    :returns: Printed out json of the requests
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized    

    """
    # Should contain the id, whether or not it's organization wide, network id, type, mac, datasets(?), status, createed At, and completed At
    if level == 'org':
        try:
            # this might need to be a get request instead
            response = DASHBOARD.organizations.getPiirequests(ID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        return(response)
    elif level == 'net':
        try:
            response = DASHBOARD.networks.getNetworkPiiRequests(ID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        return(response)
    else:
        print('level must be either org or net')
        return(None)

def getPIIrequest(ID, level, requestID):
    """ 
    Obtains a personally identifiable information request for an organization or a network

    :usage: getPIIrequest(string of organization or network ID, string of level, string of request ID) -> json of PII request 
    :param ID: ID of the organization or network
    :param level: Either 'org' or 'net'
    :param requestID: ID of the request
    :returns: Printed out json of the request
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized 

    """
    # Should contain the id, whether or not it's organization wide, network id, type, mac, datasets(?), status, createed At, and completed At 
    if level == 'org':
        try:
            # this might need to be a get request instead 
            response = DASHBOARD.organizations.getPiirequest(ID, requestID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        return(response)
    elif level == 'net':
        try:
            response = DASHBOARD.networks.getNetworkPiiRequest(ID, requestID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        return(response)
    else:
        print('level must be either org or net')
        return(None)


def createPIIrequest(ID, level, requestType, datasets, mac, smDevID=None, smUserID=None):
    """
     Obtains the personally identifiable information requests for an organization or a network

    :usage: createPIIrequests(string of organization or network ID, string of level, string of requestType, list of datasets, string of mac, string of smDevID, string of smUserID) 
    :param ID: ID of the organization or network
    :param level: Either 'org' or 'net'
    :param requestType: Either delete or restrict processing
    :param datasets: List of the datasets that should be deleted. Only applicable to delete
    :param mac: MAC of the device
    :param smUserID: ID of systems manager user
    :param smsDevID: ID of a systems manager device
    :returns: N/A
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initialized
    
    """
    # request type can either be delete or restrict processing
    # can also include username to log in if it's a delete request
    if level == 'org':
        try:
            # this might need to be a get request instead
            response = DASHBOARD.organizations.createPiiRequest(ID, level, type=requestType, datasets=datasets, mac=mac)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        print(response)
    elif level == 'net':
        try:
            response = DASHBOARD.networks.createNetworkPiiRequest(ID, type=requestType, datasets=datasets, mac=mac)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        print(response)
    else:
        print('level must be either org or net')
        return(None)

def deletePIIrequest(ID, level, requestID):
    """
    Deletes a personally identifiable information request
    
    :usage: deletePIIrequest(string of organization or network ID, string of level, string of request ID) 
    :param ID: ID of the organization or network
    :param level: Either 'org' or 'net'
    :param requestID: ID of the request
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized 
    
    """
    if level == 'org':
        try:
            # this might need to be a get request instead          
            response = DASHBOARD.organizations.deletePiirequest(ID, requestID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        print(response)
    elif level == 'net':
        try:
            response = DASHBOARD.networks.deleteNetworkPiiRequest(ID, requestID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        print(response)
    else:
        print('level must be either org or net')
        return(None)

def getSMdevices(ID, level):
    """
    Obtains the systems manager device ID associated with a personally identifiable information (Idk) 
    
    :usage: getSMdevices(string of organization or network ID, string of level) -> List of SM device IDs
    :param ID: ID of the organization or network
    :param level: Either 'org' or 'net'
    :param requestID: ID of the request
    :returns: List of SM device IDs
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
                      
    """
    if level == 'org':
        try:
            # this might need to be a get request instead 
            response = DASHBOARD.organizations.getPiiSmDevicesForKey(ID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        return(response)
    elif level == 'net':
        try:
            response = DASHBOARD.networks.getNetworkPiiSmDevicesForKey(ID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        return(response)
    else:
        print('level must be either org or net')
        return(None)

def getSMusers(ID, level):
    """
    Obtains the systems manager owner IDs associated with a personally identifiable information
    
    :usage: getSMusers(string of organization or network ID, string of level) -> List
of SM owner IDs
    :param ID: ID of the organization or network
    :param level: Either 'org' or 'net'
    :param requestID: ID of the request
    :returns: List of SM owner IDs
    :raises: API error if API key is faulty 
             Error on str object if dashboard key isn't initialized
                      
    """
    if level == 'org':
        try:
            # this might need to be a get request instead 
            response = DASHBOARD.organizations.getPiiSmOwnersForKey(ID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        return(response)
    elif level == 'net':
        try:
            response = DASHBOARD.networks.getNetworkPiiSmOwnersForKey(ID)
        except meraki.APIError as e:
            print('Error: %s' % e.message)
            return(None)
        except Exception as e:
            print('Error: %s' % e)
            return(None)
        return(response)
    else:
        print('level must be either org or net')
        return(None)

def getNetSettings(netID):
    """
    Obtains the settings for a network
    
    :usage: getNetSettings(string of network ID) -> Dictionary of the settings
    :param netID: ID of the network
    :returns: Dictionary/ JSON format of settings
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized 
    
    """
    
    try:
        response = DASHBOARD.networks.getNetworkSettings(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    return(response)

def updateNetSettings(netID, remoteStatPageEnabled=None, localStatPageEnabled=None, localStatPage=None, secureConnect=None, fips=None, namedVlans=None):
    """
    Updates network settings
    
    :usage: updateNetSettings(string of netID, boolean of localStatPage, boolean of remoteStat+
    :param netID: ID of the network
    :param remoteStatPageEnabled: Boolean for whether or not remote status page is enabled
    :param localStatPageEnabled: Boolean for whether or not local status page is enabled
    :param localStatPage: Dictionary of page options 
    :param secureConnect: Dictionary of secure connect options, such as whether or not it's enabled
    :param fips: Dictionary of whether or not fips is enabled
    :param namedVlans: Dictionary of whether or not named VLANS are enabled
    :returns: N/A
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.updateNetworkSettings(netID, remoteStatusPageEnabled=remoteStatPageEnabled, localStatusPageEnabled=localStatPageEnabled, localStatusPage=localStatPage, secureConnect=secureConnect, fips=fips, namedVlans=namedVlans)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def splitNet(netID):
    """
    Splits a combined network into a network for each device type such as switch, wireless, appliance, etc
    
    :usage: splitNet(string of network ID) -> list[network objects]
    :param netID: ID of the network
    :returns: List of network objects that the combined network has been split into
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = dashboard.networks.splitNetwork(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    netList = []
    i = 0
    for net in response:
        netList.append(c_Net())
        netList[i].name = net['name']
        netList[i].ID = net['id']
        netList[i].orgID = net['organizationId']
        netList[i].timezone = net['timeZone']
        netList[i].tags = net['tags']
        netList[i].productTypes = net['productTypes']
        netList[i].enrollmentString = net['enrollmentString']
        i += 1
    return(netList)

def getNetSyslogServers(netID):
    """
    Obtains the syslog servers for a network

    :usage: getNetSyslogServers(string of network ID) -> list[syslog objects]
    :param netID: ID of the network
    :returns: List of syslog objects each containing a host, port, and a list of roles
    :raises: API error if API key is faulty
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.getNetworkSyslogServers(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    serverList = []
    i = 0
    if response['servers'] != None:
        for server in response:
            serverList.append(c_Syslog())
            serverList[i].host = server['host']
            serverList[i].port = server['port']
            serverList[i].roles = server['roles']
            i += 1
        return serverList
    else:
        return(None)
    
def updateSyslogServers(netID, servers):
    """
    Updates the syslog servers for a given network
    
    :usage: updateSyslogServers(string of network ID, list of servers)
    :param netID: ID of the network
    :param server: List of syslog servers that each contain host, port, and a list of roles. needs to be in the format of a dictionary, but i return objects. maybe i should accept objects so the user doesn't need to process?
    :returns: N/A
    :raises: API error if key is bad
             Error on str object if dashboard key isn't initialized

    """
    # roles can be Wireless event log, Appliance event log, Switch event log, Air Marshal events, Flows, URLs, IDS alerts, or Securty events
    
    try:
        response = DASHBOARD.networks.updateNetworkSyslogServers(netID, servers)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)


def unbindNet(netID):
    """
    Unbinds a network from a template
    
    :usage: unbindNet(string of network ID) -> Status code
    :param netID: ID of the network
    :returns: Status code? need to test
    :raises: API error if key is bad
             Error on str object if dashboard key isn't initialized

    """
    try:
        response = DASHBOARD.networks.upnbindNetwork(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getNetBluetoothClients(netID):
    """
    Obtains bluetooth clients for a network
    
    :usage: getNetBluetoothClients(string of network ID) -> List of bluetooth client objects
    :param netID: ID of the network
    :returns: List of bluetooth client objects
    :raises: API error if key is bad
             Error on str object if dashboard key isn't initialized

    """
    # each client has id, mac, netID, name, device name, manufacturer, lastSeen, seenByDeviceMac, inSightAlert, outOfSightAlert, and tags. only a few are configured for the objects as of rn
    try:
        response = DASHBOARD.networks.getNetworkBluetoothClients(netID, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    clientList = []
    i = 0
    if response != None:
        for client in response:
            clientList.append(c_Bluetooth_Client)
            clientList[i].ID = client['id']
            clientList[i].name = client['deviceName'] # can also do name
            clientList[i].mac = client['mac']
            clientList[i].tags = client['tags']
            i += 1
    return(clientList)

def getNetBluetoothClient(netID, clientID):
    """           
    Obtains the information for a specific blueooth client on a network

    :usage: getNetBluetoothClients(string of network ID, string of client ID) -> client object
    :param netID: ID of the network
    :param clientID: ID of the bluetooth client
    :returns: Client object
    :raises: API error if key is bad
             Error on str object if dashboard key isn't initialized      
             
    """
    try:
        response = DASHBOARD.networks.getNetworkBluetoothClient(netID, clientID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    client = c_Bluetooth_Client()
    client.ID = response['id']
    client.name = response['deviceName'] # can also do name                 
    client.mac = response['mac']
    client.tags = response['tags']
    return(client) 

def getNetChannelUtil(netID):
    """
    Obtains the radio channel utilization for a network
    
    :usage: getNetChannelUtil(string of network ID) ->
    :param netID: ID of the network
    :returns:
    :raises: API error if key is bad
             Error on str object if dashboard key isn't initialized
       
    """
    # has device serial and model, tags, and then each wifi with a list of start/stop time, utilization total, 80211, and non80211
    try:
        response = DASHBOARD.networks.getNetworkNetworkHealthChannelUtilization(netID, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)
    
def getNetSplashLoginAttempts(netID):
    """ 
    Obtains the log in attempts for a network
    
    :usage: getNetSplashLoginAttempts(string of network ID) -> list of clients
    :param netID: ID of the network
    :returns: List of clients with name, login, ssid, time, gateway device mac, client mac and ID, and authorization status
    :raises: API error if key is bad
             Error on str object if dashboard key isn't initialized
    
    """
    try:
        response = DASHBOARD.networks.getNetworkNetworkSplashLoginAttempts(netID)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    return(response)

def getSwitchRoutingInterface(devSerial):
    """
    Seems to just return empty for each switch
    """
    try:
        response = DASHBOARD.switch.getDeviceSwitchRoutingInterfaces(devSerial)
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    print(response)

def getApplianceUplinkStatuses(orgID):
    try:
        response = DASHBOARD.appliance.getOrganizationApplianceUplinkStatuses(orgID, total_pages='all')
    except meraki.APIError as e:
        print('Error: %s' % e.message)
        return(None)
    except Exception as e:
        print('Error: %s' % e)
        return(None)
    for r in response:
        print(r)
