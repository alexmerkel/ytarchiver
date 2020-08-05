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
import ytacommon as yta

# --------------------------------------------------------------------------- #
def addMetadata(args):
    '''Add additional metadata to archive database

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Get database path
    parser = argparse.ArgumentParser(prog="ytameta", description="Add additional metadata to exising archive databases")
    parser.add_argument("DIR", help="The directory containing the archive database to work on")
    args = parser.parse_args()

    path = os.path.normpath(os.path.abspath(args.DIR))
    dbPath = os.path.join(path, "archive.db")
    if not os.path.isdir(path) or not os.path.isfile(dbPath):
        parser.error("DIR must be a directory containg an archive database")

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
    likeCount = toInt(d["items"][0]["statistics"]["likeCount"])
    dislikeCount = toInt(d["items"][0]["statistics"]["dislikeCount"])
    if isinstance(viewCount, int) and isinstance(likeCount, int) and isinstance(dislikeCount, int):
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
def updateStatistics(db, youngerTimestamp=sys.maxsize, count=sys.maxsize):
    '''Update the video statistics in an archive database

    :param db: Connection to the arcive database
    :type db: sqlite3.Cursor
    :param youngerTimestamp: Only videos with an update timestamp younger than this one will be updated (Default: max 64-bit int)
    :type lastUpdateTimestamp: integer
    :param count: Max number of videos to update (Default: max 64-bit int)
    :type count: integer

    :returns: Tuple with what is left of maxCount (int), whether the update was complete (bool)
    :rtype: Tuple
    '''
    #Get API key
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
            if r.fetchone():
                break
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
        print(url)
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
