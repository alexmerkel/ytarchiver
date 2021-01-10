#!/usr/bin/env python3
''' common functions for the test suite of ytarchiver '''

import os
from appdirs import user_data_dir

TESTDATA = os.path.join(os.path.dirname(__file__), "testdata")

# --------------------------------------------------------------------------- #
def setTestMode():
    '''Set environment variable for testing'''
    os.environ["YTA_TEST"] = "TRUE"
# ########################################################################### #

# --------------------------------------------------------------------------- #
def unsetTestMode():
    '''Unset environment variable for testing'''
    try:
        del os.environ["YTA_TEST"]
    except KeyError:
        pass
# ########################################################################### #

# --------------------------------------------------------------------------- #
def setTestAPIKey():
    '''Read or ask for Youtube API key for testing'''
    #Check if envorinment already contains a test API key
    if os.environ.get("YTA_TEST_APIKEY"):
        #Noting to do
        return
    #Try reading from user data dir (e.g. /usr/local/share, /Library/Application Support)
    userDir = user_data_dir("ytarchiver", "yta")
    try:
        with open(os.path.join(userDir, "yttestapikey")) as f:
            #Read first line
            line = f.readline().strip()
            while line:
                #If line is not a comment, return it as the api key
                if not line.startswith('#'):
                    apiKey = line
                    break
                #Read next line
                line = f.readline().strip()
            #Either no lines or only comments
            apiKey = None
    except OSError:
        #No api key
        apiKey = None
    #Ask user
    if not apiKey:
        q = input("Enter Youtube API key for testing or press enter to continue without (NOT RECOMMENDED): ")
        if q:
            #Save given key
            apiKey = q
            try:
                os.makedirs(userDir, exist_ok=True)
                with open(os.path.join(userDir, "yttestapikey"), 'w') as f:
                    f.write(apiKey)
            except OSError:
                print("WARNING: Unable to save API key")
                raise
    #Save result
    if apiKey:
        os.environ["YTA_TEST_APIKEY"] = apiKey
# ########################################################################### #

# --------------------------------------------------------------------------- #
def deleteIfExists(path):
    '''Deletes the file at path if it exists'''
    try:
        os.remove(path)
    except OSError:
        pass
# ########################################################################### #
