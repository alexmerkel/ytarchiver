#!/usr/bin/env python3
''' unit test suite for ytacommon '''

import os
from shutil import copyfile
import pytest
import utils

import ytacommon

# --------------------------------------------------------------------------- #
def test_calcSHA():
    '''Test the SHA256 calculation'''
    #Perform calculation
    received = ytacommon.calcSHA(os.path.join(os.environ["YTA_TESTDATA"], "testimg.png"))
    #Compare
    expected = "5cf2415463b439b87d908570b1e6caa98d77707cfbae187d04448cf36a3653e0"
    assert received == expected
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
def test_loadImage():
    '''Test the image download'''
    #Download file
    url = "https://raw.githubusercontent.com/alexmerkel/ytarchiver/master/test/testdata/testimg.png"
    [img, mime] = ytacommon.loadImage(url)
    #Read comparison
    with open(os.path.join(os.environ["YTA_TESTDATA"], "testimg.png"), "rb") as f:
        expected = f.read()
    #Compare
    assert mime == "image/png"
    assert img == expected
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    (), [
        pytest.param(marks=pytest.mark.internal_dbversion(0,2)),
        pytest.param(marks=pytest.mark.internal_dbversion(1,2))],
    ids=["new", "1>2"])
def test_upgradeDatabaseV2(upgradeDB):
    '''Test the database upgrade to version 2'''
    #Verify added columns
    r = upgradeDB.execute("UPDATE channel SET dbversion=?,lastupdate=?,videos=? WHERE id = 1", (2,1577836800,10))
    assert r.rowcount == 1
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    (), [
        pytest.param(marks=pytest.mark.internal_dbversion(0,3)),
        pytest.param(marks=pytest.mark.internal_dbversion(1,3)),
        pytest.param(marks=pytest.mark.internal_dbversion(2,3))],
    ids=["new", "1>3", "2>3"])
def test_upgradeDatabaseV3(upgradeDB):
    '''Test the database upgrade to version 3'''
    #Verify added video columns
    r = upgradeDB.execute("UPDATE videos SET language=?,width=?,height=?,resolution=? WHERE id = 1", ("en",1920,1080,"Full HD"))
    assert r.rowcount == 1
    #Verify added channel column
    r = upgradeDB.execute("SELECT maxresolution FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] == "default"
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    (), [
        pytest.param(marks=pytest.mark.internal_dbversion(0,4)),
        pytest.param(marks=pytest.mark.internal_dbversion(1,4)),
        pytest.param(marks=pytest.mark.internal_dbversion(2,4)),
        pytest.param(marks=pytest.mark.internal_dbversion(3,4))],
    ids=["new", "1>4", "2>4", "3>4"])
def test_upgradeDatabaseV4(upgradeDB):
    '''Test the database upgrade to version 4'''
    #Verify added video columns
    r = upgradeDB.execute("UPDATE videos SET viewcount=?,likecount=?,dislikecount=?,statisticsupdated=? WHERE id = 1", (1000,90,5,1577836800))
    assert r.rowcount == 1
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("version"), [
        pytest.param(0, marks=pytest.mark.internal_dbversion(0,5)),
        pytest.param(1, marks=pytest.mark.internal_dbversion(1,5)),
        pytest.param(2, marks=pytest.mark.internal_dbversion(2,5)),
        pytest.param(3, marks=pytest.mark.internal_dbversion(3,5)),
        pytest.param(4, marks=pytest.mark.internal_dbversion(4,5))],
    ids=["new", "1>5", "2>5", "3>5", "4>5"])
def test_upgradeDatabaseV5(upgradeDB, version):
    '''Test the database upgrade to version 5'''
    #Verify added chapters
    if version > 0:
        r = upgradeDB.execute("SELECT id FROM videos WHERE chapters NOT NULL;")
        assert len(r.fetchall()) == 6
    else:
        r = upgradeDB.execute("UPDATE videos SET chapters=? WHERE id = 1", ("00:00:00.000 Test 1",))
        assert r.rowcount == 1
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("version"), [
        pytest.param(0, marks=pytest.mark.internal_dbversion(0,6)),
        pytest.param(1, marks=pytest.mark.internal_dbversion(1,6)),
        pytest.param(2, marks=pytest.mark.internal_dbversion(2,6)),
        pytest.param(3, marks=pytest.mark.internal_dbversion(3,6)),
        pytest.param(4, marks=pytest.mark.internal_dbversion(4,6)),
        pytest.param(5, marks=pytest.mark.internal_dbversion(5,6))],
    ids=["new", "1>6", "2>6", "3>6", "4>6", "5>6"])
def test_upgradeDatabaseV6(upgradeDB, version):
    '''Test the database upgrade to version 6'''
    #Verify new resolution names
    if version > 2:
        r = upgradeDB.execute("SELECT id FROM videos WHERE resolution = 'LD';")
        assert len(r.fetchall()) == 2
    r = upgradeDB.execute("UPDATE videos SET resolution=? WHERE id = 1", ("LD",))
    assert r.rowcount == 1
    #Verify added oldtitles and olddescriptions
    r = upgradeDB.execute("UPDATE videos SET oldtitles=?,olddescriptions=? WHERE id = 1", ("oldtitle","olddesc"))
    assert r.rowcount == 1
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    (), [pytest.param(marks=pytest.mark.internal_dbversion(0,7)),
        pytest.param(marks=pytest.mark.internal_dbversion(1,7)),
        pytest.param(marks=pytest.mark.internal_dbversion(2,7)),
        pytest.param(marks=pytest.mark.internal_dbversion(3,7)),
        pytest.param(marks=pytest.mark.internal_dbversion(4,7)),
        pytest.param(marks=pytest.mark.internal_dbversion(5,7)),
        pytest.param(marks=pytest.mark.internal_dbversion(6,7))],
    ids=["new", "1>7", "2>7", "3>7", "4>7", "5>7", "6>7"])
def test_upgradeDatabaseV7(upgradeDB):
    '''Test the database upgrade to version 7'''
    #Verify added filesize
    r = upgradeDB.execute("UPDATE videos SET filesize=? WHERE id = 1", (100000,))
    assert r.rowcount == 1
    #Verify added totalsize
    r = upgradeDB.execute("UPDATE channel SET totalsize=? WHERE id = 1", (1000000,))
    assert r.rowcount == 1
    #Close and remove database
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.fixture
def upgradeDB(request):
    '''Prepare and upgrade database with versions given via the "internal_dbversion"
    marker in the for of (oldversion, newversion), verify upgraded database version
    number, yield connection to database, and close and delete it afterwards
    '''
    #Get database version
    oldVersion = request.node.get_closest_marker("internal_dbversion").args[0]
    newVersion = request.node.get_closest_marker("internal_dbversion").args[1]
    #Prepare test database
    dbPath = prepareAndUpgradeDatabase(oldVersion)
    #Connect to database
    _dbCon = ytacommon.connectDB(dbPath)
    #Verify version
    r = _dbCon.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
    assert r.fetchone()[0] >= newVersion
    yield _dbCon
    ytacommon.closeDB(_dbCon)
    utils.deleteIfExists(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def createNewTestDB(path):
    '''Create a test db using the two ytacommon methods'''
    #Connect
    dbCon = ytacommon.connectDB(path)
    #Create video table
    ytacommon.createVideoTable(dbCon)
    insert = "INSERT INTO videos(title,creator,date,timestamp,youtubeID,filename,checksum,language,width,height,resolution,statisticsupdated,filesize) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)"
    dbCon.execute(insert, ("Test", "Test", "2020-01-01", 1577836800, "test", "test.mp4", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", "en", 1920, 1080, "Full HD", 1577836800, 1000000))
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
    origDBPath = os.path.join(os.environ["YTA_TESTDATA"], "dbversions", "dbv{}.db".format(version))
    dbPath = os.path.join(os.environ["YTA_TESTDATA"], "test.db")
    utils.deleteIfExists(dbPath)
    if version > 0:
        #Old database version
        copyfile(origDBPath, dbPath)
        ytacommon.upgradeDatabase(dbPath)
    else:
        createNewTestDB(dbPath)
    return dbPath
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.exiftool
def test_readResolution():
    '''Test the resolution reading from a file'''
    #Read resoption
    hd, formatString, width, height = ytacommon.readResolution(os.path.join(os.environ["YTA_TESTDATA"], "testimg.png"))
    #Compare
    assert hd == 0
    assert formatString == "SD"
    assert width == 800
    assert height == 800
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
    descPath = os.path.join(os.environ["YTA_TESTDATA"], "testdesc", "{}.desc".format(num))
    with open(descPath) as f:
        desc = f.read()
    #Read expected chapters
    chaptersPath = os.path.join(os.environ["YTA_TESTDATA"], "testdesc", "{}.chapters".format(num))
    with open(chaptersPath) as f:
        expected = f.read()
    if not expected:
        expected = None
    #Extract chapters
    received = ytacommon.extractChapters(desc)
    #Compare
    assert received == expected
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("var,expected", [(10, 10), ("11", 11), (12.1, 12), ("13.2", None), ("abc", None), (None, None)], ids=["int", "str_int", "float", "float_str", "str", "none"])
def test_toInt(var,expected):
    '''Test the conversion to integer'''
    #Convert
    received = ytacommon.toInt(var)
    #Compare
    assert received == expected
# ########################################################################### #
