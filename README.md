ytarchiver
==========

ytarchiver.py
-------------

A script to download and archive Youtube content by leveraging [youtube-dl](https://github.com/ytdl-org/youtube-dl). Either a single video
or an entire playlist can be downloaded, the thumbnail and (if available) subtitles will be embedded and a database containing metadata will be created.

Usage:
```
$ ytarchiver.py [-c] DIR SUBLANG YOUTUBEID
```
where `DIR` is the directory in which to store the downloaded files, `SUBLANG` is the subtitle language to include (e.g. `en`) and `YOUTUBEID` is ID used by
YouTube to identify a video or playlist (e.g. `dQw4w9WgXcQ`). The optional `-c` flag instructs the script to verify the integrity of the downloaded
video file using ffmpeg. In addition to the metadata stored inside the video file, a database called *archive.db* is created, where the metadata as
well as a checksum are stored. After youtube-dl completed its process, the script `ytapost.py` will be called automatically to perform the
post-processing steps. The `YOUTUBEID` can be omitted if the specified directory contains a file called *playlist* which contains the ID of the playlist
to archive. The `SUBLANG` can be omitted as well if, in addition to the *playlist* file, the specified directory contains a file called *language* which contains
the subtitle language code (e.g. `en` for English, `de` for German, etc). Alternatively, the playlist and language info can also be stored inside the archive
database along with additional information about the channel. When creating a new archive, a prompt for the channel info appears. They can also be added to
an existing archive database using the `ytainfo.py` script.

ytamissing.py
-------------

A script to find discrepancies between the database and the files (i.e. database entries without the corresponding video file or video files without the
corresponding database entry).

Usage:
```
$ ytamissing.py DIR
```
where `DIR` is the directory containing the video files and the *archive.db* database.

ytacheck.py
-----------

A script to compare the checksums of the video files to the ones stored in the database and optionally perform an integrity check.

Usage:
```
$ ytacheck.py [-c] DIR
```
where `DIR` is the directory containing the video files and the *archive.db* database and the optional `-c` flag results in an additional integrity check
of each file using ffmpeg.

Requirements
------------

*   [python3](https://www.python.org/)
*   [youtube-dl](https://github.com/ytdl-org/youtube-dl)
*   [ffmpeg](https://www.ffmpeg.org/)
*   [exiftool](https://www.sno.phy.queensu.ca/~phil/exiftool/)

License
-------

MIT

