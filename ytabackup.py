#!/usr/bin/env python3
''' ytabackup - backup archive databases '''

import os
import sys
import errno
import time
import argparse
from zipfile import ZipFile, ZIP_DEFLATED
import sqlite3
import ytacommon as yta

# --------------------------------------------------------------------------- #
def backup(args):
    '''Update the archive databases

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Parse arguments
    parser = argparse.ArgumentParser(prog="ytabackup", description="Backup the archive database")
    parser.add_argument("-a", "--all", action="store_const", dest="all", const=True, default=False, help="Run backup for all subdirectories with archive databases. In this mode, the backups are stored in a central folder")
    parser.add_argument("DIR", help="The directory to work in")
    args = parser.parse_args()

    #Validate path
    path = os.path.normpath(os.path.abspath(args.DIR))
    if not os.path.isdir(path):
        parser.error("DIR must be a directory containg an archive database or contain subdirectories with database")

    #Create backup dir if it doesn't already exist
    backupDir = os.path.join(path, "backups")
    try:
        os.makedirs(backupDir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print("ERROR: Unable to create backup directory at \'{}\'".format(backupDir))
            return

    #Check if all subdirs
    if args.all:
        print("BACKING UP ALL CHANNEL DATABASES IN \'{}\'\n".format(path))
        #Get subdirs in path
        subdirs = [os.path.join(path, name) for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
        subdirs = [sub for sub in subdirs if os.path.isfile(os.path.join(sub, "archive.db"))]
        if not subdirs:
            print("ERROR: No subdirs with archive databases at \'{}\'".format(path))
            return
        for subdir in subdirs:
            name = os.path.basename(os.path.normpath(subdir))
            #Create channel backup dir if it doesn't already exist
            channelBackupDir = os.path.join(backupDir, name)
            try:
                os.makedirs(channelBackupDir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    print("ERROR: Unable to create channel backup directory for \'{}\'".format(channelBackupDir))
                    return
            #Backup database
            dbPath = os.path.join(subdir, "archive.db")
            print("Backing up \'{}\' db".format(name))
            backupDB(dbPath, channelBackupDir)
        print("\nDONE!")
    #Just one channel
    else:
        dbPath = os.path.join(path, "archive.db")
        if not os.path.isfile(dbPath):
            print("ERROR: No archive database found at \'{}\'".format(path))
        backupDB(dbPath, backupDir)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def backupDB(dbPath, backupDir):
    '''Create a backup copy of the database in the specified directory

    :param dbPath: Path of the database to back up
    :type dbPath: string
    :param directory: Path of the directory in which to store backup
    :type directory: string

    :raises: :class:``sqlite3.Error: Unable to backup database

    :returns: True if backup successful, otherwise False
    :rtype: boolean
    '''
    #Connect to database
    con = yta.connectDB(dbPath)
    #Check database integrity
    if not checkDB(con):
        print("ERROR: Database \'{}\' has integrity error".format(dbPath))
        return False
    #Create db backup
    timestamp = int(time.time())
    backupPath = os.path.join(backupDir, "{}.db".format(timestamp))
    bck = sqlite3.connect(backupPath)
    con.backup(bck)
    bck.close()
    #Zip backup
    with ZipFile(backupPath + ".zip", 'w') as zipf:
        zipf.write(backupPath, arcname="{}.db".format(timestamp), compress_type=ZIP_DEFLATED)
    #Verify zip
    with ZipFile(backupPath + ".zip", 'r') as zipf:
        if zipf.testzip():
            print("ERROR: Database \'{}\' backup zip error".format(dbPath))
            return False
    #Remove uncompressed backup
    os.remove(backupPath)
    return True
# ########################################################################### #

# --------------------------------------------------------------------------- #
def checkDB(con):
    '''Check integrity of database

    :param con: Connection to the database
    :type con: sqlite3.Connection

    :raises: :class:``sqlite3.Error: Unable to check database

    :returns: True if check passed, otherwise False
    :rtype: boolean
    '''
    r = con.execute("pragma integrity_check;")
    res = r.fetchall()
    try:
        return res[0][0] == "ok"
    except IndexError:
        return False
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        backup(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
