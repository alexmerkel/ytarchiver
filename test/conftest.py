#!/usr/bin/env python3
''' configure pytest run '''

import os
import pytest
from appdirs import user_data_dir

# --------------------------------------------------------------------------- #
def pytest_configure(config):
    '''Called by pytest after the command line options have been parsed'''
# ########################################################################### #

# --------------------------------------------------------------------------- #
def pytest_sessionstart(session):
    '''Called by pytest before entering the run test loop'''
    #Set environment variable for testing
    os.environ["YTA_TEST"] = "TRUE"
    os.environ["YTA_TESTDATA"] = os.path.join(os.path.dirname(__file__), "testdata")
# ########################################################################### #

# --------------------------------------------------------------------------- #
def pytest_sessionfinish(session, exitstatus):
    '''Called by pytest after whole test run finished'''
    #Unset testing environment variable
    try:
        del os.environ["YTA_TEST"]
    except KeyError:
        pass
    try:
        del os.environ["YTA_TESTDATA"]
    except KeyError:
        pass
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture()
def apikey(capsys):
    '''Read or ask for Youtube API key for testing'''
    #Check if envorinment already contains a test API key
    if os.environ.get("YTA_TEST_APIKEY"):
        #Noting to do
        return
    #Try reading from user data dir (e.g. /usr/local/share, /Library/Application Support)
    apiFile = os.path.join(user_data_dir("ytarchiver", "yta"), "yttestapikey")
    try:
        with open(apiFile) as f:
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
        with capsys.disabled():
            print("INFO: No testing API key available!")
            print("INFO: Add it to the \'{}\' file,".format(apiFile))
            print("INFO: to the $YTA_TEST_APIKEY environment variable,")
            print("INFO: or use \'-m \"not tube\"\' option to skip tests that require an API key")
        pytest.exit("Missing Youtube API key for testing", 3)
    #Save result
    os.environ["YTA_TEST_APIKEY"] = apiKey
# ########################################################################### #
