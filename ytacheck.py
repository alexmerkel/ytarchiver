#!/usr/bin/env python3
''' ytacheck - performs integrity checks '''

import os
import sys
import argparse
import subprocess
import sqlite3
import ytacommon as yta

# --------------------------------------------------------------------------- #
def check(args, parsed=False):
    '''Perform integrity checks on files

    :param args: The command line arguments given by the user
    :type args: list
    '''
    if not parsed:
        parser = argparse.ArgumentParser(prog="ytacheck", description="Verify integrity of archived files")
        parser.add_argument("DIR", help="The directory to work in")
        parser.add_argument("-a", "--all", action="store_const", dest="all", const=True, default=False, help="Run checker for all subdirectories with archive databases")
        parser.add_argument("-c", "--check", action="store_const", dest="check", const=True, default=False, help="Perform additional integrity check using ffmpeg")
        args = parser.parse_args()

    #Run checker for all subdirectories
    if args.all:
        checkAll(args)
        return

    #Validate path
    path = os.path.normpath(os.path.abspath(args.DIR))
    dbPath = os.path.join(path, "archive.db")
    if not os.path.isdir(path) or not os.path.isfile(dbPath):
        parser.error("DIR must be a directory containg an archive database")

    #Read filenames and checksums from database
    files = []
    errors = []
    try:
        db = yta.connectDB(dbPath)
        r = db.execute("SELECT youtubeID,filename,checksum FROM videos;")
        for f in r.fetchall():
            files.append({"checksum" : f[2], "name" : f[1], "youtubeID" : f[0]})
    except sqlite3.Error as e:
        print(e)
        return

    for f in files:
        filepath = os.path.join(path, f["name"])
        #CHeck if file exits
        if not os.path.isfile(filepath):
            msg = "ERROR: File \"{}\" missing".format(f["name"])
            print(msg)
            errors.append(msg)
            continue
        #Check movie file
        if args.check:
            cmd = ["ffmpeg", "-v", "error", "-i", filepath, "-f", "null", "-"]
            out, _ = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
            if out:
                msg = "ERROR: File \"{}\" corrupt!".format(f["name"])
                print(msg)
                errors.append(msg)
            else:
                print("File \"{}\" check passed".format(f["name"]))
        #Calculate checksums
        checksum = yta.calcSHA(filepath)

        if not f["checksum"]:
            db.execute("UPDATE videos SET checksum = ? WHERE youtubeID = ?", (checksum, f["youtubeID"]))
            print("WARNING: File \"{}\" no checksum in database, adding {}".format(f["name"], checksum))
        else:
            if f["checksum"] == checksum:
                print("File \"{}\" checksums match".format(f["name"]))
            else:
                msg = "ERROR: Checksum mismatch for file \"{}\" (New checksum: {})".format(f["name"], checksum)
                print(msg)
                errors.append(msg)
    #Close database
    yta.closeDB(db)

    #Print status
    if errors:
        print("\nDONE, {} CORRUPTED FILE(S)".format(len(errors)))
    else:
        print("\nDONE, NO CORRUPTED FILE")
    #Return errors
    return errors
# ########################################################################### #

# --------------------------------------------------------------------------- #
def checkAll(args):
    '''Call check script for all subdirs

    :param args: The command line arguments given by the user
    :type args: list
    '''
    #Set all to false for susequent calls
    args.all = False

    #Get path
    path = os.path.normpath(os.path.abspath(args.DIR))
    #Get subdirs in path
    subdirs = [os.path.join(path, name) for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    subdirs = [sub for sub in subdirs if os.path.isfile(os.path.join(sub, "archive.db"))]
    if not subdirs:
        print("ERROR: No subdirs with archive databases at \'{}\'".format(path))
        return
    #Print message
    print("CHECKING ALL CHANNELS IN \'{}\'\n".format(path))
    #Initiate error log
    errorLog = ""
    #Loop through all subdirs
    for subdir in subdirs:
        name = os.path.basename(os.path.normpath(subdir))
        args.DIR = subdir
        print("\nCHECKING \'{}\'".format(name))
        errors = check(args, True)
        if errors:
            errorLog += '\n\n' + name + '\n' + '\n'.join(errors)
    #Print error log
    if not errorLog:
        errorLog = "No errors\n"
    logFile = os.path.join(path, "log")
    with open(logFile, 'w+') as f:
        f.writelines(errorLog)

    print("\nDONE!")
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        check(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #

