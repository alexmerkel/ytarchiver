#!/usr/bin/env python3
''' ytarchiver - download and archive youtube videos or playlists '''

import os
import sys
import subprocess
import shutil
import sqlite3
import ytacommon as yta
import ytainfo

# --------------------------------------------------------------------------- #
def archive(args):
    '''Archive youtube videos or playlists

    :param args: The command line arguments given by the user
    :type args: list
    '''

    try:
        #All subdirs
        if args[1] == "-a":
            archiveAll(args)
            return
        #Check files?
        elif args[1] == "-c":
            check = "-c"
            args.pop(1)
        else:
            check = ""
        #Get directory path
        path = os.path.normpath(os.path.abspath(args[1]))
        if not os.path.isdir(path):
            print("Usage: ytarchiver DIR SUBLANG YOUTUBEID")
            return
    except IndexError:
        print("Usage: ytarchiver DIR SUBLANG YOUTUBEID")
        return

    dbPath = os.path.join(path, "archive.db")
    if not os.path.isfile(dbPath):
        #No database found, ask to create one
        while True:
            q = input("New archive. Populate with channel info? [Y|n] ")
            if not q:
                q = 'y'
            a = q[0].lower()
            if a in ['y', 'n']:
                break
        if a == 'y':
            ytainfo.add(dbPath)

    if len(args) != 4:
        if len(args) == 2:
            #Try reading playlist and language from database
            try:
                args += readInfoFromDB(dbPath)
            except sqlite3.Error:
                #Try reading playlist and language from files
                try:
                    with open(os.path.join(path, "language"), 'r') as f:
                        args.append(f.readline().strip())
                    with open(os.path.join(path, "playlist"), 'r') as f:
                        args.append(f.readline().strip())
                except (IndexError, OSError):
                    print("Usage: ytarchiver DIR SUBLANG YOUTUBEID")
                    return
        elif len(args) == 3:
            try:
                with open(os.path.join(path, "playlist"), 'r') as f:
                    args.append(f.readline().strip())
            except (IndexError, OSError):
                print("Usage: ytarchiver DIR SUBLANG YOUTUBEID")
                return
        else:
            print("Usage: ytarchiver DIR SUBLANG YOUTUBEID")
            return

    dlfilePath = os.path.join(path, "downloaded")
    dbPath = os.path.join(path, "archive.db")
    writeDownloadedFile(dbPath, dlfilePath)
    dlpath = os.path.join(path, "ID%(id)s&%(title)s.%(ext)s")
    dlformat = "(bestvideo[width<4000][width>1920][ext=mp4]/bestvideo[width<4000][width>1920]/bestvideo[width>1920][ext=mp4]/bestvideo[width>1920]/bestvideo[ext=mp4]/bestvideo)+(140/m4a/bestaudio)/best"
    cmd = ["youtube-dl", "--ignore-errors", "--download-archive", dlfilePath, "-f", dlformat, "--recode-video", "mp4", "--add-metadata", "-o", dlpath, "--embed-thumbnail", "--write-sub", "--sub-lang", args[2], "--write-description", "--exec", "ytapost {} {{}} {} ".format(check, args[2]), args[3]]

    logFile = os.path.join(path, "log")
    with open(logFile, 'w+') as f:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while p.poll() is None:
            line = p.stdout.readline().decode("utf-8")
            print(line, end='')
            f.write(line)
        line = p.stdout.read().decode("utf-8")
        f.write(line)
        print(line, end='')
        p.wait()

    try:
        os.remove(dlfilePath)
    except OSError:
        pass
# ########################################################################### #

# --------------------------------------------------------------------------- #
def archiveAll(args):
    '''Call archive script for all subdirs

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Remove "-a" from args
    args.pop(1)
    a = ["ytarchiver.py"]
    if args[1] == "-c":
        a.append("-c")
        args.pop(1)
    #Get path
    path = os.path.normpath(os.path.abspath(args[1]))
    #Get subdirs in path
    subdirs = [os.path.join(path, name) for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    subdirs = [sub for sub in subdirs if os.path.isfile(os.path.join(sub, "archive.db"))]
    if not subdirs:
        print("ERROR: No subdirs with archive databases at \'{}\'".format(path))
        return
    #Loop through all subdirs
    for subdir in subdirs:
        print("\nARCHIVING \'{}\'".format(subdir))
        archive(a + [subdir])
    print("\nDONE!")
# ########################################################################### #

# --------------------------------------------------------------------------- #
def writeDownloadedFile(dbPath, filePath):
    '''Write file containing Youtube IDs of all videos already archived

    :param dbPath: Path of the archive database
    :type dbPath: string
    :param filePath: Path where the file containing all existing IDs should be written to
    :type filePath: string
    '''
    #Check if db exists
    if not os.path.isfile(dbPath):
        return
    try:
        with open(filePath, 'w+') as f:
            #Connect to database
            db = yta.connectDB(dbPath)
            #Read IDs of all videos already in archive
            r = db.execute("SELECT youtubeID FROM videos;")
            for item in r.fetchall():
                #Write IDs to file
                f.write("youtube {}\n".format(item[0]))
            yta.closeDB(db)
    except sqlite3.Error:
        return
# ########################################################################### #

# --------------------------------------------------------------------------- #
def readInfoFromDB(dbPath):
    '''Read playlist and language from database

    :param dbPath: Path of the archive database
    :type dbPath: string

    :raises: :class:``sqlite3.Error: Unable to read from database

    :returns: List with language code at index 0 and playlist at index 1
    :rtype: list of string
    '''
    db = yta.connectDB(dbPath)
    r = db.execute("SELECT language,playlist FROM channel ORDER BY id DESC LIMIT 1;")
    item = r.fetchone()
    yta.closeDB(db)
    return [item[0], item[1]]
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        archive(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
