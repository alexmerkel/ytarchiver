#!/usr/bin/env python3
''' ytapost - youtube archiver post processing steps '''

import os
import sys
import subprocess
import argparse
import shutil
import sqlite3
import json
import time
from datetime import datetime, timezone
from pycountry import languages
import ytacommon as yta
import ytameta
import ytafix

# --------------------------------------------------------------------------- #
def postprocess(args):
    '''Postprocess a video file or a directory of video files

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Get files
    files = []
    parser = argparse.ArgumentParser(prog="ytapost", description="Perform the postprocessing steps on a downloaded video file")
    parser.add_argument("-c", "--check", action="store_const", dest="check", const=True, default=False, help="Check file integrity")
    parser.add_argument("-r", "--replace", action="store_const", dest="replace", const=True, default=False, help="Replace existing file")
    parser.add_argument("PATH", help="The file or the directory to work with")
    parser.add_argument("LANG", nargs='?', default="", help="The video language")
    args = parser.parse_args()

    path = os.path.normpath(os.path.abspath(args.PATH))
    if os.path.isfile(path):
        dirPath = os.path.dirname(path)
        if path.lower().endswith((".m4v", ".mp4")):
            files.append(path)
        else:
            parser.error("Unsupported file format, only .mp4 and .m4v are supported")
    elif os.path.isdir(path):
        dirPath = path
        allf = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        for f in allf:
            if f.lower().endswith((".m4v", ".mp4")):
                files.append(os.path.join(path, f))
        if not files:
            parser.error("No supported files in directory, only .mp4 and .m4v are supported")

    #Connect to database
    try:
        dbFile = os.path.join(dirPath, "archive.db")
        dbCon = createOrConnectDB(dbFile)
        db = dbCon.cursor()
    except sqlite3.Error as e:
        print(e)
        return

    for f in files:
        processFile(f, args.LANG, db, args.check, args.replace)

    yta.closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def processFile(name, subLang, db, check, replace):
    '''Process a file

    :param name: The video file name
    :type name: string
    :param subLang: The subtitle language identifier
    :type subLang: string
    :param db: Connection to the metadata database
    :type db: sqlite3.Cursor
    :param check: Whether to perform an integrity check and calc the checksum
    :type check: boolean
    :param replace: Whether to replace a video already in the archive database
    :type replace: boolean

    :raises: :class:``sqlite3.Error: Unable to write to database
    '''
    videoFileComp = os.path.splitext(name)
    #Get language for ffmpeg
    lang = languages.get(alpha_2=subLang).alpha_3
    #If subtitles, read and embed them
    subs = None
    tmpFile = videoFileComp[0] + "_tmp" + videoFileComp[1]
    if subLang:
        subFile = videoFileComp[0] + ".{}.vtt".format(subLang)
        try:
            #Read subtitle file
            with open(subFile, 'r') as f:
                subs = f.read()
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "panic", "-i", name, "-sub_charenc", "UTF-8", "-i", subFile, "-map", "0:v", "-map", "0:a", "-c", "copy", "-map", "1", "-c:s:0", "mov_text", "-metadata:s:s:0", "language=" + lang, "-metadata:s:a:0", "language=" + lang, tmpFile]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            shutil.move(tmpFile, name)
            os.remove(subFile)
        except IOError:
            subs = None
    #If no subtitles added, change audio language at least
    if not subs:
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "panic", "-i", name, "-map", "0:v", "-map", "0:a", "-c", "copy", "-metadata:s:a:0", "language=" + lang, tmpFile]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process.wait()
        shutil.move(tmpFile, name)
    #Read description
    desc = None
    try:
        descFile = videoFileComp[0] + ".description"
        with open(descFile, 'r') as f:
            desc = f.read()
        os.remove(descFile)
    except IOError:
        pass
    #Read artist, title
    cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-Artist", name]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    artist = process.stdout.read().decode("UTF-8").split(':', 1)[1].strip()
    cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-Title", name]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    title = process.stdout.read().decode("UTF-8").split(':', 1)[1].strip()
    #Read image width
    hd, formatString, width, height = yta.readResolution(name)
    #Read date
    cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-ContentCreateDate", name]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    r = process.stdout.read().decode("UTF-8").split(':', 1)[1].strip()
    dateTime = r[0:4] + ':' + r[4:6] + ':' + r[6:8] + " 00:00:00"
    date = r[0:4] + '-' + r[4:6] + '-' + r[6:8]
    oldName = os.path.basename(name)
    #Remove id from filename
    videoID = ''
    if oldName.startswith("ID") and '&' in oldName:
        [videoID, oldName] = oldName.split('&', 1)
        videoID = videoID[2:]
    #Download additional metadata
    timestamp = None
    duration = None
    tags = None
    apiDesc = None
    viewCount = None
    likeCount = None
    dislikeCount = None
    statisticsUpdated = None
    try:
        [timestamp, duration, tags, apiDesc, viewCount, likeCount, dislikeCount, statisticsUpdated] = ytameta.getMetadata(videoID)
    except FileNotFoundError:
        print("WARNING: No Youtube data API key available, unable to load additional metadata")
    except OSError:
        print("ERROR: Unable to load metadata for {}".format(videoID))
    if timestamp:
        dateTime = datetime.strftime(datetime.fromtimestamp(timestamp, tz=timezone.utc), "%Y:%m:%d %H:%M:%S+0")
    else:
        dateTime = r[0:4] + ':' + r[4:6] + ':' + r[6:8] + " 00:00:00+0"
        timestamp = datetime.timestamp(datetime.strptime(dateTime + "000", "%Y:%m:%d %H:%M:%S%z"))
    #Replace existing video
    if replace:
        try:
            dbfilename = db.execute("SELECT filename FROM videos WHERE youtubeID = ?;", (videoID,)).fetchone()[0]
        except (sqlite3.Error, IndexError):
            sys.exit("ERROR: Unable to replace video with ID \"{}\"".format(videoID))
        dbfilename = os.path.join(os.path.dirname(name), dbfilename)
        replaceFilepath = dbfilename + ".bak"
        try:
            os.rename(dbfilename, replaceFilepath)
        except OSError:
            print("WARNING: File to replace not found")
    #Add date to file name
    (oldName, ext) = os.path.splitext(oldName)
    fileName = "{} {}{}".format(date, oldName, ext)
    #Check if file name already exists
    i = 1
    while checkFilename(fileName, db, replace, videoID):
        i += 1
        fileName = "{} {} {}{}".format(date, oldName, i, ext)
    #Rename file
    newName = os.path.join(os.path.dirname(name), fileName)
    os.rename(name, newName)
    #Set additional metadata
    cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-overwrite_original", "-ContentCreateDate='{}'".format(dateTime), "-Comment={}".format('YoutubeID: ' + videoID), "-Encoder=", newName]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "--printConv", "-overwrite_original", "-HDVideo={}".format(hd), newName]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    #Use description from API if available
    if apiDesc:
        desc = apiDesc
        config = os.path.join(os.path.dirname(os.path.realpath(__file__)), "exiftool.config")
        cmd = ["exiftool", "-config", config, "-api", "largefilesupport=1", "-overwrite_original", "-ec", "-Description={}".format(desc), newName]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        process.wait()
    #Get chapter information
    chapters = yta.extractChapters(desc)
    #Check if fix required
    artist, title = ytafix.fixVideo(newName, videoID, fileArtist=artist)
    #Calculate checksum
    checksum = yta.calcSHA(newName)
    #Check file integrity
    if check:
        cmd = ["ffmpeg", "-v", "error", "-i", newName, "-f", "null", "-"]
        out, _ = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
        if out:
            print("ERROR: File corrupt! SHA256: " + checksum)
        else:
            print("File check passed, SHA256: " + checksum)
    #Download thumbnail
    url = "https://i.ytimg.com/vi/{}/maxresdefault.jpg".format(videoID)
    try:
        [thumbData, thumbFormat] = yta.loadImage(url)
    except OSError:
        url = "https://i.ytimg.com/vi/{}/hqdefault.jpg".format(videoID)
        try:
            print("WARNING: Unable to download highres thumbnail for {}, getting lower res".format(videoID))
            [thumbData, thumbFormat] = yta.loadImage(url)
        except OSError:
            print("ERROR: Unable to download thumbnail for {}".format(videoID))
            thumbData = None
            thumbFormat = None
    #Save to database
    saveToDB(db, replace, title, artist, date, timestamp, desc, videoID, subs, fileName, checksum, thumbData, thumbFormat, duration, tags, formatString, width, height, subLang, viewCount, likeCount, dislikeCount, statisticsUpdated, chapters)
    #Remove replaced file:
    if replace:
        try:
            os.remove(replaceFilepath)
        except OSError:
            pass
# ########################################################################### #

# --------------------------------------------------------------------------- #
def saveToDB(db, replace, name, artist, date, timestamp, desc, youtubeID, subs, filename, checksum, thumbData, thumbFormat, duration, tags, res, width, height, lang, viewCount, likeCount, dislikeCount, statisticsUpdated, chapters):
    '''Write info to database

    :param db: Connection to the database
    :type db: sqlite3.Cursor
    :param replace: Whether to replace a video already in the archive database
    :type replace: boolean
    :param name: The video title
    :type name: string
    :param artist: The creators name
    :type artist: string
    :param date: The release date in the format YYYY-MM-DD
    :type date: string
    :param timestamp: The unix timestamp of the video release
    :type timestamp: integer
    :param desc: The video description
    :type desc: string
    :param youtubeID: The youtube ID
    :type youtubeID: string
    :param subs: The subtitles
    :type subs: string
    :param filename: The name of the video file
    :type filename: string
    :param checksum: A sha256 checksum of the file
    :type checksum: string
    :param thumbData: Raw thumbnail image data
    :type thumbData: bytes
    :param thumbFormat: Thumbnail MIME type
    :type thumbFormat: string
    :param duration: The duration of the video in seconds
    :type duration: integer
    :param tags: String with one tag per line
    :type tags: strings
    :param res: Resolution string
    :type res: strings
    :param width: The video image width
    :type width: integer
    :param height: The video image height
    :type height: integer
    :param lang: Video language code
    :type lang: strings
    :param viewCount: The view count
    :type viewCount: integer
    :param likeCount: The like count
    :type likeCount: integer
    :param dislikeCount: The dislike count
    :type dislikeCount: integer
    :param statisticsUpdated: Timestamp of the last statistics update, None if one of the other statistics items is None
    :type statisticsUpdated: integer
    :param chapters: String containing one chapter per line in the format:  hh:mm:ss.sss Chapter Name
    :type chapters: string

    :raises: :class:``sqlite3.Error: Unable to write to database
    '''
    if replace:
        #Get current and old title + description
        r = db.execute("SELECT id,title,description,oldtitles,olddescriptions FROM videos WHERE youtubeID = ?;", (youtubeID,))
        info = r.fetchone()
        del r
        dbID = info[0]
        currentTitle = info[1]
        currentDesc = info[2]
        #Check if title and desc are unchanged
        if currentTitle == name and currentDesc == desc:
            #Unchanged, just update the rest
            update = "UPDATE videos SET creator = ?, date = ?, timestamp = ?, subtitles = ?, filename = ?, checksum = ?, thumb = ?, thumbformat = ?, duration = ?, tags = ?, resolution = ?, width = ?, height = ?, language = ?, chapters = ? WHERE id = ?"
            db.execute(update, (artist, date, timestamp, subs, filename, checksum, thumbData, thumbFormat, duration, tags, res, width, height, lang, chapters, dbID))
        else:
            #Changed, write old title + desc to json, update everything
            t = int(time.time())
            #Title changed
            if currentTitle != name:
                try:
                    oldtitles = json.loads(info[3])
                except TypeError:
                    oldtitles = []
                oldtitles.append({"timestamp":t,"title":currentTitle})
                oldtitles = json.dumps(oldtitles, ensure_ascii=False)
            else:
                oldtitles = info[3]
            #Desc changed
            if currentDesc != desc:
                try:
                    olddescs = json.loads(info[4])
                except TypeError:
                    olddescs = []
                olddescs.append({"timestamp":t,"description":currentDesc})
                olddescs = json.dumps(olddescs, ensure_ascii=False)
            else:
                olddescs = info[4]
            #Update db
            update = "UPDATE videos SET title = ?, creator = ?, date = ?, timestamp = ?, description = ?, subtitles = ?, filename = ?, checksum = ?, thumb = ?, thumbformat = ?, duration = ?, tags = ?, resolution = ?, width = ?, height = ?, language = ?, chapters = ? , oldtitles = ?, olddescriptions = ? WHERE id = ?"
            db.execute(update, (name, artist, date, timestamp, desc, subs, filename, checksum, thumbData, thumbFormat, duration, tags, res, width, height, lang, chapters, oldtitles, olddescs, dbID))
    else:
        insert = "INSERT INTO videos(title, creator, date, timestamp, description, youtubeID, subtitles, filename, checksum, thumb, thumbformat, duration, tags, resolution, width, height, language, chapters) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        db.execute(insert, (name, artist, date, timestamp, desc, youtubeID, subs, filename, checksum, thumbData, thumbFormat, duration, tags, res, width, height, lang, chapters))
    #Update statistics if statisticsUpdated is not None
    if statisticsUpdated:
        update = "UPDATE videos SET viewcount = ?, likecount = ?, dislikecount = ?, statisticsupdated = ? WHERE youtubeID = ?"
        db.execute(update, (viewCount, likeCount, dislikeCount, statisticsUpdated, youtubeID))
# ########################################################################### #

# --------------------------------------------------------------------------- #
def checkFilename(name, db, replace, videoID):
    '''Check if the given filename is already in the database

    :param name: The filename to check
    :type name: string
    :param db: Connection to the metadata database
    :type db: sqlite3.Cursor
    :param replace: Whether to replace a video already in the archive database
    :type replace: boolean
    :param videoID: The video ID to replace
    :type videoID: string

    :returns: True if filename in database, else False
    :rtype: boolean
    '''
    cmd = "SELECT youtubeID FROM videos WHERE filename = ?;"
    r = db.execute(cmd, (name,)).fetchone()
    if replace:
        return bool(r) and r[0] != videoID
    return bool(r)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def createOrConnectDB(path):
    '''Create database with the required tables

    :param path: Path at which to store the new database
    :type path: string

    :raises: :class:``sqlite3.Error: Unable to create database

    :returns: Connection to the newly created database
    :rtype: sqlite3.Connection
    '''

    #Create database
    dbCon = yta.connectDB(path)
    #Create table
    yta.createVideoTable(dbCon)
    #Return database connection
    return dbCon
# ########################################################################### #

# --------------------------------------------------------------------------- #
class PostHook:
    '''Youtube-dl progress hook'''

    def __init__(self, lang, db, check, replace):
        '''Init

        :param lang: The language identifier
        :type lang: string
        :param db: Connection to the metadata database
        :type db: sqlite3.Cursor
        :param check: Whether to perform an integrity check and calc the checksum
        :type check: boolean
        :param replace: Whether to replace a video already in the archive database
        :type replace: boolean
        '''
        self.lang = lang
        self.db = db
        self.check = check
        self.replace = replace

    def finished(self, filename):
        '''Called after all the postprocessors are done

        :param filename: The complete filepath of the processed video
        :type filename: string
        '''
        print("[ytarchiver] Post-processing \"{}\"".format(filename))
        processFile(filename, self.lang, self.db, self.check, self.replace)
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        postprocess(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
