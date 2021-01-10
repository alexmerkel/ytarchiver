#!/usr/bin/env python3
''' common functions for the test suite of ytarchiver '''

import os

# --------------------------------------------------------------------------- #
def deleteIfExists(path):
    '''Deletes the file at path if it exists'''
    try:
        os.remove(path)
    except OSError:
        pass
# ########################################################################### #
