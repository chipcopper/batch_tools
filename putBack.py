#!/usr/bin/env python3
# Version 23.1.2.1
# Copyright 2022 Chip Copper

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
# to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import json
import base64
import requests
import argparse
from decouple import config



def restLogin(username, password, switchAddress, prefix):
    credentials = base64.b64encode(bytearray(username + ":" + password, 'utf-8')).decode()

    # Suppress warnings for self-signed certificates
    requests.packages.urllib3.disable_warnings()

    # Set the base for all REST calls
    url_base = prefix + "://" + switchAddress + "/rest/"
    session = requests.session()

    # No payload
    payload = {}
    files = {}

    # Send the login and print the return status code
    headers = {
        'Authorization': 'Basic ' + credentials
    }
    response = session.request("POST", url_base + "login", headers=headers, data=payload, files=files, verify=False)
    if response.status_code != 200:
        print("Error logging in: {}".format(response.status_code))
        exit()

    with open("sessKey.txt", "w") as fp:
        fp.write(response.headers["Authorization"])

    return session, response.headers["Authorization"]


def restLogout(session, sessionKey, switchAddress, prefix):
    url_base = prefix + "://" + switchAddress + "/rest/"
    # No payload
    payload = {}
    files = {}

    session_headers = {
        'Authorization': sessionKey,
        'Accept': 'application/yang-data+json',
        'Content-Type': 'application/yang-data+json'
    }

    # Send the logout and print the return status code
    response = session.request("POST", url_base + "logout", headers=session_headers, data=payload, verify=False)
    if response.status_code != 204:
        print("Error logging out: {}".format(response.status_code))


def getConfigurationFromFile(filename):
    with open(filename, "r") as fp:
        cfg = json.load(fp)

    if "Response" in cfg.keys():
        cfg = cfg["Response"]

    return cfg


def saveConfiguration(session, sessionKey, prefix, switchAddress, checksum):
    payload = {
        "checksum": checksum
    }

    print(f'payload: {payload}')

    url_base = prefix + "://" + switchAddress + "/rest/"
    files = {}
    session_headers = {
        'Authorization': sessionKey,
        'Accept': 'application/yang-data+json',
        'Content-Type': 'application/yang-data+json'
    }

    # Update the zone
    response = session.request("PATCH",
                               url_base + "running/brocade-zone/effective-configuration/cfg-action/1",
                               headers=session_headers, json=payload, files=files, verify=False)
    if response.status_code >= 300:
        errorDict = json.loads(response.text)
        print("Error saving configuration: {}".format(errorDict['errors']['error'][0]['error-message']))

    return response.status_code


def getEffectiveConfiguration(session, sessionKey, prefix, switchAddress):
    url_base = prefix + "://" + switchAddress + "/rest/"
    # No payload
    payload = {}
    files = {}

    session_headers = {
        'Authorization': sessionKey,
        'Accept': 'application/yang-data+json',
        'Content-Type': 'application/yang-data+json'
    }

    # Get the effective configuration
    response = session.request("GET", url_base + "running/brocade-zone/effective-configuration",
                               headers=session_headers, data=payload, files=files, verify=False)
    if response.status_code != 200:
        print("Error getting effective configuration in: {}".format(response.status_code))
        print(response.text)
    else:
        json_response = json.loads(response.text)

    return json_response["Response"]


def deleteZoneObject(session, sessionKey, prefix, switchAddress, uri):
    url_base = prefix + "://" + switchAddress + "/rest/"
    # No payload
    payload = {}
    files = {}

    session_headers = {
        'Authorization': sessionKey,
        'Accept': 'application/yang-data+json',
        'Content-Type': 'application/yang-data+json'
    }

    # Get the effective configuration
    response = session.request("DELETE",
                               url_base + "running/brocade-zone/defined-configuration/" + uri,
                               headers=session_headers, data=payload, files=files, verify=False)
    if response.status_code != 204 and response.status_code != 400:
        errorDict = json.loads(response.text)
        print("Error deleting object: {}".format(errorDict['errors']['error'][0]['error-message']))

    return response.status_code


def createZoneObject(session, sessionKey, prefix, switchAddress, uri, payload):
    url_base = prefix + "://" + switchAddress + "/rest/"
    files = {}

    session_headers = {
        'Authorization': sessionKey,
        'Accept': 'application/yang-data+json',
        'Content-Type': 'application/yang-data+json'
    }

    # Get the effective configuration
    response = session.request("POST",
                               url_base + "running/brocade-zone/defined-configuration/" + uri,
                               headers=session_headers, json=payload, files=files, verify=False)
    if response.status_code != 201:
        errorDict = json.loads(response.text)
        print("Error creating object: {}".format(errorDict['errors']['error'][0]['error-message']))

    return response.status_code


def saveConfiguration(session, sessionKey, prefix, switchAddress, checksum):
    payload = {
        "checksum": checksum
    }

    url_base = prefix + "://" + switchAddress + "/rest/"
    files = {}
    session_headers = {
        'Authorization': sessionKey,
        'Accept': 'application/yang-data+json',
        'Content-Type': 'application/yang-data+json'
    }

    # Update the zone
    response = session.request("PATCH",
                               url_base + "running/brocade-zone/effective-configuration/cfg-action/1",
                               headers=session_headers, json=payload, files=files, verify=False)
    if response.status_code >= 300:
        errorDict = json.loads(response.text)
        print("Error saving configuration: {}".format(errorDict['errors']['error'][0]['error-message']))

    return response.status_code


def main(sysArgv):
    fabricIP = config('FABRICIP')
    fabricUser = config('FABRICUSER')
    fabricPassword = config('FABRICPASSWORD')
    fabricPrefix = config('FABRICPREFIX')

    parser = argparse.ArgumentParser()

    parser.add_argument("-z", "--zoneobj", default=False, help="Zoning object to put back", \
                        required=True)
    parser.add_argument("-d", "--defconfig", default=False, help="Previously saved defined configuration", \
                        required=True)
    args = parser.parse_args()

    target = args.zoneobj
    defConf = args.defconfig

    definedConfiguration = getConfigurationFromFile(defConf)

    aliasesArray = definedConfiguration['defined-configuration']['alias']
    zoneArray = definedConfiguration['defined-configuration']['zone']
    cfgArray = definedConfiguration['defined-configuration']['cfg']

    aliasDict = {}
    for i in aliasesArray:
        aliasDict[i['alias-name']] = {}
        aliasDict[i['alias-name']]['member-entry'] = i['member-entry']

    zoneDict = {}
    for i in zoneArray:
        zoneDict[i['zone-name']] = {}
        zoneDict[i['zone-name']]['member-entry'] = i['member-entry']
        zoneDict[i['zone-name']]['zone-type'] = i['zone-type']

    cfgDict = {}
    for i in cfgArray:
        cfgDict[i['cfg-name']] = {}
        cfgDict[i['cfg-name']]['member-zone'] = i['member-zone']

    # Find the target and set up the URI and payload
    if target in aliasDict.keys():
        # Restore alias
        uri = f'alias/alias-name/{target}'
        payload = aliasDict[target]
    elif target in zoneDict.keys():
        # Restore zone
        uri = f'zone/zone-name/{target}'
        payload = zoneDict[target]
    elif target in cfgDict.keys():
        # Restore cfg
        uri = f'cfg/cfg-name/{target}'
        payload = cfgDict[target]
    else:
        print(f'Object {target} not found in stored defined configuation.')
        exit(3)

    # Log into the fabric
    session, sessionKey = restLogin(fabricUser, fabricPassword, fabricIP, fabricPrefix)

    # Get the effective configuration
    effConf = getEffectiveConfiguration(session, sessionKey, fabricPrefix, fabricIP)

    # if the object exists, delete it
    result = deleteZoneObject(session, sessionKey, fabricPrefix, fabricIP, uri)

    # Add the object
    result = createZoneObject(session, sessionKey, fabricPrefix, fabricIP, uri, payload)

    # Save the changes

    saveConfiguration(session, sessionKey, fabricPrefix, fabricIP, effConf["effective-configuration"]["checksum"])
    print(f'{target} has been added back to the defined configuration.')
    # logout of the fabric
    restLogout(session, sessionKey, fabricIP, fabricPrefix)

    pass


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main(sys.argv)
