#!/usr/bin/env python3
''' ytacheck - performs integrity checks '''

import os
import sys
import subprocess
import sqlite3
import hashlib

# --------------------------------------------------------------------------- #
def check(args):
    '''Perform integrity checks on files

    :param args: The command line arguments given by the user
    :type args: list
    '''
    try:
        if args[1] == '-c':
            checkFile = True
            args.pop(1)
        else:
            checkFile = False

        path = os.path.normpath(os.path.abspath(args[1]))
        if not os.path.isdir(path):
            print("Usage: ytacheck [-c] DIR")
            return
    except (OSError, IndexError):
        print("Usage: ytacheck [-c] DIR")
        return

    #Read all files in dir
    files = []
    cmd = ["exiftool", "-Comment", path]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        line = line.decode("utf-8").strip()
        if line.startswith("Comment"):
            vid = line.split(':', 2)[2].strip()
            files[-1]["youtubeID"] = vid
        if line.startswith("=="):
            files.append({"name" : os.path.basename(line.split(' ', 1)[1].strip())})
    if not files:
        print("No videos found in directory")
        return
    #Read checksums from database
    try:
        dbPath = os.path.join(path, "archive.db")
        db = connectDB(dbPath)
        for f in files:
            f["checksum"] = db.execute("SELECT checksum FROM videos WHERE youtubeID = ?;", (f["youtubeID"],)).fetchone()[0]
    except sqlite3.Error as e:
        print(e)
        return

    for f in files:
        filepath = os.path.join(path, f["name"])
        #Check movie file
        if checkFile:
            cmd = ["ffmpeg", "-v", "error", "-i", filepath, "-f", "null", "-"]
            out, _ = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
            if out:
                print("ERROR: File \"{}\" corrupt!".format(f["name"]))
            else:
                print("File \"{}\" check passed".format(f["name"]))
        #Calculate checksums
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as vf:
            for chunk in iter(lambda: vf.read(4096), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()

        if not f["checksum"]:
            f["checksum"] = checksum

        if f["checksum"] != checksum:
            print("ERROR: Checksum mismatch for file \"{}\" (New checksum: {})".format(f["name"], checksum))
        else:
            db.execute("UPDATE videos SET filename = ?, checksum = ? WHERE youtubeID = ?", (f["name"], checksum, f["youtubeID"]))
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
        check(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #

