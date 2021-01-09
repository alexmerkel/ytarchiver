#!/usr/bin/env python3
''' unit test suite for ytacommon '''

import os
import sys
import pytest
import common

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ytacommon

TESTDATA = os.path.join(os.path.dirname(__file__), "testdata")

# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def setup():
    '''Common setup'''
    common.setTestMode()
    #common.setTestAPIKey()
    yield
    common.unsetTestMode()
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("string,expected", [("PT8S", 8), ("PT34S", 34), ("PT3M14S", 194), ("PT28M31S", 1711), ("PT1H28M55S", 5335), ("PT1H16S", 3616), ("P4DT4H1S", 360001), ("P1DT36M41S", 88601), ("P2W3DT13H25M19S", 1517119)], ids=["sec", "two_sec", "sec+min", "sec+two_min", "sec+min+hour", "sec+hour", "day+hour+sec", "day+min+sec", "week+day+hour+min+sec"])
def test_convertDuration(string, expected):
    '''Test the duration conversion'''
    #Convert
    received = ytacommon.convertDuration(string)
    #Compare
    assert received == expected
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("num", [1, 2, 3, 4, 5, 6], ids=["default", "only_two", "unicode", "split_second", "split_first", "formats"])
def test_extractChapters(num):
    '''Test the chapter extraction'''
    #Read description
    descPath = os.path.join(TESTDATA, "testdesc", "{}.desc".format(num))
    with open(descPath) as f:
        desc = f.read()
    #Read expected chapters
    chaptersPath = os.path.join(TESTDATA, "testdesc", "{}.chapters".format(num))
    with open(chaptersPath) as f:
        expected = f.read()
    if not expected:
        expected = None
    #Extract chapters
    received = ytacommon.extractChapters(desc)
    #Compare
    assert received == expected
# ########################################################################### #
