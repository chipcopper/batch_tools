#!/usr/bin/env python3
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

switchAddress = None
username = None
password = None
outfileName = None
prefix = "https"
verbose = False


# Retrieve and parse command line arguments.
try:
    opts, args = getopt.getopt(sys.argv[1:],"u:p:i:ho:v",
        ["username=", "password=", "address=", "insecure", "outfile"])
except getopt.GetoptError:
    print("usage: {} -u <username> -p <password> -i <ipaddress> -o <outfile> [--insecure]".format(sys.argv[0]))
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print("usage: {} -u <username> -p <password> -i <ipaddress> -o <outfile> [--insecure]".format(sys.argv[0]))
        sys.exit()
    elif opt in ("-u", "--username"):
        username = arg
    elif opt in ("-p", "--password"):
        password = arg
    elif opt in ("-i","--ipaddress"):
        switchAddress = arg
    elif opt in ("-o", "--outfile"):
        outfileName = arg
    elif opt in ("--insecure"):
        prefix = "http"
    elif opt in ("-v"):
        verbose = True


if (username is None or password is None or switchAddress is None or outfileName is None):
    print("usage: {} -u <username> -p <password> -i <ipaddress> -o <outfile> [--insecure]".format(sys.argv[0]))
    sys.exit(2)

try:
    outfileFD = open(outfileName, "w")
except:
    print("Could not open outfile {}".format(outfileName))
    sys.exit(3)



# Base64 encode the username and password
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

session_headers = {
  'Authorization': response.headers["Authorization"],
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
    # print(json.dumps(json_response["Response"]))

# Send the logout and print the return status code
response = session.request("POST", url_base + "logout", headers=session_headers, data=payload,verify=False)
if response.status_code != 204:
    print("Error logging out: {}".format(response.status_code))
if verbose:
    print("Current effective configuration retrieved.")

json.dump(json_response["Response"], outfileFD)

outfileFD.close()


