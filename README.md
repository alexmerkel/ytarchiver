ytarchiver
==========

ytarchiver.py
-------------

A script to download and archive Youtube content by leveraging [youtube-dl](https://github.com/ytdl-org/youtube-dl). Either a single video
or an entire playlist can be downloaded, the thumbnail and (if available) subtitles will be embedded and a database containing metadata will be created.

Usage:
```
$ ytarchiver.py [-a] [-c] [-s] DIR [LANG] [VIDEO]
```
where `DIR` is the directory in which to store the downloaded files, `LANG` is the subtitle language to include (e.g. `en`) and `VIDEO` is the ID or URL used by
YouTube to identify a video or playlist (e.g. `dQw4w9WgXcQ`). The optional `-c` flag instructs the script to verify the integrity of the downloaded
video file using ffmpeg. In addition to the metadata stored inside the video file, a database called `archive.db` is created, where the metadata as
well as a checksum are stored. After youtube-dl completed its process, the script `ytapost.py` will be called automatically to perform the
post-processing steps. The `VIDEO` can be omitted if the specified directory contains a file called `playlist` which contains the ID of the playlist
to archive. The `LANG` can be omitted as well if, in addition to the `playlist` file, the specified directory contains a file called `language` which contains
the subtitle language code (e.g. `en` for English, `de` for German, etc). Alternatively, the playlist and language info can also be stored inside the archive
database along with additional information about the channel. This is the recommended way when archiving a channel where the archive is updated as new videos
are added. When creating a new archive, a prompt for the channel info appears. They can also be added to an existing archive database using the `ytainfo.py` script.

To update multiple channel archives that are each contained in their own subfolder, the `-a` flag can be used. This will update all archives contained in
(first level) subdirectories of the given `DIR`.

The script is extracting additional metadata, such as the time of publishing and the tags, from the Youtube Data API which requires an API key.
The key can be obtained by visiting https://console.developers.google.com/apis/api/youtube.googleapis.com, creating a new project, enabling the
YouTube Data API, and creating a new API Key credential. `ytarchiver` is looking for the API key in a file called `ytapikey` in the users config folder.
When non exists, the user will be asked for an API key which will be stored for future use. It is highly recommended to add an API key.
The quota cost for each video is 1. Thus, when applying the default daily query quota of 10000, the metadata lookup can be performed for 10000 videos per
day before hitting the limit.

Using the additional `-s` flag, the statistics (view count, like and dislike count) can be updated for all videos in the archive. This requires an API key
(see above) and has a unit cost of 1 per 30 videos. Thus, when applying the default daily query quota of 10000, the statistics update can be performed
for 300000 videos per day before hitting the limit. When using this option with the `-a` flag, a `statistics.db` is created which contains information about
all the subdirectory archives, when they were last updated and if this update was complete or was aborted early due the max API request per day counter
being reached. This counter is also stored inside the database and currently defaults to 100000. Lastly, an `autoupdate` flag can be set inside this database
which directs `ytarchiver` to always update the statistics when being called for this directory with the `-a` flag.

More flags an options are described in the help:
```
usage: ytarchiver [-h] [-a] [-c] [-s | -u | -x] [-r] [-8k | -4k | -hd] [-V] [-f FILE] DIR [LANG] [VIDEO]

Download and archive Youtube videos or playlists

positional arguments:
  DIR                   The directory to work in
  LANG                  The video language (read from the database if not given)
  VIDEO                 The Youtube video or playlist ID (read from the database if not given)

optional arguments:
  -h, --help            show this help message and exit
  -a, --all             Run archiver for all subdirectories with archive databases. In this mode, LANG and VIDEO will always be read from the databases
  -c, --check           Check each file after download
  -s, --statistics      Update the video statistics
  -u, --captions        List videos where captions were added since archiving (forces -s)
  -x, --amendcaptions   Download captions were they were added since archiving (forces -u and consequently -s)
  -r, --replace         Replace an existing video (a video ID has to be provided)
  -8k, --8K             Limit download resolution to 8K
  -4k, --4K             Limit download resolution to 4K (default)
  -hd, --HD             Limit download resolution to full HD
  -V, --version         show program's version number and exit
  -f FILE, --file FILE  Read IDs to archive from a batch file with one ID per line
```

ytamissing.py
-------------

A script to find discrepancies between the database and the files (i.e. database entries without the corresponding video file or video files without the
corresponding database entry).

Usage:
```
$ ytamissing.py DIR
```
where `DIR` is the directory containing the video files and the `archive.db` database.

ytacheck.py
-----------

A script to compare the checksums of the video files to the ones stored in the database and optionally perform an integrity check.

Usage:
```
$ ytacheck.py [-c] DIR
```
where `DIR` is the directory containing the video files and the `archive.db` database and the optional `-c` flag results in an additional integrity check
of each file using ffmpeg.

Requirements
------------

*   [python3](https://www.python.org/)
*   [ffmpeg](https://www.ffmpeg.org/)
*   [exiftool](https://www.sno.phy.queensu.ca/~phil/exiftool/)
*   [AtomicParsley](http://atomicparsley.sourceforge.net/)

*   [youtube_dl](https://pypi.org/project/youtube_dl/)
*   [requests](https://pypi.org/project/requests/)
*   [pycountry](https://pypi.org/project/pycountry/)
*   [pytz](https://pypi.org/project/pytz/)
*   [appdirs](https://pypi.org/project/appdirs/)

License
-------

MIT

