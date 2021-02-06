#!/usr/bin/env python3
''' unit test suite for ytaformats '''

import os
import sqlite3
import subprocess
import pytest

import ytaformats

# --------------------------------------------------------------------------- #
@pytest.mark.network
@pytest.mark.tube
@pytest.mark.parametrize("mode", ["HD", "4K", "8K", "vid"],
    ids=["channelHD", "channel4K", "channel8K", "video"])
def test_formatsFunc(capsys, mode):
    playlist = "UUsiMuEX8d_OnJe3u8i4FiqQ"
    #Switch by mode
    #Test channel in HD mode
    if mode == "HD":
        #Set expected
        exp = ["Number of videos: 6", "Formats:", "1080: 3 (Total: 03:00, Avg: 01:00)", "720: 1 (Total: 01:00, Avg: 01:00)", "SD: 2 (Total: 02:00, Avg: 01:00)"]
        #Get formats
        ytaformats.main(['-hd', playlist])
        #Process output
        rec = _processOutput(capsys.readouterr(), 5)
        #Compare
        assert rec == exp
    #Test channel in 4K mode
    elif mode == "4K":
        #Set expected
        exp = ["Number of videos: 6", "Formats:", "4K: 2 (Total: 02:00, Avg: 01:00)", "1080: 1 (Total: 01:00, Avg: 01:00)", "720: 1 (Total: 01:00, Avg: 01:00)", "SD: 2 (Total: 02:00, Avg: 01:00)"]
        #Get formats
        ytaformats.main(['-4k', playlist])
        #Process output
        rec = _processOutput(capsys.readouterr(), 6)
        #Compare
        assert rec == exp
    #Test channel in 8K mode
    elif mode == "8K":
        #Set expected
        exp = ["Number of videos: 6", "Formats:", "8K: 1 (Total: 01:00, Avg: 01:00)", "4K: 1 (Total: 01:00, Avg: 01:00)", "1080: 1 (Total: 01:00, Avg: 01:00)", "720: 1 (Total: 01:00, Avg: 01:00)", "SD: 2 (Total: 02:00, Avg: 01:00)"]
        #Get formats
        ytaformats.main(['-8k', playlist])
        #Process output
        rec = _processOutput(capsys.readouterr(), 7)
        #Compare
        assert rec == exp
    #Test single video
    elif mode == "vid":
        #Set expected
        exp = ["Example 6 (01:00)", "315 - 3840x2160 (2160p60)+140 - audio only (tiny)"]
        #Get formats
        ytaformats.main(["19qObzFI878"])
        #Process output
        rec = _processOutput(capsys.readouterr(), 2)
        #Compare
        assert rec == exp
    #Unknown mode
    else:
        pytest.fail("Unknown mode: {}".format(mode))
# ########################################################################### #

# --------------------------------------------------------------------------- #
def _processOutput(captured, lines):
    out = captured.out.strip().splitlines()
    return [l.strip() for l in out[-lines:]]
# ########################################################################### #

# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("sec,exp",
    [(47232, "13:07:12"), (4864, "01:21:04"), (3144, "52:24"), (291, "04:51"), (25, "00:25"), (4, "00:04")],
    ids=["hours", "hour", "mins", "min", "secs", "sec"])
def test_secToTime(sec, exp):
    ''' Test secToTime '''
    #Convert
    rec = ytaformats.secToTime(sec)
    #Compare
    assert rec == exp
# ########################################################################### #
