#!/usr/bin/env python3
''' ytafix - update all wrong artits '''

import os
import sys
import subprocess
import sqlite3
import requests
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
        dbPath = os.path.join(path, "archive.db")
        db = yta.connectDB(dbPath)
        if len(args) == 3:
            artist = args[2]
        else:
            r = db.execute("SELECT name FROM channel LIMIT 1;")
            (artist, ) = r.fetchone()
            if not artist:
                print("Usage: ytafix DIR ARTIST")
                return
    except (OSError, IndexError, sqlite3.Error):
        print("Usage: ytafix DIR ARTIST")
        return

    #Read filenames and checksums from database
    files = []
    try:
        r = db.execute("SELECT creator,filename,youtubeID FROM videos;")
        for f in r.fetchall():
            files.append({"artist" : f[0], "name" : f[1], "id" : f[2]})
    except sqlite3.Error as e:
        print(e)
        return

    found = False
    for f in files:
        #Compare artist
        if f["artist"] != artist:
            found = True
            filepath = os.path.join(path, f["name"])
            #Get title
            try:
                r = requests.get("https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v=" + f["id"])
                r.raise_for_status()
                d = r.json()
                title = d["title"]
            except requests.exceptions.HTTPError:
                print("ERROR: Unable to fix \"{}\"".format(f["name"]))
                continue
            #Update artist and title
            cmd = ["exiftool", "-api", "largefilesupport=1", "-overwrite_original", "-Artist={}".format(artist), "-Title={}".format(title), filepath]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            process.wait()
            #Calculate checksums
            checksum = yta.calcSHA(filepath)
            #Update database
            db.execute("UPDATE videos SET checksum = ?, creator = ? , title = ? WHERE filename = ?", (checksum, artist, title, f["name"]))
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
