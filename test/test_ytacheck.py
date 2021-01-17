#!/usr/bin/env python3
''' unit test suite for ytacheck '''

import os
import sqlite3
import pytest

import ytacheck

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.parametrize("mode", [
    pytest.param("channel", marks=pytest.mark.temp_completearchive),
    pytest.param("subdirs", marks=pytest.mark.temp_completeallarchive),
    pytest.param("noarchive", marks=pytest.mark.temp_completearchive),
    pytest.param("noarchivesubs", marks=pytest.mark.temp_completeallarchive)],
    ids=["channel", "subdirs", "noarchiveall", "noarchivesubs"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_ytacheck(request, capsys, mode):
    '''Test checking the videos'''
    #Get path
    path = request.node.get_closest_marker("internal_path").args[0]
    #Switch by mode
    #Test single channel
    if mode == "channel":
        #Prepare
        filenames, checksum = _prepDB(path)
        os.remove(os.path.join(path, filenames[0]))
        _corruptFile(os.path.join(path, filenames[1]))
        #Check videos
        received = ytacheck.check(['-c', path])
        #Compare
        expected = ["ERROR: File \"{}\" missing".format(filenames[0]), "ERROR: File \"{}\" corrupt!".format(filenames[1]),
                   "ERROR: Checksum mismatch for file \"{}\" (New checksum: ".format(filenames[1])]
        for r, e in zip(received, expected):
            assert r.startswith(e)
        db = sqlite3.connect(os.path.join(path, "archive.db"))
        received = db.execute("SELECT checksum FROM videos WHERE id = 3").fetchone()[0]
        db.close()
        assert received == checksum
    elif mode == "subdirs":
        #Prepare
        for i in (1, 2):
            filenames, checksum = _prepDB(os.path.join(path, str(i)), "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")
        #Check videos
        received = ytacheck.check(['-a', path])
        #Compare
        with open(os.path.join(path, "log"), 'r') as f:
            received = [r.strip() for r in f.readlines()]
            received = [r for r in received if r]
        expected = "ERROR: Checksum mismatch for file \"{}\" (New checksum: {})".format(filenames[2], checksum)
        expected = ['1', expected, '2', expected]
        assert received == expected
    elif mode == "noarchive":
        #Prepare
        os.remove(os.path.join(path, "archive.db"))
        #Check
        with pytest.raises(SystemExit):
            ytacheck.check([path])
        #Compare
        captured = capsys.readouterr()
        assert captured.err.strip().endswith("DIR must be a directory containing an archive database")
    elif mode == "noarchivesubs":
        #Prepare
        for i in range(1, 4):
            os.remove(os.path.join(path, str(i), "archive.db"))
        #Check
        ytacheck.check(['-a', path])
        #Compare
        captured = capsys.readouterr()
        assert captured.out.startswith("ERROR: No subdirs with archive databases at")
    else:
        pytest.fail("Unknown mode: {}".format(mode))
# ########################################################################### #

# --------------------------------------------------------------------------- #
def _prepDB(path, newChecksum=''):
    db = sqlite3.connect(os.path.join(path, "archive.db"))
    filenames = db.execute("SELECT filename FROM videos ORDER BY id").fetchall()
    filenames = [f[0] for f in filenames]
    checksum = db.execute("SELECT checksum FROM videos WHERE id = 3").fetchone()[0]
    db.execute("UPDATE videos SET checksum = ? WHERE id = 3", (newChecksum,))
    db.commit()
    db.close()
    return filenames, checksum
# ########################################################################### #

# --------------------------------------------------------------------------- #
def _corruptFile(path):
    with open(path, "rb") as inFile:
        with open(path+".tmp", "wb") as outFile:
            outFile.write(inFile.read()[256:])
    os.remove(path)
    os.rename(path+".tmp", path)
# ########################################################################### #
