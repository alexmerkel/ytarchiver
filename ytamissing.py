#!/usr/bin/env python3
''' ytamissing - find discrepancies between files and database '''

import os
import sys
import subprocess
import sqlite3
import ytacommon as yta

# --------------------------------------------------------------------------- #
def findMissing(args):
    '''Find discrepancies between files and database

    :param argv: The command line arguments given by the user
    :type argv: list
    '''
    try:
        path = os.path.normpath(os.path.abspath(args[1]))
        if not os.path.isdir(path):
            print("No directory specified")
            return
    except (OSError, IndexError):
        print("No directory specified")
        return
    #Read IDs from file
    fFiles = []
    fIDs = []
    cmd = ["exiftool", "-api", "largefilesupport=1", "-Comment", path]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        line = line.decode("utf-8").strip()
        if line.startswith("Comment"):
            vid = line.split(':', 2)[2].strip()
            fIDs.append(vid)
            fFiles[-1]["id"] = vid
        if line.startswith("=="):
            fFiles.append({"name" : os.path.basename(line.split(' ', 1)[1].strip())})
    if not fIDs:
        print("No videos found in directory")
        return
    #Read IDs from database
    dbPath = os.path.join(path, "archive.db")
    aFiles = []
    try:
        db = yta.connectDB(dbPath)
        r = db.execute("SELECT youtubeID,title FROM videos;")
        for item in r.fetchall():
            #Write ids to list
            aFiles.append({"name" : item[1], "id" : item[0]})
    except sqlite3.Error as e:
        print(e)
        return
    if not aFiles:
        print("No videos found in archive db")
        return
    #Compare IDs
    found = False
    for aFile in aFiles:
        try:
            fIDs.remove(aFile["id"])
        except ValueError:
            found = True
            print("Video file \"{}\" missing (ID: {})".format(aFile["name"], aFile["id"]))
    for fID in fIDs:
        found = True
        fFile = [f for f in fFiles if f["id"] == fID][0]
        print("Video \"{}\" not in database (ID: {})".format(fFile["name"], fFile["id"]))
    if not found:
        print("No discrepancies between files and database")
    #Close db
    yta.closeDB(db)
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        findMissing(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
