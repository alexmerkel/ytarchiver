#!/usr/bin/env python3
''' ytafix - update all wrong artists '''

import os
import sys
import argparse
import subprocess
import sqlite3
import requests
import ytacommon as yta

# --------------------------------------------------------------------------- #
def fix(args, parsed=False):
    '''Update artist in database and metadata

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Parse arguments
    if not parsed:
        parser = argparse.ArgumentParser(prog="ytafix", description="Fix wrong artist information")
        parser.add_argument("-a", "--all", action="store_const", dest="all", const=True, default=False, help="Run fixer for all subdirectories with archive databases. In this mode, the ARTIST will always be read from the database")
        parser.add_argument("DIR", help="The directory to work in")
        parser.add_argument("ARTIST", nargs='?', help="The correct artist name (read from the database if not given)")
        args = parser.parse_args(args)

    #Run fixer for all subdirectories
    if args.all:
        fixAll(args)
        return

    #Validate path
    path = os.path.normpath(os.path.abspath(args.DIR))
    dbPath = os.path.join(path, "archive.db")
    if not os.path.isdir(path) or not os.path.isfile(dbPath):
        parser.error("DIR must be a directory containing an archive database")

    #Check if database needs upgrade
    yta.upgradeDatabase(dbPath)

    #Connect to database
    db = yta.connectDB(dbPath)

    #Get correct artist
    if args.ARTIST:
        artist = args.ARTIST
    else:
        try:
            r = db.execute("SELECT name FROM channel LIMIT 1;")
            (artist, ) = r.fetchone()
            del r
            if not artist:
                raise sqlite3.Error
        except sqlite3.Error:
            parser.error("No correct artist specified and unable to read it from the database")


    #Read filenames and checksums from database
    files = []
    try:
        r = db.execute("SELECT creator,filename,youtubeID FROM videos;")
        for f in r.fetchall():
            files.append({"artist" : f[0], "name" : f[1], "id" : f[2]})
        del r
    except sqlite3.Error as e:
        print(e)
        return

    found = False
    for f in files:
        #Compare artist
        if f["artist"] != artist:
            found = True
            filepath = os.path.join(path, f["name"])
            try:
                #Change meta data
                artist, title = fixVideo(filepath, f["id"], artist)
                #Calculate checksums
                checksum = yta.calcSHA(filepath)
                #Update database
                db.execute("UPDATE videos SET checksum = ?, creator = ? , title = ? WHERE youtubeID = ?", (checksum, artist, title, f["id"]))
            except requests.exceptions.HTTPError:
                print("ERROR: Unable to fix \"{}\"".format(f["name"]))
                continue
            print("File \"{}\" fixed".format(f["name"]))
    if not found:
        print("No files to fix")
    #Close database
    yta.closeDB(db)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def fixVideo(path, videoID, correctArtist=None, fileArtist=None):
    '''Fix a video

    :param path: The filepath
    :type path: string
    :param videoID: The video ID
    :type videoID: string
    :param correctArtist: The correct artist name (Optional, read from the JSON if not given)
    :type correctArtist: string
    :param fileArtist: The artist name to compare the one correct one to (Optional, if not given, the new artist and title will always be saved)
    :type fileArtist: string

    :raises: :class:``requests.exceptions.HTTPError: Unable to get title

    :returns: Tuple with new metadata (artist, title)
    :rtype: tuple(string, string)
    '''
    #Get title
    r = requests.get("https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v=" + videoID)
    r.raise_for_status()
    d = r.json()
    title = d["title"]
    if not correctArtist:
        correctArtist = d["author_name"]
    #Update artist and title
    if not fileArtist or fileArtist != correctArtist:
        cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-overwrite_original", "-Artist={}".format(correctArtist), "-Title={}".format(title), "-Album=", path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        process.wait()
    #Return new metadata
    return(correctArtist, title)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def fixAll(args):
    '''Call fix script for all subdirs

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Get path
    path = os.path.normpath(os.path.abspath(args.DIR))
    args.all = False
    args.ARTIST = None
    #Get subdirs in path
    subdirs = [os.path.join(path, name) for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    subdirs = [sub for sub in subdirs if os.path.isfile(os.path.join(sub, "archive.db"))]
    if not subdirs:
        print("ERROR: No subdirs with archive databases at \'{}\'".format(path))
        return
    #Loop through all subdirs
    print("FIXING ALL CHANNELS IN \'{}\'\n".format(path))
    for subdir in subdirs:
        name = os.path.basename(os.path.normpath(subdir))
        print("\nFIXING \'{}\'".format(name))
        args.DIR = subdir
        fix(args, True)
    print("\nDONE!")
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        fix(sys.argv[1:])
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
