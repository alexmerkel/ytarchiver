#!/usr/bin/env python3
''' configure pytest run '''

import os
import sqlite3
import string
import random
import socket
import shutil
import pytest
from appdirs import user_data_dir
from requests.exceptions import ConnectionError as rConnectionError

LATEST_DB = "dbv7.db"

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
    os.environ["YTA_TEST_LATESTDB"] = LATEST_DB
# ########################################################################### #

# --------------------------------------------------------------------------- #
def pytest_sessionfinish(session, exitstatus):
    '''Called by pytest after whole test run finished'''
    #Unset testing environment variable
    try:
        del os.environ["YTA_TEST"]
    except KeyError:
        pass
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _tubeMarker(request):
    '''Add apikey fixture if the tube marker is used'''
    if request.node.get_closest_marker("tube"):
        request.getfixturevalue("apikey")
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture()
def apikey(capsys):
    '''Read or ask for Youtube API key for testing'''
    #Check if environment already contains a test API key
    if os.environ.get("YTA_TEST_APIKEY"):
        #Noting to do
        return
    #Try reading from user data dir (e.g. /usr/local/share, /Library/Application Support)
    apiFile = os.path.join(user_data_dir("ytarchiver", "yta"), "yttestapikey")
    apiKey = None
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
    except OSError:
        #No api key
        apiKey = None
    #Ask user
    if not apiKey:
        with capsys.disabled():
            print("ERROR: No testing API key available!")
            print("INFO: Add it to the \"{}\" file,".format(apiFile))
            print("INFO: to the $YTA_TEST_APIKEY environment variable,")
            print("INFO: or use \'-m \"not tube\"\' option to skip tests that require an API key")
        pytest.exit("Missing Youtube API key for testing", 3)
    #Save result
    os.environ["YTA_TEST_APIKEY"] = apiKey
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture
def temparchive(request):
    '''Creates a temporary archive by copying the database given via the
    "internal_path" marker into a temp directory and renaming it to archive.db,
    rewrites the "internal_path" to the new temporary directory and
    delete it afterwards
    '''
    #Read path
    dbPath = request.node.get_closest_marker("internal_path").args[0]
    #Create temporary archive directory
    tempPath = os.path.join(os.environ["YTA_TESTDATA"], "temp_"+generateRandom(10))
    os.mkdir(tempPath)
    #Copy database to archive and change marker
    shutil.copyfile(dbPath, os.path.join(tempPath, "archive.db"))
    request.node.add_marker(pytest.mark.internal_path(tempPath), False)
    #Wait for test to finish
    yield
    #Remove temporary archive
    shutil.rmtree(tempPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _temparchiveMarker(request):
    if request.node.get_closest_marker("temp_archive"):
        request.getfixturevalue("temparchive")
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture
def tempallarchive(request):
    '''Creates a temporary directory of archives by copying the database given via
    the "internal_path" marker into 3 temp subdirectory and renaming them to
    archive.db, rewrites the "internal_path" to the new temporary directory, and
    deletes it afterwards
    '''
    #Read path
    dbPath = request.node.get_closest_marker("internal_path").args[0]
    #Create temporary main directory
    tempPath = os.path.join(os.environ["YTA_TESTDATA"], "temp_"+generateRandom(10))
    os.mkdir(tempPath)
    #Create archive subdirectories and copy the database
    for i in range(1, 4):
        subPath = os.path.join(tempPath, str(i))
        os.mkdir(subPath)
        subDB = os.path.join(subPath, "archive.db")
        shutil.copyfile(dbPath, subDB)
        _db = sqlite3.connect(subDB)
        _db.execute("UPDATE channel SET name = (SELECT name FROM channel WHERE id = 1) || ?;", (" {}".format(i),))
        _db.commit()
        _db.close()
    #Cahnge marker
    request.node.add_marker(pytest.mark.internal_path(tempPath), False)
    #Wait for test to finish
    yield
    #Remove temporary archive
    shutil.rmtree(tempPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _tempallarchiveMarker(request):
    if request.node.get_closest_marker("temp_allarchive"):
        request.getfixturevalue("tempallarchive")
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture
def tempcopy(request):
    '''Creates a temporary copy of the file given via the "internal_path"
    marker, rewrites the "internal_path" to the new temporary file, and
    deletes it afterwards
    '''
    #Read path
    origPath = request.node.get_closest_marker("internal_path").args[0]
    #Generate temporary path
    _, ext = os.path.splitext(origPath)
    tempPath = os.path.join(os.environ["YTA_TESTDATA"], "temp_"+generateRandom(10)+ext)
    request.node.add_marker(pytest.mark.internal_path(tempPath), False)
    #Copy file
    shutil.copyfile(origPath, tempPath)
    #Wait for test to finish
    yield
    #Remove temporary file
    os.remove(tempPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture
def tempdir(request):
    '''Creates a temporary directory, writes its path to the "internal_path2"
    marker, and deletes the directory afterwards
    '''
    #Create temporary directory
    tempPath = os.path.join(os.environ["YTA_TESTDATA"], "temp_"+generateRandom(10))
    os.mkdir(tempPath)
    #Change marker
    request.node.add_marker(pytest.mark.internal_path2(tempPath), False)
    #Wait for test to finish
    yield
    #Remove temporary file
    shutil.rmtree(tempPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def generateRandom(length, chars=string.hexdigits):
    '''Generate a random string of given length, not cryptographically secure'''
    return ''.join(random.choice(chars) for _ in range(length))
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture
def dbCon(request):
    '''Get a database connection to the database given via the "internal_path" marker'''
    #Read database path
    marker = request.node.get_closest_marker("internal_path")
    dbPath = marker.args[0]
    #Open database
    _dbCon = sqlite3.connect(dbPath)
    yield _dbCon
    _dbCon.close()
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture
def db(dbCon):
    '''Get a database cursor to the database given via the "internal_path" marker'''
    return dbCon.cursor()
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture
def disableRequests():
    '''Disable requests by throwing requests.exceptions.ConnectionError'''
    true = disRequests()
    yield
    enRequests(true)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _disableRequestsMarker(request):
    if request.node.get_closest_marker("disable_requests"):
        request.getfixturevalue("disableRequests")
# ########################################################################### #

# --------------------------------------------------------------------------- #
def disRequests():
    '''Disable requests by raising a requests.exceptions.ConnectionError when
    a socket connection is being established, return true socket for later reset
    '''
    def raiseExp(*args, **kwargs):
        raise rConnectionError
    trueSocket = socket.socket
    socket.socket = raiseExp
    return trueSocket
# ########################################################################### #

# --------------------------------------------------------------------------- #
def enRequests(trueSocket):
    '''Re-enable requests by returning socket.socket to its normal state'''
    socket.socket = trueSocket
# ########################################################################### #
