#!/usr/bin/env python3
''' ytameta - add additional metadata to archive database '''

import os
import sys
import argparse
import sqlite3
import random
from datetime import datetime
from xml.etree import ElementTree
import time
import json
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
    args = parser.parse_args(args)

    path = os.path.normpath(os.path.abspath(args.DIR))
    dbPath = os.path.join(path, "archive.db")
    if not os.path.isdir(path) or not os.path.isfile(dbPath):
        parser.error("DIR must be a directory containing an archive database")

    #Check if database needs upgrade
    yta.upgradeDatabase(dbPath)

    #Connect to database
    dbCon = yta.connectDB(dbPath)
    db = dbCon.cursor()
    #Save thumbnails to database
    r = db.execute("SELECT youtubeID FROM videos;")
    for item in r.fetchall():
        #Get video filepath
        youtubeID = item[0]
        try:
            [timestamp, duration, tags, _, _, _, _, _] = getMetadata(youtubeID)
            db.execute("UPDATE videos SET timestamp = ?, duration = ?, tags = ? WHERE youtubeID = ?", (timestamp, duration, tags, youtubeID))
        except yta.NoAPIKeyError:
            break
        except requests.exceptions.RequestException:
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

    :raises: :class:``ytacommon.NoAPIKeyError: Unable to read API key from file
    :raises: :class:``requests.exceptions.RequestException: Unable to get metadata

    :returns: List with timestamp (int) at index 0, duration (int) at index 1,
        tags (string) at index 2, description (string) at index 3,
        viewCount (int or None) at index 4, likeCount (int or None) at index 5,
        dislikeCount (int or None) at index 6, and statistics updated timestamp (int or None)
        at index 7. The timestamp is None, if one or more of the other statistics items is None
    :rtype: list
    '''
    #Get API key
    apiKey = yta.getAPIKey()
    if not apiKey:
        raise yta.NoAPIKeyError
    #Get metadata
    url = "https://www.googleapis.com/youtube/v3/videos?part=contentDetails%2Csnippet%2Cstatistics%2CliveStreamingDetails&id={}&key={}".format(youtubeID, apiKey)
    r = requests.get(url)
    r.raise_for_status()
    d = r.json()
    #Check if empty
    if not d["items"]:
        print("WARNING: No metadata available for " + youtubeID)
        return [None, None, None, None, None, None, None, None]
    #Convert update time to timestamp
    if "liveStreamingDetails" in d["items"][0] and "actualStartTime" in d["items"][0]["liveStreamingDetails"]:
        dtString = d["items"][0]["liveStreamingDetails"]["actualStartTime"]
    else:
        dtString = d["items"][0]["snippet"]["publishedAt"]
    try:
        timestamp = int(datetime.timestamp(datetime.strptime(dtString, "%Y-%m-%dT%H:%M:%S.%f%z")))
    except ValueError:
        timestamp = int(datetime.timestamp(datetime.strptime(dtString, "%Y-%m-%dT%H:%M:%S%z")))
    #Get description
    description = d["items"][0]["snippet"]["description"]
    #Convert duration to seconds
    duration = yta.convertDuration(d["items"][0]["contentDetails"]["duration"])
    #Extract tags
    if "tags" in d["items"][0]["snippet"]:
        tags = '\n'.join([i.lower() for i in d["items"][0]["snippet"]["tags"]])
    else:
        tags = None
    #Extract statistics
    try:
        viewCount = yta.toInt(d["items"][0]["statistics"]["viewCount"])
    except KeyError:
        viewCount = None
    try:
        likeCount = yta.toInt(d["items"][0]["statistics"]["likeCount"])
    except KeyError:
        likeCount = None
    try:
        dislikeCount = yta.toInt(d["items"][0]["statistics"]["dislikeCount"])
    except KeyError:
        dislikeCount = None
    if isinstance(viewCount, int) or isinstance(likeCount, int):
        statisticsUpdated = int(time.time())
    else:
        statisticsUpdated = None
    #Return results
    return [timestamp, duration, tags, description, viewCount, likeCount, dislikeCount, statisticsUpdated]
# ########################################################################### #

# --------------------------------------------------------------------------- #
def updateStatistics(db, youngerTimestamp=sys.maxsize, checkCaptions=False, count=sys.maxsize, apiKey=None, amendCaptions=False):
    '''Update the video statistics in an archive database

    :param db: Connection to the archive database
    :type db: sqlite3.Cursor
    :param youngerTimestamp: Only return incomplete if videos with a timestamp earlier than this one were not updated (Default: max 64-bit int)
    :type youngerTimestamp: integer, optional
    :param checkCaptions: Whether to check if captions were added since archiving the video (Default: False)
    :type checkCaptions: boolean, option
    :param count: Max number of videos to update (Default: max 64-bit int)
    :type count: integer, optional
    :param apiKey: The API-Key for the Youtube-API (if not given, it will be read from file)
    :type apiKey: string, optional
    :param amendCaptions: Whether to download the captions that were added since the video was archived
    :type amendCaptions: boolean, optional

    :raises: :class:``ytacommon.NoAPIKeyError: Unable to read API key from file
    :raises: :class:``requests.exceptions.RequestException: Unable to connect to API endpoint

    :returns: Tuple with what is left of maxCount (int), whether the update was complete (bool)
    :rtype: Tuple
    '''
    #Get API key
    if not apiKey:
        apiKey = yta.getAPIKey()
    if not apiKey:
        raise yta.NoAPIKeyError
    #Check captions
    checkCaptions = True if amendCaptions else checkCaptions
    #Loop through videos
    requestLimit = 50
    offset = 0
    completed = False
    items = []
    while True:
        #Check if max videos count reached zero
        if count <= 0:
            #Check if videos missing
            r = db.execute("SELECT id FROM videos WHERE statisticsupdated < ? ORDER BY id LIMIT 1;", (youngerTimestamp))
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
        r = db.execute("SELECT id,youtubeID,title,description,subtitles,oldtitles,olddescriptions,language FROM videos ORDER BY id LIMIT ? OFFSET ?;", (requestLimit, offset))
        videos = r.fetchall()
        #If no more videos exit look
        if not videos:
            completed = True
            break
        #Create result dict and ids list
        ids = []
        vids = {}
        for video in videos:
            ids.append(video[1])
            try:
                oldtitles = json.loads(video[5])
            except TypeError:
                oldtitles = []
            try:
                olddescs = json.loads(video[6])
            except TypeError:
                olddescs = []
            try:
                subtitles = len(video[4]) > 0
            except TypeError:
                subtitles = False
            vids[video[1]] = [video[0], video[2], video[3], subtitles, oldtitles, olddescs, video[7]] #database ID, title, desc, subtitles, oldtitles, olddescriptions, language
        #Update offset and count
        offset += requestLimit
        count -= requestLimit
        #Get metadata
        url = "https://www.googleapis.com/youtube/v3/videos?part=contentDetails%2Csnippet%2Cstatistics&id={}&key={}".format(','.join(ids), apiKey)
        r = requests.get(url)
        r.raise_for_status()
        d = r.json()
        if not d["items"]:
            continue
        #Add request time to items
        requestTime = int(time.time())
        for i in d["items"]:
            i["requestTime"] = requestTime
            i["dbid"] = vids[i["id"]][0]
            i["currenttitle"] = vids[i["id"]][1]
            i["currentdesc"] = vids[i["id"]][2]
            i["subtitles"] = vids[i["id"]][3]
            i["oldtitles"] = vids[i["id"]][4]
            i["olddescs"] = vids[i["id"]][5]
            i["language"] = vids[i["id"]][6]
        #Add items to list
        items += d["items"]

    #Loop through items
    for item in items:
        cmd = []
        i = []
        try:
            viewCount = yta.toInt(item["statistics"]["viewCount"])
        except KeyError:
            viewCount = None
        try:
            likeCount = yta.toInt(item["statistics"]["likeCount"])
        except KeyError:
            likeCount = 0
        try:
            dislikeCount = yta.toInt(item["statistics"]["dislikeCount"])
        except KeyError:
            dislikeCount = 0
        if isinstance(viewCount, int) and isinstance(likeCount, int) and isinstance(dislikeCount, int):
            cmd.append("viewcount = ?, likecount = ?, dislikecount = ?, statisticsupdated = ?")
            i += [viewCount, likeCount, dislikeCount, item["requestTime"]]
        #Compare title and desc
        try:
            if item["snippet"]["title"] and item["snippet"]["title"] != item["currenttitle"]:
                item["oldtitles"].append({"timestamp":item["requestTime"],"title":item["currenttitle"]})
                cmd.append("title = ?, oldtitles = ?")
                i += [item["snippet"]["title"], json.dumps(item["oldtitles"], ensure_ascii=False)]
        except KeyError:
            pass
        try:
            if item["snippet"]["description"] and item["snippet"]["description"] != item["currentdesc"]:
                item["olddescs"].append({"timestamp":item["requestTime"],"description":item["currentdesc"]})
                cmd.append("description = ?, olddescriptions = ?")
                i += [item["snippet"]["description"], json.dumps(item["olddescs"], ensure_ascii=False)]
        except KeyError:
            pass
        #Check if captions were added
        captions = item["contentDetails"]["caption"].lower() == "true"
        if checkCaptions and captions != item["subtitles"]:
            if captions:
                if amendCaptions:
                    amendCaption(db,item["dbid"], item["id"], item["language"])
                else:
                    print("INFO: Video [{}] \"{}\" had captions added since archiving".format(item["id"], item["snippet"]["title"]))
            else:
                print("INFO: Video [{}] \"{}\" had captions removed since archiving".format(item["id"], item["snippet"]["title"]))
        #Update database
        if cmd:
            update = "UPDATE videos SET " + ", ".join(cmd) + " WHERE id = ?"
            i.append(item["dbid"])
            db.execute(update, tuple(i))
    #Return status
    return (count, completed)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def updateAllStatistics(path, automatic=False, captions=False, amendCaptions=False):
    '''Update the video statistics from all subdirs

    :param path: The path of the parent directory
    :type path: string
    :param automatic: Whether the update was started automatically or from user input (Default: False)
    :type automatic: boolean
    :param captions: Whether to check if captions were added since archiving the video (Default: False)
    :type captions: boolean, optional
    :param amendCaptions: Whether to download the captions that were added since the video was archived
    :type amendCaptions: boolean, optional

    :raises: :class:``ytacommon.NoAPIKeyError: Unable to read API key from file
    :raises: :class:``requests.exceptions.RequestException: Unable to connect to API endpoint
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
    apiKey = yta.getAPIKey()
    if not apiKey:
        raise yta.NoAPIKeyError
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
        try:
            maxcount = _updateSubdirStatistics(db, subdir, name, captions, amendCaptions, maxcount, lastupdate, complete, apiKey)
        except requests.exceptions.RequestException as e:
            print("ERROR: Network error while trying to update the statistics (\"{}\")".format(e))
            return

    #Loop through skipped subdirs
    i = 0
    count = len(skippedSubdirs)
    random.shuffle(skippedSubdirs)
    for subdir in skippedSubdirs:
        #Check if maxcount was reached
        if maxcount == 0:
            break
        i += 1
        #Get last update info
        name = os.path.basename(os.path.normpath(subdir))
        lastupdate, complete = channels[name]
        #Update statistics
        print("({}/{}) ".format(i, count), end='')
        try:
            maxcount = _updateSubdirStatistics(db, subdir, name, captions, amendCaptions, maxcount, lastupdate, complete, apiKey)
        except requests.exceptions.RequestException as e:
            print("ERROR: Network error while trying to update the statistics (\"{}\")".format(e))
            return

    #Write lastupdate to statistics database
    db.execute("UPDATE setup SET lastupdate = ? WHERE id = 1", (updateStarted,))
    #Close database
    yta.closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def _updateSubdirStatistics(db, path, name, captions, amendCaptions, maxcount, lastupdate, complete, apiKey):
    '''Update the statistics for one subdir

    :param db: Connection to the statistics database
    :type db: sqlite3.Connection
    :param path: The path of the subdir
    :type path: string
    :param name: The channel/subdir name
    :type name: string
    :param captions: Whether to check if captions were added since archiving the video (Default: False)
    :type captions: boolean
    :param amendCaptions: Whether to download the captions that were added since the video was archived
    :type amendCaptions: boolean, optional
    :param maxcount: The max number of videos allowed to update
    :type maxcount: integer
    :param lastupdate: Timestamp of the last update
    :type lastupdate: integer
    :param complete: Whether the last update was complete
    :type complete: boolean
    :param apiKey: The API-Key for the Youtube-API
    :type apiKey: string

    :raises: :class:``requests.exceptions.RequestException: Unable to connect to API endpoint

    :returns: Number of update counts left
    :rtype: integer
    '''
    #Print status
    print("Updating \"{}\"".format(name))
    #Connect to channel database
    channelDB = yta.connectDB(os.path.join(path, "archive.db"))
    #Perform update
    updateTimestamp = int(time.time())
    maxcount, complete = updateStatistics(channelDB, lastupdate, captions, maxcount, apiKey, amendCaptions)
    #Close channel db
    yta.closeDB(channelDB)
    #Write new info to database
    db.execute("UPDATE channels SET lastupdate = ?, complete = ? WHERE name = ?;", (updateTimestamp, complete, name))

    return maxcount
# ########################################################################### #

# --------------------------------------------------------------------------- #
def amendCaption(db, dbID, youtubeID, lang):
    '''Download the video captions that were added since the video was archived

    :param db: Connection to the statistics database
    :type db: sqlite3.Connection
    :param dbID: The id of the video in the video table
    :type dbID: integer
    :param youtubeID: The youtube id of the video
    :type youtubeID: string
    :param lang: The language string of the video
    :type lang: string
    '''
    #Get a list of all available subtitles
    try:
        url = "https://video.google.com/timedtext?hl=en&type=list&v=" + youtubeID
        r = requests.get(url)
        r.raise_for_status()
        subs = [c.attrib for c in ElementTree.fromstring(r.content) if c.tag == "track"]
    except requests.exceptions.RequestException:
        print("ERROR: Unable to amend subtitles for video \"{}\"".format(youtubeID))
        return
    sub = None
    #Try direct match for sub language
    for s in subs:
        if s["lang_code"] == lang:
            sub = s
            break
    #No direct match, try prefix match with default key
    if not sub:
        for s in subs:
            if s["lang_code"][0:2] == lang and "lang_default" in s and s["lang_default"]:
                sub = s
                break
    #No direct match, try prefix match without default key
    if not sub:
        for s in subs:
            if s["lang_code"][0:2] == lang:
                sub = s
                break
    if not sub:
        print("INFO: No subtitle with language \"{}\" for video \"{}\" available".format(lang, youtubeID))
        return
    #Download subtitles
    try:
        url = "https://video.google.com/timedtext?fmt=vtt&lang={}&v={}&name={}".format(sub["lang_code"], youtubeID, requests.utils.quote(sub["name"]))
        r = requests.get(url)
        r.raise_for_status()
        subtitles = r.text
    except requests.exceptions.RequestException:
        print("ERROR: Unable to download subtitle \"{}\" for video \"{}\"".format(sub["lang_code"], youtubeID))
        return
    #Write new subtitles to database
    try:
        db.execute("UPDATE videos SET subtitles = ? WHERE id = ?", (subtitles, dbID))
    except sqlite3.Error as e:
        print("ERROR: Unable to write subtitle for video \"{}\" to database (Error: \"{}\")".format(youtubeID, e))
        return
    #Print success message
    print("INFO: Added subtitle \"{}\" for video \"{}\" to the database".format(sub["lang_code"], youtubeID))
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
                              id INTEGER PRIMARY KEY UNIQUE NOT NULL,
                              autoupdate BOOLEAN NOT NULL,
                              lastupdate INTEGER NOT NULL,
                              maxcount INTEGER NOT NULL,
                              dbversion INTEGER NOT NULL
                          ); """
                dbCon.execute(cmd)
                cmd = """ CREATE TABLE channels (
                              id INTEGER PRIMARY KEY UNIQUE NOT NULL,
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
if __name__ == "__main__":
    try:
        addMetadata(sys.argv[1:])
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
