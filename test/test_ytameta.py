#!/usr/bin/env python3
''' unit test suite for ytameta '''

import os
import time
import pytest
import utils
import sqlite3
from requests.exceptions import RequestException

import ytameta

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.parametrize("expException", [False, pytest.param(True, marks=pytest.mark.disable_requests)],
    ids=["network", "nonetwork"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", "dbv7.db"))
def test_addMetadata(request, capsys, temparchive, expException):
    '''Test adding the metadata from the Youtube API to the database'''
    #Remove metadata from database
    path = request.node.get_closest_marker("internal_path").args[0]
    db = sqlite3.connect(os.path.join(path, "archive.db"))
    db.execute("UPDATE videos SET timestamp = 0, duration = 0, tags = \"\";")
    db.commit()
    db.close()
    #Check if exception expected
    if expException:
        ytameta.addMetadata([path])
        captured = capsys.readouterr()
        assert captured.out.startswith("ERROR: Unable to load metadata for")
    else:
        #Add metadata
        ytameta.addMetadata([path])
        #Compare
        db = sqlite3.connect(os.path.join(path, "archive.db"))
        assert len(db.execute("SELECT id FROM videos WHERE duration != 60;").fetchall()) == 0
        assert len(db.execute("SELECT id FROM videos WHERE timestamp >= 1609286401 and timestamp <= 1609304400;").fetchall()) == 6
        assert len(db.execute("SELECT id FROM videos WHERE tags = \"\";").fetchall()) == 0
        assert db.execute("SELECT tags FROM videos WHERE id = 1;").fetchone()[0] == "example\none\nvideo\ntest"
        db.close()
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.parametrize("expException", [False, pytest.param(True, marks=pytest.mark.disable_requests)],
    ids=["network", "nonetwork"])
def test_getMetadata(capsys, expException):
    '''Test getting the metadata from the Youtube API'''
    #Get metadata
    if expException:
        with pytest.raises(RequestException):
            ytameta.getMetadata("0-cN7NVjXxc")
    else:
        #Test video with metadata
        t1 = int(time.time())
        received = ytameta.getMetadata("0-cN7NVjXxc")
        t2 = int(time.time())
        #Compare
        assert received[0:4] == [1609286401, 60, "example\none\nvideo\ntest", "The first example video\n\n0:00 Grow one\n0:30 Halt one\n0:45 Shrink one\n\nLD\nCaptions\n\nGoodbye"]
        assert t1 <= received[7] <= t2
        #Test nonexisting video
        received = ytameta.getMetadata("01234567890")
        captured = capsys.readouterr()
        assert captured.out == "WARNING: No metadata available for 01234567890\n"
        assert received == [None] * 8
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.parametrize("lang,expected", [
    ("en", "INFO: Added subtitle"),
    ("de", "ERROR: No subtitle with language"),
    pytest.param("en", "ERROR: Unable to amend", marks=pytest.mark.disable_requests)],
    ids=["available", "unavailable", "network"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "subtest.db"))
def test_amendCaption(capsys, tempcopy, db, lang, expected):
    '''Test the ability to amend the archived subtitles'''
    #Get ids from database
    r = db.execute("SELECT id,youtubeID,shouldHaveSub FROM videos")
    videos = r.fetchall()
    #Loop through videos
    for video in videos:
        ytameta.amendCaption(db, video[0], video[1], lang)
        captured = capsys.readouterr()
        if video[2]:
            assert captured.out.startswith(expected)
        else:
            assert captured.out.startswith(expected) or captured.out.startswith("ERROR: No subtitle with language")
# ########################################################################### #

# --------------------------------------------------------------------------- #
def test_connectUpdateCreateStatisticsDB():
    '''Test the creation of a statistics database and the connection to an existing
    one. The upgrade functionality cannot really be tested yet, as there is only
    v1 of the statistics database
    '''
    dbPath = os.path.join(os.environ["YTA_TESTDATA"], "statistics.db")
    #Clear previous
    utils.deleteIfExists(dbPath)
    #Create a database
    dbCon = ytameta.connectUpdateCreateStatisticsDB(os.environ["YTA_TESTDATA"])
    #Verify v1 database tables
    r = dbCon.execute("SELECT autoupdate,lastupdate,maxcount,dbversion FROM setup WHERE id = 1;")
    data = r.fetchone()
    assert not data[0] #Autoupate == False
    assert data[1] == 0 #No lastupdate yet
    assert data[2] == 100000 #Default maxcount
    assert data[3] == 1 #Statistics database version 1
    r = dbCon.execute("INSERT INTO channels(name,lastupdate,complete) VALUES(?,?,?);", ("Test", 1577836800, True))
    assert r.rowcount == 1
    #Close database
    dbCon.commit()
    dbCon.close()
    #Reopen database
    dbCon = ytameta.connectUpdateCreateStatisticsDB(os.environ["YTA_TESTDATA"])
    #Read data from channels
    r = dbCon.execute("SELECT name,lastupdate,complete FROM channels WHERE id = 1;")
    data = r.fetchone()
    assert data[0] == "Test"
    assert data[1] == 1577836800
    assert data[2] #True
    #Close and delete database
    dbCon.close()
    utils.deleteIfExists(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def test_getResetTimestamp():
    '''Test getting the timestamp of the last midnight pacific time'''
    #Get timestamp
    received = ytameta.getResetTimestamp()
    current = int(time.time())
    #Can't know the supposed time without reimplementing the function
    #Therefore, tests that the received timestamp lies in the last 24 hours
    #and that a full hour was received
    assert current - 86400 < received <= current
    assert received % 60 == 0
# ########################################################################### #
