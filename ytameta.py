#!/usr/bin/env python3
''' ytameta - add additional metadata to archive database '''

import os
import sys
import argparse
import sqlite3
from decimal import Decimal
from datetime import datetime
import time
import re
import requests
import pytz
import ytacommon as yta

# --------------------------------------------------------------------------- #
__statisticsdbversion__ = 1
# ########################################################################### #

# --------------------------------------------------------------------------- #
def addMetadata(args):
    '''Add additional metadata to archive database

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Get database path
    parser = argparse.ArgumentParser(prog="ytameta", description="Add additional metadata to existing archive databases")
    parser.add_argument("DIR", help="The directory containing the archive database to work on")
    args = parser.parse_args()

    path = os.path.normpath(os.path.abspath(args.DIR))
    dbPath = os.path.join(path, "archive.db")
    if not os.path.isdir(path) or not os.path.isfile(dbPath):
        parser.error("DIR must be a directory containing an archive database")

    #Check if database needs upgrade
    yta.upgradeDatabase(dbPath)

    #Connect to database
    dbCon = yta.connectDB(dbPath)
    db = dbCon.cursor()
    #Modify database
    modifyDatabase(db)
    #Save thumbnails to database
    r = db.execute("SELECT youtubeID FROM videos;")
    for item in r.fetchall():
        #Get video filepath
        youtubeID = item[0]
        try:
            [timestamp, duration, tags, _, _, _, _, _] = getMetadata(youtubeID)
            db.execute("UPDATE videos SET timestamp = ?, duration = ?, tags = ? WHERE youtubeID = ?", (timestamp, duration, tags, youtubeID))
        except FileNotFoundError:
            print("WARNING: No Youtube data API key available, unable to load additional metadata")
            break
        except requests.exceptions.HTTPError:
            print("ERROR: Unable to load metadata for {}".format(youtubeID))
            continue
    #Close database
    yta.closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def getMetadata(youtubeID):
    '''Calls the Youtube Data API to get the video duration, upload timestamp
    and tags

    :param youtubeID: The Youtube ID
    :type youtubeID: string

    :raises: :class:``OSError: Unable to read API key from file
    :raises: :class:``requests.exceptions.HTTPError: Unable to get metadata

    :returns: List with timestamp (int) at index 0, duration (int) at index 1,
        tags (string) at index 2, description (string) at index 3,
        viewCount (int or None) at index 4, likeCount (int or None) at index 5,
        dislikeCount (int or None) at index 6, and statistics updated timestamp (int or None)
        at index 7. The timestamp is None, if one or more of the other statistics items is None
    :rtype: list
    '''
    #Get API key
    apiKey = getAPIKey()
    #Get metadata
    url = "https://www.googleapis.com/youtube/v3/videos?part=contentDetails%2Csnippet%2Cstatistics&id={}&key={}".format(youtubeID, apiKey)
    r = requests.get(url)
    r.raise_for_status()
    d = r.json()
    #Check if empty
    if not d["items"]:
        print("WARNING: No metadata available for " + youtubeID)
        return [None, None, None, None, None, None, None, None]
    #Convert update time to timestamp
    try:
        timestamp = int(datetime.timestamp(datetime.strptime(d["items"][0]["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%S.%f%z")))
    except ValueError:
        timestamp = int(datetime.timestamp(datetime.strptime(d["items"][0]["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%S%z")))
    #Get description
    description = d["items"][0]["snippet"]["description"]
    #Convert duration to seconds
    duration = convertDuration(d["items"][0]["contentDetails"]["duration"])
    #Extract tags
    if "tags" in d["items"][0]["snippet"]:
        tags = '\n'.join([i.lower() for i in d["items"][0]["snippet"]["tags"]])
    else:
        tags = None
    #Extract statistics
    viewCount = toInt(d["items"][0]["statistics"]["viewCount"])
    try:
        likeCount = toInt(d["items"][0]["statistics"]["likeCount"])
    except KeyError:
        likeCount = None
    try:
        dislikeCount = toInt(d["items"][0]["statistics"]["dislikeCount"])
    except KeyError:
        dislikeCount = None
    if isinstance(viewCount, int):
        statisticsUpdated = int(time.time())
    else:
        statisticsUpdated = None
    #Return results
    return [timestamp, duration, tags, description, viewCount, likeCount, dislikeCount, statisticsUpdated]
# ########################################################################### #

# --------------------------------------------------------------------------- #
def modifyDatabase(db):
    '''Add duration and tags columns to videos table of they
    don't exist already

    :param db: Connection to the metadata database
    :type db: sqlite3.Cursor
    '''
    try:
        db.execute('ALTER TABLE videos ADD COLUMN duration INTEGER;')
        db.execute('ALTER TABLE videos ADD COLUMN tags TEXT;')
    except sqlite3.Error:
        pass
# ########################################################################### #

# --------------------------------------------------------------------------- #
def updateStatistics(db, youngerTimestamp=sys.maxsize, count=sys.maxsize, apiKey=None):
    '''Update the video statistics in an archive database

    :param db: Connection to the archive database
    :type db: sqlite3.Cursor
    :param youngerTimestamp: Only videos with an update timestamp younger than this one will be updated (Default: max 64-bit int)
    :type lastUpdateTimestamp: integer
    :param count: Max number of videos to update (Default: max 64-bit int)
    :type count: integer
    :param apiKey: The API-Key for the Youtube-API (if not given, it will be read from file)
    :type apiKey: string

    :returns: Tuple with what is left of maxCount (int), whether the update was complete (bool)
    :rtype: Tuple
    '''
    #Get API key
    if not apiKey:
        apiKey = getAPIKey()
    #Loop through videos
    requestLimit = 50
    offset = 0
    completed = False
    items = []
    while True:
        #Check if max videos count reached zero
        if count == 0:
            #Check if videos missing
            r = db.execute("SELECT id FROM videos WHERE statisticsupdated < ? ORDER BY id LIMIT 1 OFFSET ?;", (youngerTimestamp, offset))
            #If videos missing exist loop without setting complete to true
            if r.fetchone():
                break
            #If no videos missing exist loop after setting complete to true
            completed = True
            break
        #Update request limit if smaller than max count
        if requestLimit > count:
            requestLimit = count
        #Select videos
        r = db.execute("SELECT youtubeID FROM videos WHERE statisticsupdated < ? ORDER BY id LIMIT ? OFFSET ?;", (youngerTimestamp, requestLimit, offset))
        videos = r.fetchall()
        #If no more videos exit look
        if not videos:
            completed = True
            break
        #Get video ids
        ids = [video[0] for video in videos]
        #Update offset and count
        offset += requestLimit
        count -= requestLimit
        #Get metadata
        url = "https://www.googleapis.com/youtube/v3/videos?part=statistics&id={}&key={}".format(','.join(ids), apiKey)
        r = requests.get(url)
        r.raise_for_status()
        d = r.json()
        if not d["items"]:
            continue
        #Add request time to items
        requestTime = int(time.time())
        for i in d["items"]:
            i["requestTime"] = requestTime
        #Add items to list
        items += d["items"]

    #Loop through items
    for item in items:
        try:
            viewCount = toInt(item["statistics"]["viewCount"])
        except KeyError:
            viewCount = None
        try:
            likeCount = toInt(item["statistics"]["likeCount"])
        except KeyError:
            likeCount = 0
        try:
            dislikeCount = toInt(item["statistics"]["dislikeCount"])
        except KeyError:
            dislikeCount = 0
        if isinstance(viewCount, int) and isinstance(likeCount, int) and isinstance(dislikeCount, int):
            statisticsUpdated = item["requestTime"]
        else:
            statisticsUpdated = None
        #Update database
        if statisticsUpdated:
            update = "UPDATE videos SET viewcount = ?, likecount = ?, dislikecount = ?, statisticsupdated = ? WHERE youtubeID = ?"
            db.execute(update, (viewCount, likeCount, dislikeCount, statisticsUpdated, item["id"]))
    #Return status
    return (count, completed)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def updateAllStatistics(path, automatic=False):
    '''Update the video statistics from all subdirs

    :param path: The path of the parent directory
    :type path: string
    :param automatic: Whether the update was started automatically or from user input (Default: False)
    :type automatic: boolean
    '''
    updateStarted = int(time.time())
    #Print message
    if automatic:
        print("\nUPDATING VIDEO STATISTICS DUE TO DATABASE OPTION")
    else:
        print("\nUPDATING VIDEO STATISTICS")
    #Get subdirs in path
    subdirs = [os.path.join(path, name) for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    subdirs = [sub for sub in subdirs if os.path.isfile(os.path.join(sub, "archive.db"))]
    if not subdirs:
        print("ERROR: No subdirs with archive databases at \'{}\'".format(path))
        return
    #Connect to database
    dbCon = connectUpdateCreateStatisticsDB(path)
    db = dbCon.cursor()
    #Check if quota was reset since last update
    lastupdate = db.execute("SELECT lastupdate FROM setup WHERE id = 1 LIMIT 1;").fetchone()[0]
    if lastupdate > getResetTimestamp():
        print("WARNING: Statistics update skipped because no quota reset since the last update")
        yta.closeDB(dbCon)
        return
    print('')
    #Get channels
    r = db.execute("SELECT name,lastupdate,complete FROM channels;")
    channels = {}
    for item in r.fetchall():
        channels[item[0]] = [item[1], item[2]]
    #Get maxcount
    maxcount = db.execute("SELECT maxcount FROM setup WHERE id = 1 LIMIT 1;").fetchone()[0]
    #Get API key
    apiKey = getAPIKey()
    #Loop through subdirs, skip completed ones
    skippedSubdirs = []
    for subdir in subdirs:
        #Check if maxcount was reached
        if maxcount == 0:
            break
        #Get last update info
        name = os.path.basename(os.path.normpath(subdir))
        try:
            lastupdate, complete = channels[name]
        except KeyError:
            lastupdate = sys.maxsize
            complete = False
            db.execute("INSERT INTO channels(name,lastupdate,complete) VALUES(?,?,?);", (name, lastupdate, complete))
        #If completed, skip for now
        if complete:
            skippedSubdirs.append(subdir)
            continue
        #Update statistics
        maxcount = updateSubdirStatistics(db, subdir, name, maxcount, lastupdate, complete, apiKey)

    #Loop through skipped subdirs
    for subdir in skippedSubdirs:
        #Check if maxcount was reached
        if maxcount == 0:
            break
        #Get last update info
        name = os.path.basename(os.path.normpath(subdir))
        lastupdate, complete = channels[name]
        #Update statistics
        maxcount = updateSubdirStatistics(db, subdir, name, maxcount, lastupdate, complete, apiKey)

    #Write lastupdate to statistics database
    db.execute("UPDATE setup SET lastupdate = ? WHERE id = 1", (updateStarted,))
    #Close database
    yta.closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def updateSubdirStatistics(db, path, name, maxcount, lastupdate, complete, apiKey):
    '''Update the statistics for one subdir

    :param db: Connection to the statistics database
    :type db: sqlite3.Connection
    :param path: The path of the subdir
    :type path: string
    :param name: The channel/subdir name
    :type name: string
    :param maxcount: The max number of videos allowed to update
    :type maxcount: integer
    :param lastupdate: Timestamp of the last update
    :type lastupdate: integer
    :param complete: Whether the last update was complete
    :type complete: boolean
    :param apiKey: The API-Key for the Youtube-API
    :type apiKey: string

    :returns: Number of update counts left
    :rtype: integer
    '''
    #Print status
    print("Updating \"{}\"".format(name))
    #Connect to channel database
    channelDB = yta.connectDB(os.path.join(path, "archive.db"))
    #First update the stats missed last time
    updateTimestamp = int(time.time())
    if not complete:
        maxcount, complete = updateStatistics(channelDB, lastupdate, maxcount, apiKey)
    #If counts left, update the other ones
    if complete and maxcount > 0:
        maxcount, complete = updateStatistics(channelDB, updateTimestamp, maxcount, apiKey)
    #Close channel db
    yta.closeDB(channelDB)
    #Write new info to database
    db.execute("UPDATE channels SET lastupdate = ?, complete = ? WHERE name = ?;", (updateTimestamp, complete, name))

    return maxcount
# ########################################################################### #

# --------------------------------------------------------------------------- #
def connectUpdateCreateStatisticsDB(directory):
    '''Connects to the statistics database used for updating the statistics of
    all channels, updates it if necessary or creates it if it does not exist

    :param path: The path of the database
    :type path: string

    :raises: :class:``sqlite3.Error: Unable to connect to database

    :returns: Connection to the database
    :rtype: sqlite3.Connection
    '''
    #Connect to database
    dbCon = yta.connectDB(os.path.join(directory, "statistics.db"))
    db = dbCon.cursor()
    #Get database version
    try:
        r = db.execute("SELECT dbversion FROM setup ORDER BY id DESC LIMIT 1;")
        version = r.fetchone()[0]
        del r
    except sqlite3.Error:
        #No version field: new database
        version = 0

    if version < __statisticsdbversion__:
        try:
            #Perform initial setup
            if version < 1:
                #Set encoding
                dbCon.execute("pragma encoding=UTF8")
                #Create tables
                cmd = """ CREATE TABLE setup (
                              id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                              autoupdate BOOLEAN NOT NULL,
                              lastupdate INTEGER NOT NULL,
                              maxcount INTEGER NOT NULL,
                              dbversion INTEGER NOT NULL
                          ); """
                dbCon.execute(cmd)
                cmd = """ CREATE TABLE channels (
                              id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
                              name STRING UNIQUE NOT NULL,
                              lastupdate INTEGER NOT NULL,
                              complete BOOLEAN NOT NULL
                          ); """
                dbCon.execute(cmd)
                #Set db version
                version = 1
                db.execute("INSERT INTO setup(autoupdate,lastupdate,maxcount,dbversion) VALUES(?,?,?,?)", (False, 0, 100000, version))
                dbCon.commit()
        except sqlite3.Error as e:
            print("ERROR: Unable to upgrade database (\"{}\")".format(e))
            dbCon.rollback()
            yta.closeDB(dbCon)
            sys.exit(1)

    #Return connection to database
    return dbCon
# ########################################################################### #

# --------------------------------------------------------------------------- #
def getAPIKey():
    '''Read the API key from ~/.ytarchiverapi

    :raises: :class:``OSError: Unable to read API key from file
    '''
    apiPath = os.path.join(os.path.expanduser('~'), ".ytarchiverapi")
    with open(apiPath) as f:
        apiKey = f.readline().strip()
    if not apiKey:
        raise FileNotFoundError
    return apiKey
# ########################################################################### #

# --------------------------------------------------------------------------- #
def getResetTimestamp():
    '''Return the timestamp of the last API quota reset (Midnight Pacific)

    :returns: The timestamp
    :rtype: integer
    '''
    tz = pytz.timezone('US/Pacific')
    midnight = datetime.combine(datetime.today(), datetime.min.time())
    midnightutc = tz.normalize(tz.localize(midnight)).astimezone(pytz.utc)
    timestamp = datetime.timestamp(midnightutc)
    return int(timestamp)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def convertDuration(dur):
    '''Convert ISO 8601 duration string to seconds
    Simplified from isodate by Gerhard Weis (https://github.com/gweis/isodate)

    :param dur: ISO 8601 duration string
    :type dur: string
    '''
    reg = re.compile(
        r"^(?P<sign>[+-])?"
        r"P(?!\b)"
        r"(?P<years>[0-9]+([,.][0-9]+)?Y)?"
        r"(?P<months>[0-9]+([,.][0-9]+)?M)?"
        r"(?P<weeks>[0-9]+([,.][0-9]+)?W)?"
        r"(?P<days>[0-9]+([,.][0-9]+)?D)?"
        r"((?P<separator>T)(?P<hours>[0-9]+([,.][0-9]+)?H)?"
        r"(?P<minutes>[0-9]+([,.][0-9]+)?M)?"
        r"(?P<seconds>[0-9]+([,.][0-9]+)?S)?)?$")
    items = reg.match(dur)
    el = items.groupdict()
    for key, val in el.items():
        if key not in ('separator', 'sign'):
            if val is None:
                el[key] = "0n"
            if key in ('years', 'months'):
                el[key] = Decimal(el[key][:-1].replace(',', '.'))
            else:
                el[key] = float(el[key][:-1].replace(',', '.'))

    return int(el["weeks"] * 604800 + el["days"] * 86400 + el["hours"] * 3600 + el["minutes"] * 60 + el["seconds"])
# ########################################################################### #

# --------------------------------------------------------------------------- #
def toInt(var):
    '''Cast a variable to integer or return null if not possible'''
    try:
        return int(var)
    except ValueError:
        return None
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        addMetadata(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
