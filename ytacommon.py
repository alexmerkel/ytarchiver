#!/usr/bin/env python3
''' ytacommon - common functions for ytarchiver scripts '''

import os
import sys
import sqlite3
import subprocess
import hashlib
import requests

# --------------------------------------------------------------------------- #
__version__ = "1.2.0"
__dbversion__ = 3
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
        del r
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
                db.execute('ALTER TABLE channel ADD COLUMN dbversion INTEGER NOT NULL DEFAULT 1;')
                #Update db version
                version = 2
                db.execute("UPDATE channel SET dbversion = 2 WHERE id = 1")
                dbCon.commit()
            #Perform upgrade to version 3
            if version < 3:
                #Add language info to each video
                r = db.execute("SELECT language FROM channel ORDER BY id DESC LIMIT 1;")
                lang = r.fetchone()[0]
                del r
                db.execute('ALTER TABLE videos ADD COLUMN language TEXT NOT NULL DEFAULT {};'.format(lang))
                #Add video resolution info
                db.execute('ALTER TABLE videos ADD COLUMN width INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE videos ADD COLUMN height INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE videos ADD COLUMN resolution TEXT NOT NULL DEFAULT "";')
                r = db.execute("SELECT id,filename FROM videos;")
                files = r.fetchall()
                dirname = os.path.dirname(dbPath)
                del r
                for f in files:
                    path = os.path.join(dirname, f[1])
                    _, formatString, width, height = readResolution(path)
                    db.execute("UPDATE videos SET width = ?, height = ?, resolution = ? WHERE id = ?", (width, height, formatString, f[0]))
                #Add maxres to channel
                db.execute('ALTER TABLE channel ADD COLUMN maxresolution NOT NULL DEFAULT "default";')
                #Update db version
                version = 3
                db.execute("UPDATE channel SET dbversion = 3 WHERE id = 1")
                dbCon.commit()
        except sqlite3.Error as e:
            print("ERROR: Unable to upgrade database (\"{}\")".format(e))
            dbCon.rollback()
            closeDB(dbCon)
            sys.exit(1)

    #Close database
    closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def readResolution(path):
    '''Read the resoultion of a video file and return HD indicator
    (0 = SD, 1=720, 2=1080, 3=4K), a format string (e.g. "Full HD", "4K UHD")
    as well as width and height

    :param path: Path to video file
    :type path: string

    :raises: :class:``FileNotFoundError: Unable to find file

    :returns: Tuple with HD indicator, format string, width, and height
    :rtype: touple(int, string, int, int)
    '''
    #Read image width
    if not os.path.isfile(path):
        raise FileNotFoundError
    try:
        cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-ImageWidth", "-ImageHeight", path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        process.wait()
        out = process.stdout.read().decode("UTF-8").splitlines()
        width = int(out[0].split(':', 1)[1].strip())
        height = int(out[1].split(':', 1)[1].strip())
    except IndexError:
        raise FileNotFoundError
    larger = width if width > height else height
    if larger < 1200:
        hd = 0
        formatString = "SD"
    elif 1200 <= larger < 1900:
        hd = 1
        formatString = "HD"
    elif 1900 <= larger < 3500:
        hd = 2
        formatString = "Full HD"
    elif 3500 <= larger < 6000:
        hd = 3
        formatString = "4K UHD"
    else:
        hd = 3
        formatString = "8K UHD"
    return hd, formatString, width, height
# ########################################################################### #
