#!/usr/bin/env python3
''' ytacommon - common functions for ytarchiver scripts '''

import os
import sys
import sqlite3
import re
import subprocess
import hashlib
from decimal import Decimal as decimal
import requests
from appdirs import AppDirs

# --------------------------------------------------------------------------- #
__version__ = "1.4.1"
__dbversion__ = 7
# ########################################################################### #

# --------------------------------------------------------------------------- #
def getFormatString(selector="4k"):
    '''Returns the youtube-dl format string for the selected quality

    :param selector: The quality selector, "hd", "4k" (default), or "8k"
    :type selector: string, optional

    :returns: The format string for youtube-dl
    :rtype: string
    '''
    if selector == "hd":
        dlformat = "(bestvideo[width=1920][ext=mp4]/bestvideo[width=1920]/bestvideo[ext=mp4]/bestvideo)+(140/m4a/bestaudio)/best"
    elif selector == "8k":
        dlformat = "(bestvideo[width<8000][width>4000][ext=mp4]/bestvideo[width<8000][width>4000]/bestvideo[width<4000][width>1920][ext=mp4]/bestvideo[width<4000][width>1920]/bestvideo[width>1920][ext=mp4]/bestvideo[width>1920]/bestvideo[width=1920][ext=mp4]/bestvideo[width=1920]/bestvideo[ext=mp4]/bestvideo)+(140/m4a/bestaudio)/best"
    else:
        dlformat = "(bestvideo[width<4000][width>1920][ext=mp4]/bestvideo[width<4000][width>1920]/bestvideo[width>1920][ext=mp4]/bestvideo[width>1920]/bestvideo[width=1920][ext=mp4]/bestvideo[width=1920]/bestvideo[ext=mp4]/bestvideo)+(140/m4a/bestaudio)/best"
    return dlformat
# ########################################################################### #

# --------------------------------------------------------------------------- #
def connectDB(path):
    '''Connect to a database

    :param path: The path of the database
    :type path: string

    :raises: :class:``sqlite3.Error: Unable to connect to database

    :returns: Connection to the database
    :rtype: sqlite3.Connection
    '''
    #Connect database
    dbCon = sqlite3.connect(path)
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
def calcSHA(path):
    '''Calculate sha256 hash of file

    :param path: Filepath
    :type path: string

    :raises: :class:``IOError: Unable to open file
    '''
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
# ########################################################################### #

# --------------------------------------------------------------------------- #
def loadImage(url):
    '''Download image at url

    :param url: The image url
    :type url: string

    :raises: :class:``requests.exceptions.HTTPError: Unable to load image from URL

    :returns: List with the raw image data at index 0 and the mime type at index 1
    :rtype: list
    '''
    r = requests.get(url, stream=True)
    r.raw.decode_content = True
    r.raise_for_status()
    return[r.raw.data, r.headers['content-type']]
# ########################################################################### #

# --------------------------------------------------------------------------- #
def createChannelTable(dbCon):
    '''Create channel table if it does not exist already

    :param dbCon: Connection to the database
    :type dbCon: sqlite3.Connection

    :raises: :class:``sqlite3.Error: Unable to read from database
    '''
    cmd = """ CREATE TABLE IF NOT EXISTS channel (
                  id INTEGER PRIMARY KEY UNIQUE NOT NULL,
                  name TEXT NOT NULL,
                  url TEXT NOT NULL,
                  playlist TEXT NOT NULL,
                  language TEXT NOT NULL,
                  description TEXT,
                  location TEXT,
                  joined TEXT,
                  links TEXT,
                  profile BLOB,
                  profileformat TEXT,
                  banner BLOB,
                  bannerformat TEXT,
                  videos INTEGER NOT NULL,
                  lastupdate INTEGER NOT NULL,
                  dbversion INTEGER NOT NULL,
                  maxresolution NOT NULL,
                  totalsize INTEGER NOT NULL
              ); """
    #Set encoding
    dbCon.execute("pragma encoding=UTF8")
    #Create tables
    dbCon.execute(cmd)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def createVideoTable(dbCon):
    '''Create video table if it does not exist already

    :param dbCon: Connection to the database
    :type dbCon: sqlite3.Connection

    :raises: :class:``sqlite3.Error: Unable to read from database
    '''
    cmd = """ CREATE TABLE IF NOT EXISTS videos (
                  id INTEGER PRIMARY KEY UNIQUE NOT NULL,
                  title TEXT NOT NULL,
                  creator TEXT NOT NULL,
                  date TEXT NOT NULL,
                  timestamp INTEGER NOT NULL,
                  description TEXT,
                  youtubeID TEXT NOT NULL UNIQUE,
                  subtitles TEXT,
                  filename TEXT NOT NULL,
                  checksum TEXT NOT NULL,
                  thumb BLOB,
                  thumbformat TEXT,
                  duration INTEGER,
                  tags TEXT,
                  language TEXT NOT NULL,
                  width INTEGER NOT NULL,
                  height INTEGER NOT NULL,
                  resolution TEXT NOT NULL,
                  viewcount INTEGER,
                  likecount INTEGER,
                  dislikecount INTEGER,
                  statisticsupdated INTEGER NOT NULL DEFAULT 0,
                  chapters TEXT,
                  oldtitles TEXT,
                  olddescriptions TEXT,
                  filesize INTEGER NOT NULL
              ); """
    #Set encoding
    dbCon.execute("pragma encoding=UTF8")
    #Create tables
    dbCon.execute(cmd)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def upgradeDatabase(dbPath):
    '''Check the database version and upgrade it if not newest

    :param dbPath: Path of the archive database
    :type dbPath: string

    :raises: :class:``sqlite3.Error: Unable to read from database
    '''
    #Connect to database
    dbCon = connectDB(dbPath)
    db = dbCon.cursor()
    #Get database version
    try:
        r = db.execute("SELECT dbversion FROM channel ORDER BY id DESC LIMIT 1;")
        version = r.fetchone()[0]
        del r
    except sqlite3.Error:
        #No version field -> db version 1
        version = 1

    #Check if not up to date
    if version < __dbversion__:
        print("Upgrading database")
        try:
            #Perform upgrade to version 2
            if version < 2:
                db.execute('ALTER TABLE channel ADD COLUMN videos INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE channel ADD COLUMN lastupdate INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE channel ADD COLUMN dbversion INTEGER NOT NULL DEFAULT 1;')
                #Update db version
                version = 2
                db.execute("UPDATE channel SET dbversion = ? WHERE id = 1", (version,))
                dbCon.commit()
            #Perform upgrade to version 3
            if version < 3:
                #Add language info to each video
                r = db.execute("SELECT language FROM channel ORDER BY id DESC LIMIT 1;")
                lang = r.fetchone()[0]
                del r
                db.execute('ALTER TABLE videos ADD COLUMN language TEXT NOT NULL DEFAULT {};'.format(lang))
                #Add video resolution info
                db.execute('ALTER TABLE videos ADD COLUMN width INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE videos ADD COLUMN height INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE videos ADD COLUMN resolution TEXT NOT NULL DEFAULT "";')
                r = db.execute("SELECT id,filename FROM videos;")
                files = r.fetchall()
                dirname = os.path.dirname(dbPath)
                del r
                for f in files:
                    path = os.path.join(dirname, f[1])
                    _, formatString, width, height = readResolution(path)
                    db.execute("UPDATE videos SET width = ?, height = ?, resolution = ? WHERE id = ?", (width, height, formatString, f[0]))
                #Add maxres to channel
                db.execute('ALTER TABLE channel ADD COLUMN maxresolution NOT NULL DEFAULT "default";')
                #Update db version
                version = 3
                db.execute("UPDATE channel SET dbversion = ? WHERE id = 1", (version,))
                dbCon.commit()
            #Perform upgrade to version 4
            if version < 4:
                #Add video statistics
                db.execute('ALTER TABLE videos ADD COLUMN viewcount INTEGER;')
                db.execute('ALTER TABLE videos ADD COLUMN likecount INTEGER;')
                db.execute('ALTER TABLE videos ADD COLUMN dislikecount INTEGER;')
                db.execute('ALTER TABLE videos ADD COLUMN statisticsupdated INTEGER NOT NULL DEFAULT 0;')
                #Update db version
                version = 4
                db.execute("UPDATE channel SET dbversion = ? WHERE id = 1", (version,))
                dbCon.commit()
            #Perform upgrade to version 5
            if version < 5:
                #Add video chapters
                db.execute('ALTER TABLE videos ADD COLUMN chapters TEXT;')
                #Extract chapters from video descriptions
                r = db.execute("SELECT id,description FROM videos;")
                videos = r.fetchall()
                for video in videos:
                    chapters = extractChapters(video[1])
                    if chapters:
                        db.execute("UPDATE videos SET chapters = ? WHERE id = ?;", (chapters, video[0]))
                #Update db version
                version = 5
                db.execute("UPDATE channel SET dbversion = ? WHERE id = 1", (version,))
                dbCon.commit()
            #Perform upgrade to version 6
            if version < 6:
                #Update format
                r = db.execute("SELECT id,width,height FROM videos;")
                videos = r.fetchall()
                del r
                for video in videos:
                    _, f = convertResolution(video[1], video[2])
                    db.execute("UPDATE videos SET resolution = ? WHERE id = ?;", (f, video[0]))
                #Add old titles and desctiption
                db.execute('ALTER TABLE videos ADD COLUMN oldtitles TEXT;')
                db.execute('ALTER TABLE videos ADD COLUMN olddescriptions TEXT;')
                #Update db version
                version = 6
                db.execute("UPDATE channel SET dbversion = ? WHERE id = 1", (version,))
                dbCon.commit()
            #Perform upgrade to version 7
            if version < 7:
                #Add filesize and totalsize column
                db.execute('ALTER TABLE videos ADD COLUMN filesize INTEGER NOT NULL DEFAULT 0;')
                db.execute('ALTER TABLE channel ADD COLUMN totalsize INTEGER NOT NULL DEFAULT 0;')
                #Read filesize
                dirname = os.path.dirname(dbPath)
                r = db.execute("SELECT id,filename FROM videos;")
                videos = r.fetchall()
                del r
                for video in videos:
                    try:
                        b = os.path.getsize(os.path.join(dirname, video[1]))
                        db.execute("UPDATE videos SET filesize = ? WHERE id = ?;", (b, video[0]))
                    except OSError:
                        pass
                db.execute("UPDATE channel SET totalsize = (SELECT sum(filesize) FROM videos);")
                #Update db version
                version = 7
                db.execute("UPDATE channel SET dbversion = ? WHERE id = 1", (version,))
                dbCon.commit()
        except sqlite3.Error as e:
            print("ERROR: Unable to upgrade database (\"{}\")".format(e))
            dbCon.rollback()
            closeDB(dbCon)
            sys.exit(1)

    #Close database
    closeDB(dbCon)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def readResolution(path):
    '''Read the resolution of a video file and return HD indicator
    (0 = SD, 1=720, 2=1080, 3=4K), a format string (e.g. "Full HD", "4K UHD")
    as well as width and height

    :param path: Path to video file
    :type path: string

    :raises: :class:``FileNotFoundError: Unable to find file

    :returns: Tuple with HD indicator, format string, width, and height
    :rtype: tuple(int, string, int, int)
    '''
    #Read image width
    if not os.path.isfile(path):
        raise FileNotFoundError
    try:
        cmd = ["exiftool", "-api", "largefilesupport=1", "-m", "-ImageWidth", "-ImageHeight", path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        process.wait()
        out = process.stdout.read().decode("UTF-8").splitlines()
        width = int(out[0].split(':', 1)[1].strip())
        height = int(out[1].split(':', 1)[1].strip())
    except IndexError:
        raise FileNotFoundError from IndexError
    (hd, formatString) = convertResolution(width, height)
    return hd, formatString, width, height
# ########################################################################### #

# --------------------------------------------------------------------------- #
def convertResolution(width, height):
    '''Takes the width and height, returns HD indicator (0 = SD, 1=720, 2=1080, 3=4K)
    and a format string (e.g. "Full HD", "4K UHD")

    :param width: The video image width in pixels
    :type width: integer
    :param height: The video image height in pixels
    :type height: integer

    :returns: Tuple with HD indicator and format string
    :rtype: tuple(int, string)
    '''
    larger = width if width > height else height
    smaller = height if width > height else width
    if larger < 1200:
        hd = 0
        if larger < 700 and smaller < 400:
            formatString = "LD"
        else:
            formatString = "SD"
    elif 1200 <= larger < 1900:
        hd = 1
        formatString = "HD"
    elif 1900 <= larger < 3500:
        hd = 2
        formatString = "Full HD"
    elif 3500 <= larger < 6000:
        hd = 3
        formatString = "4K UHD"
    else:
        hd = 3
        formatString = "8K UHD"
    return (hd, formatString)
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
                el[key] = decimal(el[key][:-1].replace(',', '.'))
            else:
                el[key] = float(el[key][:-1].replace(',', '.'))

    return int(el["weeks"] * 604800 + el["days"] * 86400 + el["hours"] * 3600 + el["minutes"] * 60 + el["seconds"])
# ########################################################################### #

# --------------------------------------------------------------------------- #
def extractChapters(desc):
    '''Try to read chapter information from the description
    If chapter data is found, it will be returned as a multiline string
    with a line per chapter. The line format is
    hh:mm:ss.sss Chapter Name

    :param desc: The video description
    :type desc: string
    :returns: Chapters or None
    :rtype: string
    '''
    #Check if video has a description
    if not desc:
        return None
    #Setup
    lines = desc.splitlines()
    inChapters = False
    r1 = re.compile("\\d{1,2}:\\d{1,2}")
    r2 = re.compile("\\d{1,2}(:\\d{1,2})?:\\d{2}")
    chapters = []
    #Loop through lines
    for line in lines:
        line = line.strip()
        #Look beginning of chapter list: 0:00, 00:00, 0:00:00 or 00:00:00
        if not inChapters:
            if not line.startswith('0'):
                continue
            if line.startswith('0:00') or line.startswith('00:00') or line.startswith('0:0:00'):
                inChapters = True
            else:
                continue
        #Look for end of chapter list
        else:
            if not r1.match(line):
                inChapters = False
                break
        #Parse chapter info
        ts = r2.search(line).group(0)
        try:
            name = line.split(maxsplit=1)[1]
        except IndexError:
            #No name found, not in a chapter
            inChapters = False
            continue
        if name.startswith('- '):
            name = name.split(maxsplit=1)[1]
        #Normalize time code
        i = ts.count(':')
        if i < 2:
            ts = "00:" + ts
        if not ts[2] == ':':
            ts = "0" + ts
        if not ts[5] == ':':
            ts = ts[0:3] + '0' + ts[3:]
        ts = ts + ".000"
        #Save chapter to list
        chapters.append("{} {}".format(ts, name))
    #Return chapter or none
    return '\n'.join(chapters) if len(chapters) >= 3 else None
# ########################################################################### #

# --------------------------------------------------------------------------- #
def getAPIKey(askWhenMissing=False):
    '''Get the API key from the config or ask for it

    :param askWhenMissing: Whether to ask for an API key if non is found (Default: False)
    :type askWhenMissing: boolean, optional
    :returns: The API key or None
    :rtype: string
    '''
    #Check if test env
    if os.environ.get('YTA_TEST'):
        #Return test API key
        if os.environ.get('YTA_TEST_APIKEY'):
            return os.environ.get('YTA_TEST_APIKEY')
        #In test mode, but no test API key, print warning
        print("WARNING: No test API key given, trying to use \"normal\" API key")

    dirs = AppDirs("ytarchiver", "yta")
    try:
        #Try user data dir (e.g. ~.config, ~/Library/Application Support, AppData\Local)
        apiKey = readAPIKey(os.path.join(dirs.user_data_dir, "ytapikey"))
    except OSError:
        try:
            #Try system data dir first (e.g. /usr/local/share, /Library/Application Support)
            apiKey = readAPIKey(os.path.join(dirs.site_data_dir, "ytapikey"))
        except OSError:
            #No api key
            apiKey = None
    #No API key
    if not apiKey:
        print("WARNING: No Youtube data API key available, unable to load additional metadata")
        #Ask for an API key
        if askWhenMissing:
            q = input("Enter Youtube API key or press enter to continue without (NOT RECOMMENDED): ")
            if q:
                #Save given key
                apiKey = q
                try:
                    os.makedirs(dirs.user_data_dir, exist_ok=True)
                    with open(os.path.join(dirs.user_data_dir, "ytapikey"), 'w') as f:
                        f.write(apiKey)
                except OSError:
                    print("WARNING: Unable to save API key")
                    raise
    return apiKey
# ########################################################################### #

# --------------------------------------------------------------------------- #
def readAPIKey(filePath):
    '''Read the API key from the given file

    :param filePath: The file path to read from
    :type filePath: string
    :returns: The API key
    :rtype: string

    :raises: :class:``OSError: Unable to read API key from file
    '''
    #Open file
    with open(filePath) as f:
        #Read first line
        line = f.readline().strip()
        while line:
            #If line is not a comment, return it as the api key
            if not line.startswith('#'):
                return line
            #Read next line
            line = f.readline().strip()
        #Either no lines or only comments, raise error
        raise OSError
# ########################################################################### #

# --------------------------------------------------------------------------- #
class NoAPIKeyError(Exception):
    '''Raised if no API key was provided'''
# ########################################################################### #

# --------------------------------------------------------------------------- #
def toInt(var):
    '''Cast a variable to integer or return null if not possible'''
    try:
        return int(var)
    except ValueError:
        return None
# ########################################################################### #
