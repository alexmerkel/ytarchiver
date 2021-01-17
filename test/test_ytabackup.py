#!/usr/bin/env python3
''' unit test suite for ytabackup '''

import os
import time
import pytest

import ytabackup

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("mode", [
    pytest.param("channel", marks=pytest.mark.temp_archive),
    pytest.param("subdirs", marks=pytest.mark.temp_allarchive)],
    ids=["channel", "subdirs"])
@pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "dbversions", os.environ["YTA_TEST_LATESTDB"]))
def test_backup(request, mode):
    '''Test the backup creation'''
    #Prepare
    path = request.node.get_closest_marker("internal_path").args[0]
    args = ['-a', path] if mode == "subdirs" else [path]
    backupDir = os.path.join(path, "backups")
    #Create backup(s)
    t1 = int(time.time())
    ytabackup.backup(args)
    t2 = int(time.time())
    #Test backup of a single channel
    if mode == "channel":
        assert _backupInDir(backupDir, t1, t2)
    #Test backup of all channels in subdirs
    elif mode == "subdirs":
        channels = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name)) and name != "backups" ]
        for channel in channels:
            channelDir = os.path.join(backupDir, channel)
            assert _backupInDir(channelDir, t1, t2)
    else:
        pytest.fail("Unknown mode: {}".format(mode))
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("expected", [
    pytest.param(True, marks=pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "subtest.db"))),
    pytest.param(False, marks=pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "malformed.db")))],
    ids=["healthy", "malformed"])
def test_backupDB(request, capsys, tempdir, tempcopy, expected):
    '''Test the backup creation'''
    #Prepare
    dbPath = request.node.get_closest_marker("internal_path").args[0]
    backupDir = request.node.get_closest_marker("internal_path2").args[0]
    #Create backup
    t1 = int(time.time())
    received = ytabackup.backupDB(dbPath, backupDir)
    t2 = int(time.time())
    #Compare
    assert expected == received
    #Check ZIP was created
    if received:
        assert _backupInDir(backupDir, t1, t2)
    #Check error message
    else:
        captured = capsys.readouterr()
        assert "has integrity error" in captured.out
# ########################################################################### #

# --------------------------------------------------------------------------- #
def _backupInDir(path, t1, t2):
    for i in range (t1, t2+1):
        if os.path.isfile(os.path.join(path, "{}.db.zip".format(i))):
            return i
    return None
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("expected", [
    pytest.param(True, marks=pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "subtest.db"))),
    pytest.param(False, marks=pytest.mark.internal_path(os.path.join(os.environ["YTA_TESTDATA"], "malformed.db")))],
    ids=["healthy", "malformed"])
def test_checkDB(dbCon, expected):
    '''Test the database integrity checker'''
    received = ytabackup.checkDB(dbCon)
    assert received == expected
# ########################################################################### #
