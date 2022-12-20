#!/usr/bin/env python3
# Version 22.12.20.1
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

import requests
import base64
import json
import sys
import getopt
import readchar
from sortedcontainers import SortedSet, SortedList
import re
import time



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
    response = session.request("POST", url_base + "login", headers=headers, data=payload, files=files,verify=False)
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
    response = session.request("POST", url_base + "logout", headers=session_headers, data=payload,verify=False)
    if response.status_code != 204:
        print("Error logging out: {}".format(response.status_code))

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
                                headers=session_headers, data=payload, files=files,verify=False)
    if response.status_code != 200:
        print("Error getting defined configuration in: {}".format(response.status_code))
        print(response.text)
    else:
        json_response = json.loads(response.text)

    return json_response["Response"]

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
                                headers=session_headers, data=payload, files=files,verify=False)
    if response.status_code != 200:
        print("Error getting effective configuration in: {}".format(response.status_code))
        print(response.text)
    else:
        json_response = json.loads(response.text)

    return json_response["Response"]

def buildAliasToWwn(config):

    aliasTable = {}

    aliases = config['defined-configuration']['alias']

    for i in aliases:
        aliasTable[i['alias-name']] = i['member-entry']['alias-entry-name']

    return aliasTable

def flipAliastoWWN(aliasTable):
    wwnTable = {}
    for i in aliasTable.keys():
        for j in aliasTable[i]:
            if j not in wwnTable.keys():
                wwnTable[j] = list()
            wwnTable[j].append(i)
    return wwnTable

def getSetFromFile(filename):
    with open(filename, "r") as fp:
        fileLines = fp.readlines()

    fileSet = set()
    for i in fileLines:
        entry = i.strip()
        if len(entry) > 0:
            fileSet.add(entry)

    return fileSet

def deleteAlias(session, sessionKey, prefix, switchAddress, alias):

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
    response = session.request("DELETE", url_base + "running/brocade-zone/defined-configuration/alias/alias-name/" + alias,
                                headers=session_headers, data=payload, files=files,verify=False)
    if response.status_code != 204:
        errorDict = json.loads(response.text)
        print("Error deleting zone: {}".format(errorDict['errors']['error'][0]['error-message']))

    return response.status_code

def deleteZone(session, sessionKey, prefix, switchAddress, zone):

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
    response = session.request("DELETE", url_base + "running/brocade-zone/defined-configuration/zone/zone-name/" + zone,
                                headers=session_headers, data=payload, files=files,verify=False)
    if response.status_code != 204:
        errorDict = json.loads(response.text)
        print("Error deleting zone: {}".format(errorDict['errors']['error'][0]['error-message']))

    return response.status_code

def main(argv):
    switchAddress = None
    username = None
    password = None
    zoneDelFile = None
    wwnDelFile = None
    prefix = "https"
    verbose = False

    # Retrieve and parse command line arguments.
    try:
        opts, args = getopt.getopt(argv[1:],"u:p:i:w:z:v",
            ["username=", "password=", "address=", "zonesFile", "wwnsFile"])
    except getopt.GetoptError:
        print("usage: {} -u <username> -p <password> -i <ipaddress> -z <zonesFile> -w <wwnsFile> [--insecure]".format(sys.argv[0]))
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("usage: {} -u <username> -p <password> -i <ipaddress> -z <zonesFile> -w <wwnsFile> [--insecure]".format(sys.argv[0]))
            sys.exit()
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-i","--ipaddress"):
            switchAddress = arg
        elif opt in ("-z","--zonesFile"):
            zoneDelFile = arg
        elif opt in ("-w", "--wwnsFile"):
            wwnDelFile = arg
        elif opt in ("--insecure"):
            prefix = "http"
        elif opt in ("-v"):
            verbose = True

    # Verify all required arguments are present
    if (username is None or password is None or switchAddress is None or zoneDelFile is None or wwnDelFile is None):
        print("usage: {} -u <username> -p <password> -i <ipaddress> -z <zonesFile> -w <wwnsFile> [--insecure]".format(sys.argv[0]))
        sys.exit(2)

    zonesToDelete = getSetFromFile(zoneDelFile)
    wwnsToDelete = getSetFromFile(wwnDelFile)

    # Initiate the session
    session, sessionKey = restLogin(username, password, switchAddress, prefix)
    if verbose:
    	print("Logged in...")

    defined = getDefinedConfiguration(session, sessionKey, prefix, switchAddress)
    if verbose:
    	print("DefinedDB retrieved...")
    effective = getEffectiveConfiguration(session, sessionKey, prefix, switchAddress)
    if verbose:
    	print("EffectiveDB retrieved...")

    aliasTable = buildAliasToWwn(defined)
    wwnLookupTable = flipAliastoWWN(aliasTable)

    for wwn in wwnsToDelete:
        if verbose:
            print("Deleting alias {}...".format(wwnLookupTable[wwn][0]))
        deleteAlias(session, sessionKey, prefix, switchAddress, wwnLookupTable[wwn][0])
        time.sleep(1.1)
    for zone in zonesToDelete:
        if verbose:
            print("Deleting zone  {}...".format(zone))
        deleteZone(session, sessionKey, prefix, switchAddress, zone)
        time.sleep(1.1)

    # Free up the API session
    if verbose:
        print("Logging out...")
    restLogout(session, sessionKey, switchAddress, prefix)
    if verbose:
        print("Dry run complete")


if __name__ == "__main__":
	main(sys.argv)