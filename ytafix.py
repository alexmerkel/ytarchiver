#!/usr/bin/env python3
''' ytafix - update all wrong artits '''

import os
import sys
import subprocess
import sqlite3
import ytacommon as yta

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
        db = yta.connectDB(dbPath)
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
            checksum = yta.calcSHA(filepath)
            #Update database
            db.execute("UPDATE videos SET checksum = ?, creator = ? WHERE filename = ?", (checksum, artist, f["name"]))
            print("File \"{}\" fixed".format(f["name"]))
    if not found:
        print("No files to fix")
    #Close database
    yta.closeDB(db)
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        fix(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
