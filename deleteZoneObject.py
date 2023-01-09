#!/usr/bin/env python3
# Version 23.1.9.1
# Copyright 2023 Chip Copper

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
        exit(3)
    else:
        json_response = json.loads(response.text)

    return json_response["Response"]

def getDefinedConfiguration(session, sessionKey, prefix, switchAddress):
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
    response = session.request("GET", url_base + "running/brocade-zone/defined-configuration",
                               headers=session_headers, data=payload, files=files, verify=False)
    if response.status_code != 200:
        print("Error getting defined configuration in: {}".format(response.status_code))
        print(response.text)
        exit(3)
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

def main(sysArgv):
    fabricIP = config('FABRICIP')
    fabricUser = config('FABRICUSER')
    fabricPassword = config('FABRICPASSWORD')
    fabricPrefix = config('FABRICPREFIX')
    overrideConfirm = config("OVERRIDECONFIRM", cast=bool, default=False)

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--delfile", default=False, help="File containing objects to be deleted",
                        required=True)
    args = parser.parse_args()

    delFile = args.delfile

    with open(delFile, "r") as fd:
        rawFile = fd.readlines()

    delObjects = list()
    for i in rawFile:
        delObjects.append(i.strip())

    print(f"{delObjects}")

    # Log into the fabric
    session, sessionKey = restLogin(fabricUser, fabricPassword, fabricIP, fabricPrefix)

    # Get the effective configuration
    effConf = getEffectiveConfiguration(session, sessionKey, fabricPrefix, fabricIP)
    definedConfiguration = getDefinedConfiguration(session, sessionKey, fabricPrefix, fabricIP)

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

    for target in delObjects:
        if target in aliasDict.keys():
            zoneObject = 'alias'
            uri = f'alias/alias-name/{target}'
            payload = aliasDict[target]
        elif target in zoneDict.keys():
            zoneObject = 'zone'
            uri = f'zone/zone-name/{target}'
            payload = zoneDict[target]
        elif target in cfgDict.keys():
            zoneObject = 'cfg'
            uri = f'cfg/cfg-name/{target}'
            payload = cfgDict[target]
        else:
            print(f'Object {target} not found in defined configuration.')
            continue

        # if the object exists, delete it
        result = deleteZoneObject(session, sessionKey, fabricPrefix, fabricIP, uri)
        print(f'{zoneObject} {target} has been deleted from the defined configuration.')
    if overrideConfirm:
        checksum = effConf["effective-configuration"]["checksum"]
        saveConfiguration(session, sessionKey, fabricPrefix, fabricIP, checksum)
        print(f'Configuration saved.')
    else:
        commitConf = input(f'Save changes? Y or y to accept, anything else to reject: ')
        if len(commitConf) == 1 and commitConf in "Yy":
            checksum = effConf["effective-configuration"]["checksum"]
            saveConfiguration(session, sessionKey, fabricPrefix, fabricIP, checksum)
            print(f'Configuration saved.')
        else:
            print(f'Changes discarded.')
        print('Done!')
    # logout of the fabric
    restLogout(session, sessionKey, fabricIP, fabricPrefix)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main(sys.argv)
