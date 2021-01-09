#!/usr/bin/env python3
''' unit test suite for ytacommon '''

import os
import sys
from shutil import copyfile
import pytest
import common

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ytacommon

TESTDATA = os.path.join(os.path.dirname(__file__), "testdata")

# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def setup():
    '''Common setup'''
    common.setTestMode()
    #common.setTestAPIKey()
    yield
    common.unsetTestMode()
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("version", [0, 1], ids=["new", "1>2"])
def test_upgradeDatabaseV2(version):
    '''Test the database upgrade to version 2'''
    #Prepare test database
    dbPath = prepareAndUpgradeDatabase(version)
    #Connect to database
    db = ytacommon.connectDB(dbPath)
    #Verify version
    r = db.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] >= 2
    #Verify added columns
    r = db.execute("UPDATE channel SET dbversion=?,lastupdate=?,videos=? WHERE id = 1", (2,1577836800,10))
    assert r.rowcount == 1
    del r
    #Close and remove database
    ytacommon.closeDB(db)
    common.deleteIfExists(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("version", [0, 1, 2], ids=["new", "1>3", "2>3"])
def test_upgradeDatabaseV3(version):
    '''Test the database upgrade to version 3'''
    #Prepare test database
    dbPath = prepareAndUpgradeDatabase(version)
    #Connect to database
    db = ytacommon.connectDB(dbPath)
    #Verify version
    r = db.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] >= 3
    #Verify added video columns
    r = db.execute("UPDATE videos SET language=?,width=?,height=?,resolution=? WHERE id = 1", ("en",1920,1080,"Full HD"))
    assert r.rowcount == 1
    #Veriy added channel column
    r = db.execute("SELECT maxresolution FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] == "default"
    #Close and remove database
    ytacommon.closeDB(db)
    common.deleteIfExists(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("version", [0, 1, 2, 3], ids=["new", "1>4", "2>4", "3>4"])
def test_upgradeDatabaseV4(version):
    '''Test the database upgrade to version 4'''
    #Prepare test database
    dbPath = prepareAndUpgradeDatabase(version)
    #Connect to database
    db = ytacommon.connectDB(dbPath)
    #Verify version
    r = db.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] >= 4
    #Verify added video columns
    r = db.execute("UPDATE videos SET viewcount=?,likecount=?,dislikecount=?,statisticsupdated=? WHERE id = 1", (1000,90,5,1577836800))
    assert r.rowcount == 1
    #Close and remove database
    ytacommon.closeDB(db)
    common.deleteIfExists(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("version", [0, 1, 2, 3, 4], ids=["new", "1>5", "2>5", "3>5", "4>5"])
def test_upgradeDatabaseV5(version):
    '''Test the database upgrade to version 5'''
    #Prepare test database
    dbPath = prepareAndUpgradeDatabase(version)
    #Connect to database
    db = ytacommon.connectDB(dbPath)
    #Verify version
    r = db.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] >= 5
    #Verify added chapters
    if version > 0:
        r = db.execute("SELECT id FROM videos WHERE chapters NOT NULL;")
        assert len(r.fetchall()) == 6
    else:
        r = db.execute("UPDATE videos SET chapters=? WHERE id = 1", ("00:00:00.000 Test 1",))
        assert r.rowcount == 1
    #Close and remove database
    ytacommon.closeDB(db)
    common.deleteIfExists(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("version", [0, 1, 2, 3, 4, 5], ids=["new", "1>6", "2>6", "3>6", "4>6", "5>6"])
def test_upgradeDatabaseV6(version):
    '''Test the database upgrade to version 6'''
    #Prepare test database
    dbPath = prepareAndUpgradeDatabase(version)
    #Connect to database
    db = ytacommon.connectDB(dbPath)
    #Verify version
    r = db.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] >= 6
    #Verify new resolution names
    if version > 2:
        r = db.execute("SELECT id FROM videos WHERE resolution = 'LD';")
        assert len(r.fetchall()) == 2
    r = db.execute("UPDATE videos SET resolution=? WHERE id = 1", ("LD",))
    assert r.rowcount == 1
    #Verify added oldtitles and olddescriptions
    r = db.execute("UPDATE videos SET oldtitles=?,olddescriptions=? WHERE id = 1", ("oldtitle","olddesc"))
    assert r.rowcount == 1
    #Close and remove database
    ytacommon.closeDB(db)
    common.deleteIfExists(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("version", [0, 1, 2, 3, 4, 5, 6], ids=["new", "1>7", "2>7", "3>7", "4>7", "5>7", "6>7"])
def test_upgradeDatabaseV7(version):
    '''Test the database upgrade to version 7'''
    #Prepare test database
    dbPath = prepareAndUpgradeDatabase(version)
    #Connect to database
    db = ytacommon.connectDB(dbPath)
    #Verify version
    r = db.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] >= 7
    #Verify added filesize
    r = db.execute("UPDATE videos SET filesize=? WHERE id = 1", (100000,))
    assert r.rowcount == 1
    #Verify added totalsize
    r = db.execute("UPDATE channel SET totalsize=? WHERE id = 1", (1000000,))
    assert r.rowcount == 1
    #Close and remove database
    ytacommon.closeDB(db)
    common.deleteIfExists(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def createNewTestDB(path):
    '''Create a test db using the two ytacommon methods'''
    #Connect
    dbCon = ytacommon.connectDB(path)
    #Create video table
    ytacommon.createVideoTable(dbCon)
    insert = "INSERT INTO videos(title,creator,date,timestamp,youtubeID,filename,checksum,language,width,height,resolution,statisticsupdated,filesize) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)"
    dbCon.execute(insert, ("Test", "Test", "2020-01-01", 1577836800, "abcdefghijk", "test.mp4", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", "en", 1920, 1080, "Full HD", 1577836800, 1000000))
    #Create channel table
    ytacommon.createChannelTable(dbCon)
    insert = "INSERT INTO channel(name, url, playlist, language, videos, lastupdate, dbversion, maxresolution, totalsize) VALUES(?,?,?,?,?,?,?,?,?)"
    dbCon.execute(insert, ('', '', '', '', 0, 0, ytacommon.__dbversion__, "default", 0))
    #Close
    ytacommon.closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def prepareAndUpgradeDatabase(version):
    '''Prepare the database and perform the update, returns path to upgraded database'''
    #Prepare database
    origDBPath = os.path.join(TESTDATA, "dbversions", "dbv{}.db".format(version))
    dbPath = os.path.join(TESTDATA, "test.db")
    common.deleteIfExists(dbPath)
    if version > 0:
        #Old database version
        copyfile(origDBPath, dbPath)
        ytacommon.upgradeDatabase(dbPath)
    else:
        createNewTestDB(dbPath)
    return dbPath
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("w,h,expInd,expStr", [(320,240,0,"LD"), (640,360,0,"LD"), (640,480,0,"SD"), (854,480,0,"SD"), (768,576,0,"SD"), (1024,576,0,"SD"), (1280,720,1,"HD"), (1920,1080,2,"Full HD"), (1080,1920,2,"Full HD"), (1920,810,2,"Full HD"), (2560,1440,2,"Full HD"), (3840,2160,3,"4K UHD"), (7680,4320,3,"8K UHD")], ids=["LD240", "LD360", "SD480", "SD480w", "SD576", "SD576w", "HD720", "HD1080", "HD1080f", "HD1080w", "HD1440", "UHD2160", "UHD4320"])
def test_convertResolution(w, h, expInd, expStr):
    '''Test the resolution conversion'''
    #Convert
    received = ytacommon.convertResolution(w,h)
    #Compare
    assert received == (expInd, expStr)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("string,expected", [("PT8S", 8), ("PT34S", 34), ("PT3M14S", 194), ("PT28M31S", 1711), ("PT1H28M55S", 5335), ("PT1H16S", 3616), ("P4DT4H1S", 360001), ("P1DT36M41S", 88601), ("P2W3DT13H25M19S", 1517119)], ids=["sec", "two_sec", "sec+min", "sec+two_min", "sec+min+hour", "sec+hour", "day+hour+sec", "day+min+sec", "week+day+hour+min+sec"])
def test_convertDuration(string, expected):
    '''Test the duration conversion'''
    #Convert
    received = ytacommon.convertDuration(string)
    #Compare
    assert received == expected
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("num", [1, 2, 3, 4, 5, 6], ids=["default", "only_two", "unicode", "split_second", "split_first", "formats"])
def test_extractChapters(num):
    '''Test the chapter extraction'''
    #Read description
    descPath = os.path.join(TESTDATA, "testdesc", "{}.desc".format(num))
    with open(descPath) as f:
        desc = f.read()
    #Read expected chapters
    chaptersPath = os.path.join(TESTDATA, "testdesc", "{}.chapters".format(num))
    with open(chaptersPath) as f:
        expected = f.read()
    if not expected:
        expected = None
    #Extract chapters
    received = ytacommon.extractChapters(desc)
    #Compare
    assert received == expected
# ########################################################################### #
