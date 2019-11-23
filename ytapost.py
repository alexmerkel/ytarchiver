#!/usr/bin/env python3
''' ytapost - youtube archiver post processing steps '''

import os
import sys
import subprocess
import shutil
import sqlite3

# --------------------------------------------------------------------------- #
def postprocess(args):
    '''Postprocess a video file or a directory of video files

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Get files
    files = []
    try:
        path = os.path.normpath(os.path.abspath(args[1]))
        if os.path.isfile(path):
            dirPath = os.path.dirname(path)
            if path.lower().endswith((".m4v", ".mp4")):
                files.append(path)
            else:
                print("Unsupported file format, only .mp4 and .m4v are supported")
                return
        elif os.path.isdir(path):
            dirPath = path
            allf = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            for f in allf:
                if f.lower().endswith((".m4v", ".mp4")):
                    files.append(os.path.join(path, f))
            if not files:
                print("No supported files in directory, only .mp4 and .m4v are supported")
                return
        else:
            print("Usage: vapost.py FILE/DIR")
            return
    except IndexError:
        print("Usage: vapost.py FILE/DIR")
        return
    #Get subtitle language
    subLang = ""
    try:
        subLang = args[2]
    except IndexError:
        pass

    #Connect to database
    try:
        dbFile = os.path.join(dirPath, "archive.db")
        dbCon = createOrConnectDB(dbFile)
        db = dbCon.cursor()
    except sqlite3.Error as e:
        print(e)
        return

    for f in files:
        processFile(f, subLang, db)

    closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def processFile(name, subLang, db):
    '''Process a file

    :param name: The video file name
    :type name: string
    :param subLang: The subtitle language identifier
    :type subLang: string
    :param db: Connection to the metadata database
    :type db: sqlite3.Cursor

    :raises: :class:``sqlite3.Error: Unable to write to database
    '''
    videoFileComp = os.path.splitext(name)
    #If subtitles, read and embed them
    subs = None
    if subLang:
        subFile = videoFileComp[0] + ".{}.vtt".format(subLang)
        tmpFile = videoFileComp[0] + "_tmp" + videoFileComp[1]
        try:
            #Read subtitle file
            with open(subFile, 'r') as f:
                subs = f.read()
            #Get subtitle language for ffmpeg
            if subLang == "de":
                lang = "deu"
            elif subLang == "en":
                lang = "eng"
            else:
                lang = subLang
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "panic", "-i", name, "-sub_charenc", "UTF-8", "-i", subFile, "-map", "0:v", "-map", "0:a", "-c", "copy", "-map", "1", "-c:s:0", "mov_text", "-metadata:s:s:0", "language=" + lang, "-metadata:s:a:0", "language=" + lang, tmpFile]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            shutil.move(tmpFile, name)
            os.remove(subFile)
        except IOError:
            pass
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
    cmd = ["exiftool", "-Artist", name]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    artist = process.stdout.read().decode("UTF-8").split(':', 1)[1].strip()
    cmd = ["exiftool", "-Title", name]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    title = process.stdout.read().decode("UTF-8").split(':', 1)[1].strip()
    #Read image width
    cmd = ["exiftool", "-ImageWidth", name]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    width = int(process.stdout.read().decode("UTF-8").split(':', 1)[1].strip())
    if width < 1200:
        hd = 0
    elif 1200 <= width < 1900:
        hd = 1
    elif 1900 <= width <= 3500:
        hd = 2
    else:
        hd = 3
    #Read date
    cmd = ["exiftool", "-ContentCreateDate", name]
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
    #Remove timestamp from filename
    timestamp = None
    if oldName.startswith("TS") and '&' in oldName:
        [timestamp, oldName] = oldName.split('&', 1)
        timestamp = int(timestamp)
    #Add date to file name
    newName = os.path.join(os.path.dirname(name), date + ' ' + oldName)
    os.rename(name, newName)
    #Fix metadata
    cmd = ["exiftool", "-overwrite_original", "-ContentCreateDate='{}'".format(dateTime), "-Comment={}".format('YoutubeID: ' + videoID), "-Encoder=", newName]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    cmd = ["exiftool", "--printConv", "-overwrite_original", "-HDVideo={}".format(hd), newName]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    process.wait()
    saveToDB(db, title, artist, date, timestamp, desc, videoID, subs)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def saveToDB(db, name, artist, date, timestamp, desc, youtubeID, subs):
    '''Write info to database

    :param db: Connection to the database
    :type db: sqlite3.Cursor
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

    :raises: :class:``sqlite3.Error: Unable to write to database
    '''
    insert = "INSERT INTO videos(title, creator, date, timestamp, description, youtubeID, subtitles) VALUES(?,?,?,?,?,?,?)"
    db.execute(insert, (name, artist, date, timestamp, desc, youtubeID, subs))
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
    tableCmd = """ CREATE TABLE IF NOT EXISTS videos (
                       id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                       title TEXT NOT NULL,
                       creator TEST NOT NULL,
                       date TEXT,
                       timestamp INTEGER,
                       description TEXT,
                       youtubeID TEXT NOT NULL,
                       subtitles TEXT
                   ); """

    #Create database
    dbCon = sqlite3.connect(path)
    db = dbCon.cursor()
    #Set encoding
    db.execute("pragma encoding=UTF8")
    #Create tables
    db.execute(tableCmd)
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
        postprocess(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
