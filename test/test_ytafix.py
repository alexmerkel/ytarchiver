#!/usr/bin/env python3
''' unit test suite for ytafix '''

import os
import sqlite3
import subprocess
import pytest

import ytafix

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.parametrize("mode", [
    pytest.param("channel", marks=pytest.mark.temp_completearchive),
    pytest.param("subdirs", marks=pytest.mark.temp_completeallarchive),
    pytest.param("noarchive", marks=pytest.mark.temp_completearchive),
    pytest.param("noarchivesubs", marks=pytest.mark.temp_completeallarchive)],
    ids=["channel", "subdirs", "noarchive", "noarchivesubs"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_fixFunc(request, capsys, mode):
    '''Test fixing the videos'''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    #Switch by mode
    #Test single channel
    if mode == "channel":
        #Prepare database
        filenames, _ = _prepDB(path)
        db = sqlite3.connect(os.path.join(path, "archive.db"))
        expTitle = db.execute("SELECT title FROM videos WHERE id=2").fetchone()[0]
        db.execute("UPDATE videos SET title=? WHERE id=2", ("TestTitle",))
        db.close()
        #Set expected
        filepath = os.path.join(path, filenames[1])
        expArtist = "TestArtist"
        #Fix
        ytafix.fix([path, expArtist])
        #Read results
        db = sqlite3.connect(os.path.join(path, "archive.db"))
        recDB = db.execute("SELECT creator,title FROM videos").fetchall()
        db.close()
        recArtist, recTitle = _readArtistTitle(filepath)
        #Compare
        for rec in recDB:
            assert rec[0] == expArtist
        assert recDB[1][1] == expTitle
        assert recArtist == expArtist
        assert recTitle == expTitle
    #Test multiple channels in subdirs
    elif mode == "subdirs":
        #Prepare
        expArtist = "ytarchiver test"
        db = sqlite3.connect(os.path.join(path, "1", "archive.db"))
        db.execute("UPDATE videos SET creator=?", ("TestArtists",))
        db.commit()
        db.close()
        db = sqlite3.connect(os.path.join(path, "2", "archive.db"))
        expTitles = [i[0] for i in db.execute("SELECT title FROM videos").fetchall()]
        expArtists = [expArtist + " 1"] * len(expTitles)
        db.execute("UPDATE videos SET title=?", ("TestTitle",))
        db.commit()
        db.close()
        db = sqlite3.connect(os.path.join(path, "3", "archive.db"))
        db.execute("UPDATE videos SET creator=?", (expArtist + " 3",))
        db.commit()
        db.close()
        #Fix
        ytafix.fix(['-a', path])
        #Get results
        captured = capsys.readouterr()
        db = sqlite3.connect(os.path.join(path, "1", "archive.db"))
        recArtists = [i[0] for i in db.execute("SELECT creator FROM videos").fetchall()]
        db.close()
        db = sqlite3.connect(os.path.join(path, "2", "archive.db"))
        recTitles = [i[0] for i in db.execute("SELECT title FROM videos").fetchall()]
        db.close()
        #Compare
        assert not bool(set(recArtists).difference(expArtists))
        assert not bool(set(recTitles).difference(expTitles))
        assert "No files to fix" in captured.out
    #Test error no archive database
    elif mode == "noarchive":
        #Prepare
        dbPath = os.path.join(path, "archive.db")
        db = sqlite3.connect(dbPath)
        db.execute("UPDATE channel SET name=? WHERE id=1", ('',))
        db.commit()
        db.close()
        #Fix
        with pytest.raises(SystemExit):
            ytafix.fix([path])
        #Compare
        captured = capsys.readouterr()
        assert captured.err.strip().endswith("No correct artist specified and unable to read it from the database")
        #Prepare
        os.remove(dbPath)
        #Fix
        with pytest.raises(SystemExit):
            ytafix.fix([path])
        #Compare
        captured = capsys.readouterr()
        assert captured.err.strip().endswith("DIR must be a directory containing an archive database")
    #Test error no subdirs with archive database
    elif mode == "noarchivesubs":
        #Prepare
        for i in range(1, 4):
            os.remove(os.path.join(path, str(i), "archive.db"))
        #Fix
        ytafix.fix(['-a', path])
        #Compare
        captured = capsys.readouterr()
        assert captured.out.startswith("ERROR: No subdirs with archive databases at")
    #Unknown mode
    else:
        pytest.fail("Unknown mode: {}".format(mode))
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.temp_completearchive
@pytest.mark.parametrize("mode",
    ["unchanged", "given", "fetched"],
    ids=["unchanged", "given", "fetched"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_fixVideo(request, mode):
    ''' Test fixVideo '''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    #Read database
    filenames, youtubeIDs = _prepDB(path)
    filepath = os.path.join(path, filenames[0])
    #Switch by mode
    #Test no changes
    if mode == "unchanged":
        #Read expected artist and title from file
        expArtist, expTitle = _readArtistTitle(filepath)
        #Call fixVideo
        recArtist, recTitle = ytafix.fixVideo(filepath, youtubeIDs[0])
        #Compare
        assert expArtist == recArtist
        assert expTitle == recTitle
    #Test setting a given name
    elif mode == "given":
        expArtist = "TestArtist"
        #Read expected title from file
        _, expTitle = _readArtistTitle(filepath)
        #Call fixVideo
        rec1Artist, rec1Title = ytafix.fixVideo(filepath, youtubeIDs[0], expArtist)
        #Read new artist and title from file
        rec2Artist, rec2Title = _readArtistTitle(filepath)
        #Compare
        assert expArtist == rec1Artist
        assert expTitle == rec1Title
        assert expArtist == rec2Artist
        assert expTitle == rec2Title
    elif mode == "fetched":
        #Read expected artist and title from file
        expArtist, expTitle = _readArtistTitle(filepath)
        #Call fixVideo
        rec1Artist, rec1Title = ytafix.fixVideo(filepath, youtubeIDs[0], fileArtist="TestArtist")
        #Read new artist and title from file
        rec2Artist, rec2Title = _readArtistTitle(filepath)
        #Compare
        assert expArtist == rec1Artist
        assert expTitle == rec1Title
        assert expArtist == rec2Artist
        assert expTitle == rec2Title
    #Unknown mode
    else:
        pytest.fail("Unknown mode: {}".format(mode))
# ########################################################################### #

# --------------------------------------------------------------------------- #
def _prepDB(path):
    db = sqlite3.connect(os.path.join(path, "archive.db"))
    data = db.execute("SELECT filename,youtubeID FROM videos ORDER BY id").fetchall()
    filenames = [i[0] for i in data]
    youtubeIDs = [i[1] for i in data]
    db.close()
    return filenames, youtubeIDs
# ########################################################################### #

# --------------------------------------------------------------------------- #
def _readArtistTitle(path):
    #Read artist, title
    cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-Artist", path]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    artist = process.stdout.read().decode("UTF-8").split(':', 1)[1].strip()
    cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-Title", path]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    title = process.stdout.read().decode("UTF-8").split(':', 1)[1].strip()
    return artist, title
# ########################################################################### #
