#!/usr/bin/env python3
''' ytafix - update all wrong artits '''

import os
import sys
import subprocess
import sqlite3
import hashlib
# --------------------------------------------------------------------------- #
def fix(args):
    '''Update artist in database and metadata

    :param args: The command line arguments given by the user
    :type args: list
    '''
    try:
        path = os.path.normpath(os.path.abspath(args[1]))
        if not os.path.isdir(path):
            print("Usage: ytafix DIR ARTIST")
            return
        artist = args[2]
    except (OSError, IndexError):
        print("Usage: ytafix DIR ARTIST")
        return

    #Read filenames and checksums from database
    files = []
    try:
        dbPath = os.path.join(path, "archive.db")
        db = connectDB(dbPath)
        r = db.execute("SELECT creator,filename FROM videos;")
        for f in r.fetchall():
            files.append({"artist" : f[0], "name" : f[1]})
    except sqlite3.Error as e:
        print(e)
        return

    found = False
    for f in files:
        #Compare artist
        if f["artist"] != artist:
            found = True
            filepath = os.path.join(path, f["name"])
            #Update artist
            cmd = ["exiftool", "-api", "largefilesupport=1", "-overwrite_original", "-Artist={}".format(artist), filepath]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            process.wait()
            #Calculate checksums
            sha256 = hashlib.sha256()
            with open(filepath, "rb") as vf:
                for chunk in iter(lambda: vf.read(4096), b""):
                    sha256.update(chunk)
            checksum = sha256.hexdigest()
            #Update database
            db.execute("UPDATE videos SET checksum = ?, creator = ? WHERE filename = ?", (checksum, artist, f["name"]))
            print("File \"{}\" fixed".format(f["name"]))
    if not found:
        print("No files to fix")
    #Close database
    closeDB(db)
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
if __name__ == "__main__":
    try:
        fix(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #

