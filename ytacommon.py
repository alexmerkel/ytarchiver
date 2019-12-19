#!/usr/bin/env python3
''' ytacommon - common functions for ytarchiver scripts '''

import sqlite3
import hashlib
import requests

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
