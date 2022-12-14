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
import readchar
from sortedcontainers import SortedSet

def getDefinedConfigurationFromFile(filename):

    with open(filename, "r") as fp:
        config = json.load(fp)

    if "Response" in config.keys():
        config = config["Response"]

    return config

def buildZoneMemberCounts(config):
    zoneMemberCount = {}

    for i in config["defined-configuration"]["zone"]:
        print(i)

        if i["zone-type"] == 0:
            zoneMemberCount[i["zone-name"]] = { "principalCount": 0, "nonPrincipalCount": 0 }
            zoneMemberCount[i["zone-name"]]["memberCount"] = len(i["member-entry"]["entry-name"])
        if i["zone-type"] == 1:
            zoneMemberCount[i["zone-name"]] = {"memberCount": 0 }
            zoneMemberCount[i["zone-name"]]["principalCount"] = len(i["member-entry"]["principal-entry-name"])
            zoneMemberCount[i["zone-name"]]["nonPrincipalCount"] = len(i["member-entry"]["entry-name"])

        zoneMemberCount[i["zone-name"]]["zone-type"] = i["zone-type"]
    return zoneMemberCount

def main():

    if (len(sys.argv) <2):
        print("usage: {} <configFileName>".format(sys.argv[0]))
        sys.exit(2)

    config = getDefinedConfigurationFromFile("foo.json")

    zoneMemberCount = buildZoneMemberCounts(config)
    for i in zoneMemberCount.keys():
        print("{}: {}".format(i,zoneMemberCount[i]))

if __name__ == "__main__":
    # main(sys.argv)
    main()