#!/usr/bin/env python3
''' ytarchiver - download and archive youtube videos or playlists '''

import os
import sys
import subprocess
import shutil
import sqlite3

# --------------------------------------------------------------------------- #
def archive(args):
    '''Archive youtube videos or playlists

    :param args: The command line arguments given by the user
    :type args: list
    '''

    try:
        #Check files?
        if args[1] == "-c":
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

    if len(args) != 4:
        if len(args) == 3:
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
    cmd = ["youtube-dl", "--ignore-errors", "--download-archive", dlfilePath, "-f", "(bestvideo[width>1920][ext=mp4]/bestvideo[width>1920]/bestvideo[ext=mp4]/bestvideo)+(140/m4a/bestaudio)/best", "--recode-video", "mp4", "--add-metadata", "-o", dlpath, "--embed-thumbnail", "--write-sub", "--sub-lang", args[2], "--write-description", "--exec", "ytapost {} {{}} {} ".format(check, args[2]), args[3]]

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
            db = sqlite3.connect(dbPath)
            #Read IDs of all videos already in archive
            r = db.execute("SELECT youtubeID FROM videos;")
            for item in r.fetchall():
                #Write IDs to file
                f.write("youtube {}\n".format(item[0]))
    except sqlite3.Error:
        return
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        archive(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
