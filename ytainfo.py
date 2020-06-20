#!/usr/bin/env python3
''' ytainfo - add channel info to archive database '''

import os
import sys
import argparse
import requests
import ytacommon as yta

# --------------------------------------------------------------------------- #
def addInfo(args):
    '''Add channel info to the archive database

    :param args: The command line arguments given by the user
    :type args: list
    '''
    parser = argparse.ArgumentParser(prog="ytainfo", description="Add channel info to exising archive databases")
    parser.add_argument("DIR", help="The directory containing the archive database to work on")
    args = parser.parse_args()

    path = os.path.normpath(os.path.abspath(args.DIR))
    dbPath = os.path.join(path, "archive.db")
    if not os.path.isdir(path) or not os.path.isfile(dbPath):
        parser.error("DIR must be a directory containg an archive database")

    #Check if database needs upgrade
    yta.upgradeDatabase(dbPath)

    add(dbPath)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def add(dbPath):
    '''Add channel info to the archive database

    :param dbPath: The path of the archive database
    :type dbPath: string
    '''
    #Create/connect database
    db = createOrConnectDB(dbPath)
    print(yta.color.BOLD + "ADDING CHANNEL INFO" + yta.color.END)
    #Get channel name
    while True:
        q = input(yta.color.BOLD + "Channel name: " + yta.color.END)
        if q:
            break
    name = q.strip()
    #Get channel url
    while True:
        q = input(yta.color.BOLD + "Channel url: " + yta.color.END)
        if q:
            break
    url = q.strip()
    #Get playlist name
    while True:
        q = input(yta.color.BOLD + "Video playlist: " + yta.color.END)
        if q:
            break
    playlist = q.strip()
    #Get channel language
    while True:
        q = input(yta.color.BOLD + "Channel language code: " + yta.color.END)
        if q:
            break
    language = q.strip()
    #Get channel Description
    print(yta.color.BOLD + "Channel description (Press Ctrl-D [Ctrl-Z on WIN] directly to skip or after input to save):" + yta.color.END)
    desc = []
    while True:
        try:
            line = input()
            desc.append(line)
        except EOFError:
            break
    if desc:
        desc = '\n'.join(desc)
    else:
        desc = None
    #Get join date
    q = input(yta.color.BOLD + "Join date (YYYY-MM-DD) or enter to skip: " + yta.color.END)
    if q:
        joined = q.strip()
    else:
        joined = None
    #Get location
    q = input(yta.color.BOLD + "Location (or enter to skip): " + yta.color.END)
    if q:
        location = q.strip()
    else:
        location = None
    #Get links
    print(yta.color.BOLD + "Add links: Prettyname first, then the url. Enter to continue" + yta.color.END)
    links = ""
    i = 0
    while True:
        i += 1
        q1 = input("{}Prettyname no. {} (or enter to continue): {}".format(yta.color.BOLD, i, yta.color.END))
        if not q1:
            break
        q2 = input("{}URL no. {}: {}".format(yta.color.BOLD, i, yta.color.END))
        if not q2:
            print("ERROR: URL must be specified")
            continue
        links += q1.strip() + '\t' + q2.strip() + '\n'
    if not links:
        links = None
    #Get profile picture
    while True:
        q = input(yta.color.BOLD + "Profile picture URL (or enter to skip): " + yta.color.END)
        if not q:
            profile = None
            profileformat = None
            break
        try:
            [profile, profileformat] = yta.loadImage(q.strip())
            break
        except requests.exceptions.HTTPError:
            print("ERROR: Invalid URL")
            continue
    #Get banner image
    while True:
        q = input(yta.color.BOLD + "Banner image URL (or enter to skip): " + yta.color.END)
        if not q:
            banner = None
            bannerformat = None
            break
        try:
            [banner, bannerformat] = yta.loadImage(q.strip())
            break
        except requests.exceptions.HTTPError:
            print("ERROR: Invalid URL")
            continue

    insert = "INSERT INTO channel(name, url, playlist, language, description, location, joined, links, profile, profileformat, banner, bannerformat, videos, lastupdate, dbversion) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    db.execute(insert, (name, url, playlist, language, desc, location, joined, links, profile, profileformat, banner, bannerformat, 0, 0, yta.__dbversion__))
    print(yta.color.BOLD + "FINISHED ADDING CHANNEL INFO" + yta.color.END)

    yta.closeDB(db)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def createEmpty(dbPath):
    '''Create a database without adding information

    :param dbPath: The path of the archive database
    :type dbPath: string
    '''
    #Create/connect database
    db = createOrConnectDB(dbPath)
    insert = "INSERT INTO channel(name, url, playlist, language, videos, lastupdate, dbversion) VALUES(?,?,?,?,?,?,?)"
    db.execute(insert, ('', '', '', '', 0, 0, yta.__dbversion__))

    yta.closeDB(db)
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
    tableCmd = """ CREATE TABLE IF NOT EXISTS channel (
                       id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
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
                       dbversion INTEGER NOT NULL
                   ); """

    #Create database
    dbCon = yta.connectDB(path)
    #Set encoding
    dbCon.execute("pragma encoding=UTF8")
    #Create tables
    dbCon.execute(tableCmd)
    #Return database connection
    return dbCon
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        addInfo(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
