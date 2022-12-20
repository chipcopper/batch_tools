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

import json
import sys
import getopt
from sortedcontainers import SortedSet, SortedList
import re

def getConfigurationFromFile(filename):

    with open(filename, "r") as fp:
        config = json.load(fp)

    if "Response" in config.keys():
        config = config["Response"]

    return config

def getSetFromFile(filename):
    with open(filename, "r") as fp:
        fileLines = fp.readlines()

    fileSet = set()
    for i in fileLines:
        fileSet.add(i.strip())

    return fileSet

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

def getZonesAndWWPNsFromEffectiveConfig(config):
    enabledZone = config['effective-configuration']['enabled-zone']

    zoneNames = set()
    wwns = set()

    for i in enabledZone:
        zoneName = i['zone-name']
        zoneNames.add(zoneName)
        if 'entry-name' in i['member-entry'].keys():
            for j in i['member-entry']['entry-name']:
                wwns.add(j)
        if 'principal-entry-name' in i['member-entry'].keys():
            for j in i['member-entry']['principal-entry-name']:
                wwns.add(j)

    return zoneNames, wwns

def getZonesAndMembersFromDefinedConfig(config):
    zoneList = config['defined-configuration']['zone']

    zoneNames = set()
    members = set()

    for i in zoneList:
        zoneName = i['zone-name']
        zoneNames.add(zoneName)
        #print(i['member-entry'].keys())
        if 'entry-name' in i['member-entry'].keys():
            for j in i['member-entry']['entry-name']:
                members.add(j)
        if 'principal-entry-name' in i['member-entry'].keys():
            for j in i['member-entry']['principal-entry-name']:
                members.add(j)

    return zoneNames, members

def getAliasesFromWwns(wwnLookupTable, wwnList):
    aliasList = SortedSet()
    for i in wwnList:
        if i in wwnLookupTable.keys():
            for j in wwnLookupTable[i]:
                aliasList.add(j)
                
    return aliasList

def main(argv):

    effCfgFile = None
    defCfgFile = None
    zoneDelFile = None
    wwnDelFile = None

    # Retrieve and parse command line arguments.
    try:
        opts, args = getopt.getopt(argv[1:],"e:d:w:z:",
            ["effectiveDB=", "definedDB=", "zoneFile=", "wwnFile="])
    except getopt.GetoptError:
        print("usage: {} -e <effectiveDBFile> -d <definedDBFile> -z <zonesFile> -w <wwnsFile>".format(argv[0]))
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("usage: {} -e <effectiveDBFile> -d <definedDBFile> -z <zonesFile> -w <wwnsFile>".format(argv[0]))
            sys.exit()
        elif opt in ("-e", "--effectiveDB"):
            effCfgFile = arg
        elif opt in ("-d", "--definedDBFile"):
            defCfgFile = arg
        elif opt in ("-z","--zonesFile"):
            zoneDelFile = arg
        elif opt in ("-w", "--wwnsFile"):
            wwnDelFile = arg
        elif opt in ("--insecure"):
            prefix = "http"


    if (effCfgFile is None or defCfgFile is None or zoneDelFile is None or wwnDelFile is None):
        print("usage: {} -e <effectiveDBFile> -d <definedDBFile> -z <zonesFile> -w <wwnsFile>".format(argv[0]))
        sys.exit(2)



    defined = getConfigurationFromFile(defCfgFile)
    effective = getConfigurationFromFile(effCfgFile)
    zonesToDelete = getSetFromFile(zoneDelFile)
    wwnsToDelete = getSetFromFile(wwnDelFile)

    aliasTable = buildAliasToWwn(defined)
    wwnLookupTable = flipAliastoWWN(aliasTable)

    effZones, effWWPNs = getZonesAndWWPNsFromEffectiveConfig(effective)
    defZones, defAliases = getZonesAndMembersFromDefinedConfig(defined)


    # Check 1: Verify format of all WWNs
    problem = False
    for i in wwnsToDelete:
        if not re.search("([0-9a-fA-F]{2}:){7}[0-9a-fA-F]{2}", i):
            if not problem:
                print("\nError: Non-WWN(s) found in WWN Delete List:")
            problem = True
            print("\t{}".format(i))
    if problem:
        exit(2)   

    # Check 2: Verify all WWNs are currently assigned an alias
    notFoundList = wwnsToDelete - set(wwnLookupTable.keys())
    if len(notFoundList) > 0:
        problem = True
        print("\nERROR: WWNs in delete list do not have corresponding aliases:")
        for i in notFoundList:
            print("\t{}".format(i))

    aliasesToDelete = getAliasesFromWwns(wwnLookupTable, wwnsToDelete)

    # Check 3: Verify all zone names in delete list are defined
    notFoundList = zonesToDelete.difference(defZones)
    if len(notFoundList) > 0:
        problem = True
        print("\nERROR: Zone names in delete list do not have corresponding zone definitions:")
        for i in SortedList(notFoundList):
            if len(i) > 0:
                print("\t{}".format(i))
    if problem:
        exit(2)   

    # Print information for human verification of results
    print("Zones in active cfg:")
    for i in SortedList(effZones):
        print("\t{}".format(i))

    print("\nZones to be deleted:")
    for i in SortedList(zonesToDelete):
        print("\t{}".format(i))

    print("\nWWNs in active cfg:")
    for i in SortedList(effWWPNs):
        print("\t{}".format(i))

    print("\nWWNs to be deleted:")
    for i in SortedList(wwnsToDelete):
        print("\t{}".format(i))

    # Check 4: Check for non-removable zones
    zoneOverlap = effZones.intersection(zonesToDelete)
    if len(zoneOverlap) > 0:
        problem = True
        print("\nERROR: Zones in delete list appear in the active configuration!")
        print("Offending zones:")
        for i in SortedList(zoneOverlap):
            print("\t{}".format(i))
    else:
        print("\nThere are no zones in the delete list that appear in the active configuration.")


    # Check 5: Check for non-removable wwns
    wwnOverlap = effWWPNs.intersection(wwnsToDelete)
    if len(wwnOverlap) > 0:
        problem = True
        print("\nERROR: WWNs in delete list appear in the active configuration!")
        print("Offending WWNs:")
        for i in SortedList(wwnOverlap):
            print("\t{}".format(i))
    else:
        print("\nThere are no WWNs in the delete list that appear in the active configuration.")


    if problem:
        print("\nSTOP!  Do not proceed until the problems listed above have been addressed.")
        exit(2)

    # Print cross reference table for aliases
    print("\nWWN to Alias Translation Table:")
    for i in SortedList(wwnsToDelete):
        print("\t{} -> {}".format(i, wwnLookupTable[i]))

    # Show reolved aliases to be deleted from definedDB
    print("\nAliases to be deleted to remove WWNs in list:")
    for i in SortedList(aliasesToDelete):
        print("\t{}".format(i))

    print("\nReview the above and if appropriate proceed to the deletion step.")
    print("Do not proceed unless the above has been verified independently as correct.")

if __name__ == "__main__":
    main(sys.argv)