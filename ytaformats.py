#!/usr/bin/env python3
''' ytaformats - print download formats used by ytarchiver '''

import sys
import argparse
import youtube_dl
import ytacommon as yta

# --------------------------------------------------------------------------- #
def main(args):
    '''Main function, print info about the download formats used

    :param args: The command line arguments given by the user
    :type args: list
    '''

    #Parse arguments
    parser = argparse.ArgumentParser(prog="ytaformats", description="Print download formats used by ytarchiver")
    parser.add_argument("-8k", "--8K", action="store_const", dest="quality", const="8k", help="Limit download resolution to 8K")
    parser.add_argument("-4k", "--4K", action="store_const", dest="quality", const="4k", help="Limit download resolution to 4K (default)")
    parser.add_argument("-hd", "--HD", action="store_const", dest="quality", const="hd", help="Limit download resolution to full HD")
    parser.add_argument("VIDEO", help="The Youtube video or playlist ID")
    args = parser.parse_args()

    #Set format string
    dlformat = yta.getFormatString(args.quality)

    #Set options
    ydlOpts = {"call_home": False, "quiet": True, "format": dlformat, "ignoreerrors": True, "no_warnings": True}

    #Get info
    videos = []
    with youtube_dl.YoutubeDL(ydlOpts) as ydl:
        info = ydl.extract_info(args.VIDEO, download=False)
        try:
            for e in info.get('entries'):
                if e:
                    videos.append({"id": e["id"], "title": e["title"], "duration": e["duration"], "width": e["width"], "height": e["height"], "format": e["format"]})
        except TypeError:
            videos.append({"id": info["id"], "title": info["title"], "duration": info["duration"], "width": info["width"], "height": info["height"], "format": info["format"]})

    #Init counters and duration
    counter = {"sd": 0, "720": 0, "1080": 0, "4k": 0, "8k": 0}
    duration = {"sd": 0, "720": 0, "1080": 0, "4k": 0, "8k": 0}

    #Loop through videos
    i = 0
    l = len(videos)
    for v in videos:
        i += 1
        #Print info
        msg = ""
        if l > 1:
            msg += "Video {} of {}: \n\t".format(i, l)
        msg += v["title"]
        msg += " ({})".format(secToTime(v["duration"]))
        msg += "\n\t{}".format(v["format"])
        print(msg)
        #Count
        if v["width"] > 4000:
            counter["8k"] += 1
            duration["8k"] += v["duration"]
        elif v["width"] > 2000:
            counter["4k"] += 1
            duration["4k"] += v["duration"]
        elif v["width"] > 1500:
            counter["1080"] += 1
            duration["1080"] += v["duration"]
        elif v["width"] > 1000:
            counter["720"] += 1
            duration["720"] += v["duration"]
        else:
            counter["sd"] += 1
            duration["sd"] += v["duration"]

    #Print statistics
    if l > 1:
        msg = "\nNumber of videos: {}\nFormats:\n".format(l)
        if counter["8k"] > 0:
            msg += "\t  8K: {} (Total: {}, Avg: {})\n".format(counter["8k"], secToTime(duration["8k"]), secToTime(duration["8k"]//counter["8k"]))
        if counter["4k"] > 0:
            msg += "\t  4K: {} (Total: {}, Avg: {})\n".format(counter["4k"], secToTime(duration["4k"]), secToTime(duration["4k"]//counter["4k"]))
        if counter["1080"] > 0:
            msg += "\t1080: {} (Total: {}, Avg: {})\n".format(counter["1080"], secToTime(duration["1080"]), secToTime(duration["1080"]//counter["1080"]))
        if counter["720"] > 0:
            msg += "\t 720: {} (Total: {}, Avg: {})\n".format(counter["720"], secToTime(duration["720"]), secToTime(duration["720"]//counter["720"]))
        if counter["sd"] > 0:
            msg += "\t  SD: {} (Total: {}, Avg: {})\n".format(counter["sd"], secToTime(duration["sd"]), secToTime(duration["sd"]//counter["sd"]))
        print(msg)
# ########################################################################### #

# --------------------------------------------------------------------------- #
def secToTime(sec):
    '''Convert duration in seconds to MM:SS or HH:MM:SS string

    :param sec: The duration in seconds
    :type args: int
    :returns: The duration as MM:SS or HH:MM:SS
    :rtype: string
    '''
    h = int(sec // 3600)
    sec = sec % 3600
    m = int(sec // 60)
    sec = int(sec % 60)
    if h > 0:
        return "{:02d}:{:02d}:{:02d}".format(h, m, sec)
    return "{:02d}:{:02d}".format(m, sec)
# ########################################################################### #

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print("Aborted!")
# ########################################################################### #
