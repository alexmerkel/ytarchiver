#!/usr/bin/env python3
''' test suite for ytarchiver '''

import os
import sqlite3
import time
import pytest

import ytarchiver

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_yta_one(request, temparchive):
    ''' Test downloading one new video '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    dbPath = os.path.join(path, "archive.db")
    #Modify database
    db = sqlite3.connect(dbPath)
    dbID, expYoutubeID, expTitle = db.execute("SELECT id,youtubeID, title FROM videos WHERE id = (SELECT MAX(id) FROM videos);").fetchone()
    db.execute("DELETE FROM videos WHERE id = ?;", (dbID,))
    db.commit()
    db.close()
    #Download video
    t1 = int(time.time())
    ytarchiver.archive(['-hd', path])
    t2 = int(time.time())
    #Read database
    db = sqlite3.connect(dbPath)
    recYoutubeID, recTitle, recRes = db.execute("SELECT youtubeID, title, resolution FROM videos WHERE id = (SELECT MAX(id) FROM videos);").fetchone()
    recUpdate = db.execute("SELECT lastupdate FROM channel WHERE id=1;").fetchone()[0]
    db.close()
    #Compare
    assert recYoutubeID == expYoutubeID
    assert recTitle == expTitle
    assert recRes == "Full HD"
    assert t1 <= recUpdate <= t2
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_yta_stat(request, temparchive):
    ''' Test updating the statistics '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    dbPath = os.path.join(path, "archive.db")
    #Update statistics
    t1 = int(time.time())
    ytarchiver.archive(['-s', path])
    t2 = int(time.time())
    #Read database
    db = sqlite3.connect(dbPath)
    recStats = [i[0] for i in db.execute("SELECT statisticsupdated FROM videos;").fetchall()]
    db.close()
    #Compare
    for r in recStats:
        assert t1 <= r <= t2
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_yta_caps(request, capsys, temparchive):
    ''' Test checking and amending the captions '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    dbPath = os.path.join(path, "archive.db")
    #Prepare database
    db = sqlite3.connect(dbPath)
    expID, expTitle, expCap = db.execute("SELECT youtubeID,title,subtitles FROM videos WHERE id=1;").fetchone()
    db.execute("UPDATE videos SET subtitles=? WHERE id=1;", (None,))
    db.commit()
    db.close()
    #Check subtitles
    ytarchiver.archive(['-u', path])
    captured = capsys.readouterr()
    #Compare
    assert "INFO: Video [{}] \"{}\" had captions added since archiving".format(expID, expTitle) in captured.out
    #Amend subtitles
    ytarchiver.archive(['-x', path])
    captured = capsys.readouterr()
    db = sqlite3.connect(dbPath)
    recCap = db.execute("SELECT subtitles FROM videos WHERE id=1;").fetchone()[0]
    db.close()
    #Compare
    assert "INFO: Added subtitle \"{}\" for video \"{}\" to the database".format("en", expID) in captured.out
    assert expCap == recCap
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_yta_replace(request, temparchive):
    ''' Test video replacement '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    dbPath = os.path.join(path, "archive.db")
    #Prepare database
    db = sqlite3.connect(dbPath)
    expID, expName = db.execute("SELECT youtubeID,filename FROM videos WHERE id=1;").fetchone()
    db.close()
    filePath = os.path.join(path, expName)
    #Check subtitles
    ytarchiver.archive(['-r', path, "en", expID])
    #Compare
    assert os.path.isfile(filePath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_yta_file(request, temparchive):
    ''' Test downloading from file '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    dbPath = os.path.join(path, "archive.db")
    filePath = os.path.join(path, "file")
    expIDs = ["m-PGIQ6uwvk", "BBoaQvZOoFk"]
    #Prepare file
    with open(filePath, 'w') as f:
        f.write('\n'.join(expIDs))
    #Check subtitles
    ytarchiver.archive([path, "en", '-f', filePath])
    #Compare
    db = sqlite3.connect(dbPath)
    recIDs = [i[0] for i in db.execute("SELECT youtubeID FROM videos").fetchall()]
    db.close()
    for i in expIDs:
        assert i in recIDs
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_yta_all_one(request, tempallarchive):
    ''' Test downloading one new video for a dir of archives '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    #Modify database
    exp = []
    for i in range(1,3):
        db = sqlite3.connect(os.path.join(path, str(i), "archive.db"))
        exp.append(db.execute("SELECT youtubeID,title FROM videos WHERE id=?;", (i,)).fetchone())
        db.execute("DELETE FROM videos WHERE id = ?;", (i,))
        db.commit()
        db.close()
    #Download video
    t1 = int(time.time())
    ytarchiver.archive(['-a', '-hd', path])
    t2 = int(time.time())
    #Read database
    rec = []
    recUpdate = []
    for i in range(1,3):
        db = sqlite3.connect(os.path.join(path, str(i), "archive.db"))
        rec.append(db.execute("SELECT youtubeID,title FROM videos WHERE id = (SELECT MAX(id) FROM videos);").fetchone())
        recUpdate.append(db.execute("SELECT lastupdate FROM channel WHERE id=1;").fetchone()[0])
        db.close()
    #Compare
    assert rec == exp
    for r in recUpdate:
        assert t1 <= r <= t2
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_yta_all_stat(request, tempallarchive):
    ''' Test updating the statistics for a dir of archives '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    #Update statistics
    t1 = int(time.time())
    ytarchiver.archive(['-a', '-s', path])
    t2 = int(time.time())
    #Read database
    recStats = []
    for i in range(1,4):
        db = sqlite3.connect(os.path.join(path, str(i), "archive.db"))
        recStats += [i[0] for i in db.execute("SELECT statisticsupdated FROM videos;").fetchall()]
        db.close()
    #Compare
    for r in recStats:
        assert t1 <= r <= t2
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_yta_all_caps(request, capsys, tempallarchive):
    ''' Test amending the captions for a dir of archives '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    #Prepare database
    exp = []
    for i in range(1,4):
        dbID = (i*2)-1
        db = sqlite3.connect(os.path.join(path, str(i), "archive.db"))
        exp.append(db.execute("SELECT youtubeID,subtitles FROM videos WHERE id=?;", (dbID,)).fetchone())
        db.execute("UPDATE videos SET subtitles=? WHERE id=?;", (None,dbID))
        db.commit()
        db.close()
    #Amend subtitles
    ytarchiver.archive(['-a', '-x', path])
    captured = capsys.readouterr()
    #Read database
    rec = []
    for i in range(1,4):
        dbID = (i*2)-1
        db = sqlite3.connect(os.path.join(path, str(i), "archive.db"))
        rec.append(db.execute("SELECT subtitles FROM videos WHERE id=?;", (dbID,)).fetchone()[0])
        db.close()
    #Compare
    for e in exp:
        assert "INFO: Added subtitle \"{}\" for video \"{}\" to the database".format("en", e[0]) in captured.out
        assert e[1] in rec
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_writeDownloadedFile(request, tempdir, tempcopy):
    ''' Test writeDownloadedFile '''
    #Get path
    dbPath = request.node.get_closest_marker("internal_path").args[0]
    dirPath = request.node.get_closest_marker("internal_path2").args[0]
    filePath = os.path.join(dirPath, "down")
    #Read database
    db = sqlite3.connect(dbPath)
    ids = [i[0] for i in db.execute("SELECT youtubeID FROM videos;").fetchall()]
    db.close()
    #Test no replace
    exp = ["youtube {}".format(i) for i in ids]
    ytarchiver.writeDownloadedFile(dbPath, filePath, False, "UUsiMuEX8d_OnJe3u8i4FiqQ")
    #Compare
    with open(filePath) as f:
        rec = [l.strip() for l in f.readlines()]
    assert exp == rec
    #Test with replace
    exp = ["youtube {}".format(i) for i in ids[1:]]
    ytarchiver.writeDownloadedFile(dbPath, filePath, True, ids[0])
    #Compare
    with open(filePath) as f:
        rec = [l.strip() for l in f.readlines()]
    assert exp == rec
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_readInfoFromDB(request, tempcopy):
    ''' Test readInfoFromDB '''
    #Get path
    dbPath = request.node.get_closest_marker("internal_path").args[0]
    exp = ["en", "UUsiMuEX8d_OnJe3u8i4FiqQ"]
    #Read
    rec = ytarchiver.readInfoFromDB(dbPath)
    #Compare
    assert exp == rec
# ########################################################################### #
