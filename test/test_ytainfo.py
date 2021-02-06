#!/usr/bin/env python3
''' unit test suite for ytainfo '''

import os
import sqlite3

import ytainfo

# --------------------------------------------------------------------------- #
def test_createEmpty(request, tempdir):
    ''' Test createEmpty '''
    #Get path
    path = request.node.get_closest_marker("internal_path2").args[0]
    dbPath = os.path.join(path, "archive.db")
    #Create
    ytainfo.createEmpty(dbPath)
    #Read db
    db = sqlite3.connect(dbPath)
    rec = db.execute("SELECT name,dbversion FROM channel WHERE id=1").fetchone()
    db.close()
    #Compare
    assert rec[0] == ''
    assert isinstance(rec[1], int) and rec[1] > 0
# ########################################################################### #
