#!/usr/bin/env python3
''' unit test suite for ytamissing '''

import os
import sqlite3
import pytest

import ytamissing

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.parametrize("mode", [
    pytest.param("missing", marks=pytest.mark.temp_completearchive),
    pytest.param("nomissing", marks=pytest.mark.temp_completearchive),
    pytest.param("novidfiles", marks=pytest.mark.temp_completearchive),
    pytest.param("noviddb", marks=pytest.mark.temp_completearchive),
    pytest.param("nodir")],
    ids=["missing", "nomissing", "novidfiles", "noviddb", "nodir"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_findMissing(request, capsys, mode):
    '''Test finding the missing videos'''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    #Switch by mode
    #Test single channel
    if mode == "missing":
        #Prepare
        (idFile, nameFile, idDB, nameDB) = _prepDB(path)
        #Check missing
        ytamissing.findMissing([path])
        #Compare
        captured = capsys.readouterr()
        lines = [l.strip() for l in captured.out.splitlines()]
        expected = ["Video file \"{}\" missing (ID: {})".format(nameFile, idFile), "Video \"{}\" not in database (ID: {})".format(nameDB, idDB)]
        assert lines == expected
    elif mode == "nomissing":
        #Check missing
        ytamissing.findMissing([path])
        #Compare
        captured = capsys.readouterr()
        assert captured.out.strip() == "No discrepancies between files and database"
    elif mode == "novidfiles":
        #Prepare
        files = [os.path.join(path, name) for name in os.listdir(path) if name.endswith(".mp4")]
        for f in files:
            os.remove(f)
        #Compare
        ytamissing.findMissing([path])
        #Compare
        captured = capsys.readouterr()
        assert captured.out.strip() == "No videos found in directory"
    elif mode == "noviddb":
        #Prepare
        _prepDB(path, True)
        #Compare
        ytamissing.findMissing([path])
        #Compare
        captured = capsys.readouterr()
        assert captured.out.strip() == "No videos found in archive db"
    elif mode == "nodir":
        #Compare
        with pytest.raises(SystemExit):
            ytamissing.findMissing(["temp_nonexisting"])
        #Compare
        captured = capsys.readouterr()
        assert captured.err.strip().endswith("DIR must be a directory")
# ########################################################################### #

# --------------------------------------------------------------------------- #
def _prepDB(path, delAll=False):
    db = sqlite3.connect(os.path.join(path, "archive.db"))
    idFile, fFile, nameFile = db.execute("SELECT youtubeID,filename,title FROM videos WHERE id=1").fetchone()
    os.remove(os.path.join(path, fFile))
    idDB, nameDB = db.execute("SELECT youtubeID,filename FROM videos WHERE id=3").fetchone()
    if delAll:
        db.execute("DELETE FROM videos")
    else:
        db.execute("DELETE FROM videos WHERE id=3")
    db.commit()
    db.close()
    return (idFile, nameFile, idDB, nameDB)
# ########################################################################### #
