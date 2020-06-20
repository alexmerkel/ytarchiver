#!/usr/bin/env python3
''' ytacommon - common functions for ytarchiver scripts '''

import sys
import sqlite3
import hashlib
import requests

# --------------------------------------------------------------------------- #
__version__ = "1.1.0"
__dbversion__ = 2
# ########################################################################### #

# --------------------------------------------------------------------------- #
def connectDB(path):
    '''Connect to a database

    :param path: The path of the database
    :type path: string

    :raises: :class:``sqlite3.Error: Unable to connect to database

    :returns: Connection to the database
    :rtype: sqlite3.Connection
    '''
    #Connect database
    dbCon = sqlite3.connect(path)
    #Return database connection
    return dbCon
# ########################################################################### #

# --------------------------------------------------------------------------- #
def closeDB(dbCon):
    '''Close the connection to a database

    :param dbCon: Connection to the database
    :type dbCon: sqlite3.Connection

    :raises: :class:``sqlite3.Error: Unable to close database
    '''
    if dbCon:
        dbCon.commit()
        dbCon.close()
# ########################################################################### #

# --------------------------------------------------------------------------- #
def calcSHA(path):
    '''Calculate sha256 hash of file

    :param path: Filepath
    :type path: string

    :raises: :class:``IOError: Unable to open file
    '''
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
# ########################################################################### #

# --------------------------------------------------------------------------- #
class color:
    '''Terminal colors'''
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
# ########################################################################### #

# --------------------------------------------------------------------------- #
def loadImage(url):
    '''Download image at url

    :param url: The image url
    :type path: string

    :raises: :class:``requests.exceptions.HTTPError: Unable to load image from URL

    :returns: List with the raw image data at index 0 and the mime type at index 1
    :rtype: list
    '''
    r = requests.get(url, stream=True)
    r.raw.decode_content = True
    r.raise_for_status()
    return[r.raw.data, r.headers['content-type']]
# ########################################################################### #

# --------------------------------------------------------------------------- #
def upgradeDatabase(dbPath):
    '''Check the database version and upgrade it if not newest

    :param dbPath: Path of the archive database
    :type dbPath: string

    :raises: :class:``sqlite3.Error: Unable to read from database
    '''
    #Connect to database
    dbCon = connectDB(dbPath)
    db = dbCon.cursor()
    #Get database version
    try:
        r = db.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
        version = r.fetchone()[0]
    except sqlite3.Error:
        #No version field -> db version 1
        version = 1

    #Check if not uptodate
    if version < __dbversion__:
        print("Upgrading database")
        try:
            #Perform upgrade to version 2
            if version < 2:
                db.execute('ALTER TABLE channel ADD COLUMN videos INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE channel ADD COLUMN lastupdate INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE channel ADD COLUMN dbversion INTEGER NOT NULL DEFAULT {};'.format(__dbversion__))
                #Update db version
                db.execute("UPDATE channel SET dbversion = ? WHERE id = 1", (__dbversion__, ))
                version = 2
        except sqlite3.Error as e:
            print("ERROR: Unable to upgrade database (\"{}\")".format(e))
            dbCon.rollback()
            closeDB(dbCon)
            sys.exit(1)

    #Close database
    closeDB(dbCon)
# ########################################################################### #
