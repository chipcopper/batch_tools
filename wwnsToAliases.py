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
import sys
import json
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
    fileSet = SortedSet()

    with open(filename, "r") as fp:
        fileLines = fp.readlines()

    for i in fileLines:
        entry = i.strip()
        if len(entry) > 0:
            fileSet.add(entry)

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

def getAliasesFromWwns(wwnLookupTable, wwnList):
    aliasList = SortedSet()
    for i in wwnList:
        if i in wwnLookupTable.keys():
            for j in wwnLookupTable[i]:
                aliasList.add(j)
                
    return aliasList

def main(argv):
    defCfgFile = None
    wwnFile = None

    # Retrieve and parse command line arguments.
    try:
        opts, args = getopt.getopt(argv[1:],"d:w:",
            ["definedDB=", "wwnFile="])
    except getopt.GetoptError:
        print("usage: {} -d <definedDB -w <wwnsFile>".format(sys.argv[0]))
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("usage: {} -d <definedDB -w <wwnsFile>".format(sys.argv[0]))
            sys.exit()
        elif opt in ("-d", "--definedDB"):
            defCfgFile = arg
        elif opt in ("-w", "--wwnsFile"):
            wwnFile = arg


    # Verify all required arguments are present
    if (defCfgFile is None or wwnFile is None):
        print("usage: {} -d <definedDB -w <wwnsFile>".format(sys.argv[0]))
        sys.exit(2)

    defined = getConfigurationFromFile(defCfgFile)
    wwnList = getSetFromFile(wwnFile)
    
    aliasTable = buildAliasToWwn(defined)
    wwnLookupTable = flipAliastoWWN(aliasTable)

    # Check 1: Verify format of all WWNs
    problem = False
    for i in wwnList:
        if not re.search("([0-9a-fA-F]{2}:){7}[0-9a-fA-F]{2}", i):
            if not problem:
                print("\nERROR: Non-WWN(s) found in WWN List:")
            problem = True
            print("\t{}".format(i))
    if problem:
        exit(2)   

    # Check 2: Verify all WWNs are currently assigned an alias
    notFoundList = wwnList - set(wwnLookupTable.keys())
    if len(notFoundList) > 0:
        problem = True
        print("\nERROR: WWNs in list do not have corresponding aliases:")
        for i in notFoundList:
            problem = True
            print("\t{}".format(i))
    if problem:
        exit(2)  

    aliasesFound = getAliasesFromWwns(wwnLookupTable, wwnList)

    for i in aliasesFound:
    	print(i)


if __name__ == "__main__":
	main(sys.argv)