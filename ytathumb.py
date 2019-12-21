#!/usr/bin/env python3
''' ytathumb - add video thumbnails to archive database '''

import os
import sys
import subprocess
import sqlite3
import requests
import ytacommon as yta

# --------------------------------------------------------------------------- #
def addThumbnails(args):
    '''Add thumbnail to archive database

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Get database path
    try:
        path = os.path.normpath(os.path.abspath(args[1]))
        dbPath = os.path.join(path, "archive.db")
        if not os.path.isdir(path) or not os.path.isfile(dbPath):
            print("Usage: ytathumb DIR")
            return
    except (OSError, IndexError):
        print("Usage: ytathumb DIR")
        return
    #Connect to database
    dbCon = yta.connectDB(dbPath)
    db = dbCon.cursor()
    #Modify database
    modifyDatabase(db)
    #Save thumbnails to database
    r = db.execute("SELECT youtubeID FROM videos;")
    for item in r.fetchall():
        #Get video filepath
        youtubeID = item[0]
        url = "https://i.ytimg.com/vi/{}/maxresdefault.jpg".format(youtubeID)
        try:
            [thumbData, thumbFormat] = yta.loadImage(url)
            db.execute("UPDATE videos SET thumb = ?, thumbformat = ? WHERE youtubeID = ?", (thumbData, thumbFormat, youtubeID))
        except requests.exceptions.HTTPError:
            url = "https://i.ytimg.com/vi/{}/hqdefault.jpg".format(youtubeID)
            try:
                print("WARNING: Unable to download highres thumbnail for {}, getting lower res".format(youtubeID))
                [thumbData, thumbFormat] = yta.loadImage(url)
                db.execute("UPDATE videos SET thumb = ?, thumbformat = ? WHERE youtubeID = ?", (thumbData, thumbFormat, youtubeID))
            except requests.exceptions.HTTPError:
                print("ERROR: Unable to download image for {} ({})".format(youtubeID, url))
                continue
    #Close database
    yta.closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def modifyDatabase(db):
    '''Add thumbnail and thumbnailformat columns to videos table of they
    don't exist already

    :param db: Connection to the metadata database
    :type db: sqlite3.Cursor
    '''
    try:
        db.execute('ALTER TABLE videos ADD COLUMN thumb BLOB;')
        db.execute('ALTER TABLE videos ADD COLUMN thumbformat TEXT;')
    except sqlite3.Error:
        pass
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        addThumbnails(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
