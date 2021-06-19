#!/usr/bin/env python3
''' unit test suite for ytameta '''

import os
import time
import shutil
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
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
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
        assert len(db.execute("SELECT id FROM videos WHERE duration NOT BETWEEN 59 AND 61;").fetchall()) == 0
        assert len(db.execute("SELECT id FROM videos WHERE timestamp >= 1609286401 and timestamp <= 1609304400;").fetchall()) == 6
        assert len(db.execute("SELECT id FROM videos WHERE tags = \"\";").fetchall()) == 0
        assert db.execute("SELECT tags FROM videos WHERE id = 1;").fetchone()[0] == "example\none\nvideo\ntest"
        db.close()
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.parametrize("mode", ["normal", "sub", "amendsub", pytest.param("network", marks=pytest.mark.disable_requests)],
    ids=["normal", "checksub", "amendsub", "network"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_updateStatistics(capsys, tempcopy, db, mode):
    '''Test updating the video statistics via the Youtube API'''
    #Switch by mode
    #Test the ability to update the statistics
    if mode == "normal":
        #Set viewcount to 0 for comparison
        db.execute("UPDATE videos SET viewcount = 0;")
        #Update the statistics
        t1 = int(time.time())
        ytameta.updateStatistics(db)
        t2 = int(time.time())
        #Compare
        assert len(db.execute("SELECT id FROM videos WHERE viewcount > 0;").fetchall()) == 6
        assert len(db.execute("SELECT id FROM videos WHERE statisticsupdated >= ? and statisticsupdated <= ?;", (t1, t2)).fetchall()) == 6
    #Test the ability to print missing subtitles
    elif mode == "sub":
        #Prepare database
        db.execute("UPDATE videos SET subtitles = ? WHERE id = 1;", (None,))
        #Update statistics
        ytameta.updateStatistics(db, checkCaptions=True)
        #Compare
        captured = capsys.readouterr()
        assert captured.out == "INFO: Video [0-cN7NVjXxc] \"Example 1\" had captions added since archiving\n"
    #Test the ability to amend missing subtitles
    elif mode == "amendsub":
        #Prepare database
        db.execute("UPDATE videos SET subtitles = ? WHERE id = 1;", (None,))
        #Update statistics
        ytameta.updateStatistics(db, amendCaptions=True)
        #Compare
        received = db.execute("SELECT subtitles FROM videos WHERE id = 1;").fetchone()[0]
        assert received.startswith("WEBVTT\nKind: captions\nLanguage: en\n\n00:00:00.000 --> 00:00:00.900\n")
        assert len(received) == 358
    #Test the exception is thrown correctly
    elif mode == "network":
        with pytest.raises(RequestException):
            ytameta.updateStatistics(db)
    else:
        pytest.fail("Unknown mode: {}".format(mode))
# ########################################################################### #

@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_test(capsys, tempallarchive):
    pass

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.parametrize("mode", ["normal", "none", "sub", "amendsub", pytest.param("network", marks=pytest.mark.disable_requests)],
    ids=["normal", "none", "checksub", "amendsub", "network"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_updateAllStatistics(request, capsys, tempallarchive, mode):
    '''Test updating the video statistics via the Youtube API'''
    #Get archive path
    path = request.node.get_closest_marker("internal_path").args[0]
    subdirs = [os.path.join(path, name) for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    #Switch by mode
    #Test the ability to update the statistics
    if mode == "normal":
        #Update the statistics
        t1 = int(time.time())
        ytameta.updateAllStatistics(path)
        t2 = int(time.time())
        #Compare
        for subdir in subdirs:
            db = sqlite3.connect(os.path.join(subdir, "archive.db"))
            assert len(db.execute("SELECT id FROM videos WHERE statisticsupdated >= ? and statisticsupdated <= ?;", (t1, t2)).fetchall()) == 6
            db.close()
        db = sqlite3.connect(os.path.join(path, "statistics.db"))
        assert len(db.execute("SELECT id FROM channels WHERE lastupdate >= ? and lastupdate <= ?;", (t1, t2)).fetchall()) == len(subdirs)
        assert t1 <= db.execute("SELECT lastupdate FROM setup WHERE id = 1;").fetchone()[0] <= t2
    #Test error message when no archive subdirectory available
    elif mode == "none":
        #Rename archive databases
        for subdir in subdirs:
            try:
                os.rename(os.path.join(subdir, "archive.db"), os.path.join(subdir, "archive1.db"))
            except OSError:
                pass
        #Update statistics
        ytameta.updateAllStatistics(path, automatic=False)
        #Compare
        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        assert lines[-2].strip() == "UPDATING VIDEO STATISTICS"
        assert lines[-1].strip() == "ERROR: No subdirs with archive databases at \'{}\'".format(path)
        #Remove subdirs
        for subdir in subdirs:
            shutil.rmtree(subdir)
        #Update statistics
        ytameta.updateAllStatistics(path, automatic=True)
        captured = capsys.readouterr()
        lines = captured.out.splitlines()
        assert lines[-2].strip() == "UPDATING VIDEO STATISTICS DUE TO DATABASE OPTION"
        assert lines[-1].strip() == "ERROR: No subdirs with archive databases at \'{}\'".format(path)
    #Test the ability to print or amend missing subtitles
    elif mode in ("sub", "amendsub"):
        #Prepare archives
        for subdir in subdirs:
            db = sqlite3.connect(os.path.join(subdir, "archive.db"))
            db.execute("UPDATE videos SET subtitles = ? WHERE id = 1;", (None,))
            db.commit()
            db.close()
        #Just print the missing captions
        if mode == "sub":
            #Update statistics
            ytameta.updateAllStatistics(path, captions=True)
            captured = capsys.readouterr()
            lines = captured.out.splitlines()
            assert len([s for s in lines if s.strip() == "INFO: Video [0-cN7NVjXxc] \"Example 1\" had captions added since archiving"]) == 3
        #Amend the missing captions
        else:
            #Update statistics
            ytameta.updateAllStatistics(path, amendCaptions=True)
            captured = capsys.readouterr()
            lines = captured.out.splitlines()
            assert len([s for s in lines if s.strip() == "INFO: Added subtitle \"en\" for video \"0-cN7NVjXxc\" to the database"]) == 3
            for subdir in subdirs:
                db = sqlite3.connect(os.path.join(subdir, "archive.db"))
                received = db.execute("SELECT subtitles FROM videos WHERE id = 1;").fetchone()[0]
                assert received.startswith("WEBVTT\nKind: captions\nLanguage: en\n\n00:00:00.000 --> 00:00:00.900\n")
                assert len(received) == 358
                db.close()
    #Test the exception is thrown correctly
    elif mode == "network":
        ytameta.updateAllStatistics(path)
        captured = capsys.readouterr()
        assert captured.out.splitlines()[-1].startswith("ERROR: Network error while trying to update the statistics")
    else:
        pytest.fail("Unknown mode: {}".format(mode))
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
        assert received[0] == 1609286401
        assert 59 <= received[1] <= 61
        assert received[2:4] == ["example\none\nvideo\ntest", "The first example video\n\n0:00 Grow one\n0:30 Halt one\n0:45 Shrink one\n\nLD\nCaptions\n\nGoodbye"]
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
    ("de", "INFO: No subtitle with language"),
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
            assert captured.out.startswith(expected) or captured.out.startswith("INFO: No subtitle with language")
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
