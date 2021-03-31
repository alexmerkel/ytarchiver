#!/usr/bin/env python3
''' ytarchiver - download and archive youtube videos or playlists '''

import os
import sys
import re
import argparse
import time
import sqlite3
import random
import youtube_dl
from youtube_dl.utils import read_batch_urls as readBatchURLs
from requests.exceptions import RequestException
import ytacommon as yta
import ytainfo
import ytameta

# --------------------------------------------------------------------------- #
def archive(args, parsed=False):
    '''Archive youtube videos or playlists

    :param args: The command line arguments given by the user
    :type args: list
    '''

    #Parse arguments
    if not parsed:
        parser = argparse.ArgumentParser(prog="ytarchiver", description="Download and archive Youtube videos or playlists")
        parser.add_argument("-a", "--all", action="store_const", dest="all", const=True, default=False, help="Run archiver for all subdirectories with archive databases. In this mode, LANG and VIDEO will always be read from the databases")
        parser.add_argument("-c", "--check", action="store_const", dest="check", const="-c", default="", help="Check each file after download")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-s", "--statistics", action="store_const", dest="statistics", const=True, default=False, help="Update the video statistics")
        group.add_argument("-u", "--captions", action="store_const", dest="captions", const=True, default=False, help="List videos where captions were added since archiving (forces -s)")
        group.add_argument("-x", "--amendcaptions", action="store_const", dest="amendcaptions", const=True, default=False, help="Download captions were they were added since archiving (forces -u and consequently -s)")
        parser.add_argument("-r", "--replace", action="store_const", dest="replace", const="-r", default="", help="Replace an existing video (a video ID has to be provided)")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-8k", "--8K", action="store_const", dest="quality", const="8k", help="Limit download resolution to 8K")
        group.add_argument("-4k", "--4K", action="store_const", dest="quality", const="4k", help="Limit download resolution to 4K (default)")
        group.add_argument("-hd", "--HD", action="store_const", dest="quality", const="hd", help="Limit download resolution to full HD")
        parser.add_argument("-V", "--version", action="version", version='%(prog)s {}'.format(yta.__version__))
        parser.add_argument("DIR", help="The directory to work in")
        parser.add_argument("LANG", nargs='?', help="The video language (read from the database if not given)")
        parser.add_argument("-f", "--file", action="store", dest="file", help="Read IDs to archive from a batch file with one ID per line")
        parser.add_argument("VIDEO", nargs='?', help="The Youtube video or playlist ID (read from the database if not given)")
        args = parser.parse_args(args)

        if args.all and args.file:
            parser.error("-a cannot be used in combination with batch file")
        if args.all and args.replace:
            parser.error("-a cannot be used in combination with replace")


    #Check if API key provided
    yta.getAPIKey(True)

    #Archive all subdirectories
    if args.all:
        archiveAll(args)
        return

    #Validate path
    path = os.path.normpath(os.path.abspath(args.DIR))
    if not os.path.isdir(path):
        parser.error("An existing directory must be specified")

    #Check if database exists
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
        else:
            ytainfo.createEmpty(dbPath)

    #Check if database needs upgrade
    yta.upgradeDatabase(dbPath)

    #Check if ID and language are specified
    if not args.LANG or (not args.VIDEO and not args.file):
        #Try reading playlist and language from database
        try:
            (args.LANG, args.VIDEO) = readInfoFromDB(dbPath)
        except (sqlite3.Error, TypeError):
            #Try reading playlist and language from files
            try:
                with open(os.path.join(path, "language"), 'r') as f:
                    args.LANG = f.readline().strip()
                with open(os.path.join(path, "playlist"), 'r') as f:
                    args.VIDEO = f.readline().strip()
            except (IndexError, OSError):
                parser.error("LANG and VIDEO must be specified if no database exists.")

    #Update lastupdate field
    updateTimestamp = int(time.time())
    db = yta.connectDB(dbPath)
    db.execute("UPDATE channel SET lastupdate = ? WHERE id = 1", (updateTimestamp, ))

    #Replace existing video
    if args.replace:
        try:
            youtubeID = db.execute("SELECT youtubeID FROM videos WHERE youtubeID = ?;", (args.VIDEO,)).fetchone()[0]
            assert youtubeID
        except (sqlite3.Error, TypeError, AssertionError):
            print("ERROR: Unable to replace video with ID \"{}\" as it is not in the archive database".format(args.VIDEO))
            return

    #Get format string
    if args.quality:
        q = args.quality
    else:
        q = db.execute("SELECT maxresolution FROM channel WHERE id=1;").fetchone()[0]
    dlformat = yta.getFormatString(q)

    #Close database
    yta.closeDB(db)

    #Prepare download
    dlfilePath = os.path.join(path, "downloaded")
    dbPath = os.path.join(path, "archive.db")
    writeDownloadedFile(dbPath, dlfilePath, args.replace, args.VIDEO)
    dlpath = os.path.join(path, "ID%(id)s&%(title)s.%(ext)s")
    ytapostPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ytapost.py")
    ytapost = "{} {} {} {{}} {}".format(ytapostPath, args.check, args.replace, args.LANG)

    #Set options
    ytdlOpts = {"call_home": False, "quiet": False, "format": dlformat, "ignoreerrors": True, "download_archive": dlfilePath, "writesubtitles": True, "subtitleslangs": [args.LANG], "writedescription": True, "writethumbnail": True, "outtmpl": dlpath, "cachedir": False, "youtube_include_dash_manifest": True, "retries": 10, "fragment_retries": 25, "skip_unavailable_fragments": False, "continuedl": True, }
    ytdlOpts["postprocessors"] = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}, {"key": "FFmpegMetadata"}, {"key": "EmbedThumbnail","already_have_thumbnail": False}, {"key": "ExecAfterDownload", "exec_cmd": ytapost}]

    #Check if archiving one video/playlist or using a batch file
    if args.file:
        with open(args.file, 'r', encoding="utf-8") as f:
            url = readBatchURLs(f)
    else:
        url = [args.VIDEO]

    #Prepare log
    logFile = os.path.join(path, "log")
    #Download
    with DoubleLogger(logFile):
        with youtube_dl.YoutubeDL(ytdlOpts) as ytdl:
            ytdl.download(url)

    #Open database
    db = yta.connectDB(dbPath)

    #Update video number and totalsize
    try:
        db.execute("UPDATE channel SET videos = (SELECT count(id) FROM videos), totalsize = (SELECT sum(filesize) FROM videos) WHERE id = 1;")
    except sqlite3.Error:
        pass

    #Update statistics
    if args.statistics or args.captions or args.amendcaptions:
        print("Updating video statistics...")
        try:
            ytameta.updateStatistics(db, updateTimestamp, args.captions, amendCaptions=args.amendcaptions)
        except yta.NoAPIKeyError:
            print("ERROR: Unable to update video statistics as no API key is available")
        except RequestException as e:
            print("ERROR: Unable to update video statistics due to connection error: \"{}\"".format(e))

    #Close database
    yta.closeDB(db)

    #Remove download archive file
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
    #Set all to false for subsequent calls
    args.all = False

    #Set statistics to false for subsequent calls
    updateStatistics = args.statistics
    updateCaptions = args.captions
    amendCaptions = args.amendcaptions
    args.statistics = False
    args.captions = False
    args.amendcaptions = False

    #Get path
    path = os.path.normpath(os.path.abspath(args.DIR))
    #Get subdirs in path
    subdirs = [os.path.join(path, name) for name in sorted(os.listdir(path), key=str.casefold) if os.path.isdir(os.path.join(path, name))]
    subdirs = [sub for sub in subdirs if os.path.isfile(os.path.join(sub, "archive.db"))]
    if not subdirs:
        print("ERROR: No subdirs with archive databases at \'{}\'".format(path))
        return
    random.shuffle(subdirs)
    #Print message
    channels = len(subdirs)
    if channels > 1:
        print("ARCHIVING ALL {} CHANNELS IN \'{}\'\n".format(channels, path))
    #Initiate error log
    errorLog = ""
    #Loop through all subdirs
    counter = 0
    for subdir in subdirs:
        counter += 1
        name = os.path.basename(os.path.normpath(subdir))
        args.DIR = subdir
        args.LANG = None
        args.VIDEO = None
        print("\nARCHIVING \'{}\' ({}/{})".format(name, counter, channels))
        archive(args, True)
        #Read errors from log
        error = ""
        with open(os.path.join(subdir, "log"), 'r') as f:
            lines = f.readlines()
            for i in range(len(lines)):
                if lines[i].startswith("ERROR"):
                    error += "\n" + lines[i-1] + lines[i]
        if error:
            errorLog += '\n\n' + name + '\n' + error
    #Print error log
    if not errorLog:
        errorLog = "No errors\n"
    logFile = os.path.join(path, "log")
    with open(logFile, 'w+') as f:
        f.writelines(errorLog)

    #Check if statistics is set to autoupdate
    autoUpdateStatistics = False
    if not updateStatistics or updateCaptions:
        try:
            statsDB = yta.connectDB(os.path.join(path, "statistics.db"))
            r = statsDB.execute("SELECT autoupdate FROM setup ORDER BY id DESC LIMIT 1;")
            autoUpdateStatistics = bool(r.fetchone()[0])
            del r
        except sqlite3.Error:
            pass
        finally:
            try:
                yta.closeDB(statsDB)
            except sqlite3.Error:
                pass

    #Update statistics
    if updateStatistics or autoUpdateStatistics or updateCaptions or amendCaptions:
        try:
            ytameta.updateAllStatistics(path, autoUpdateStatistics, updateCaptions, amendCaptions)
        except yta.NoAPIKeyError:
            print("ERROR: Unable to update video statistics as no API key is available")
        except RequestException as e:
            print("ERROR: Unable to update video statistics due to connection error: \"{}\"".format(e))

    print("\nDONE!")
# ########################################################################### #

# --------------------------------------------------------------------------- #
def writeDownloadedFile(dbPath, filePath, replace, videoID):
    '''Write file containing Youtube IDs of all videos already archived

    :param dbPath: Path of the archive database
    :type dbPath: string
    :param filePath: Path where the file containing all existing IDs should be written to
    :type filePath: string
    :param replace: Whether to replace the existing video in the archive database
    :type replace: boolean
    :param videoID: The new video id
    :type videoID: string
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
                if not (replace and videoID == item[0]):
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
class DoubleLogger:
    '''Double logger context
    Get messages to stdout and stderr, print them to stdout and write them to a log
    '''
    def __init__(self, log):
        '''Init

        :param log: Location of the new log file
        :type log: path-like
        '''
        self.oldout = sys.stdout
        self.olderr = sys.stderr
        self.term = sys.stdout
        self.log = open(log, 'w+')
        self.filter = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def __enter__(self):
        '''Enter context, start logging to stdout and log file'''
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''Exit context, restore stdout and stderr'''
        sys.stdout = self.oldout
        sys.stderr = self.olderr
        self.close()

    def write(self, msg):
        '''Write a message to stdout and the log file

        :param msg: The message
        :type msg: string
        '''
        self.term.write(msg)
        self.log.write(self.filter.sub('', msg))

    def flush(self):
        '''Flush the log file'''
        self.log.flush()

    def close(self):
        '''Close the log file'''
        self.log.close()

    @staticmethod
    def isatty():
        '''Answer True to "Is a TTY?" question'''
        return True
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        archive(sys.argv[1:])
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
