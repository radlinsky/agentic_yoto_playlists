#!/usr/bin/env python3
"""Fetch free/legal audio into a playlist folder and normalise to mp3.

This is a thin convenience wrapper around tools the skill may install on demand
(internetarchive / yt-dlp) plus ffmpeg. It does NOT decide what is legal to
download -- the caller (the agent, with the user) must only point it at
public-domain or Creative-Commons sources. See reference/sources.md.

Modes (pick one):
    python download_audio.py --ia IDENTIFIER OUTDIR [--glob "*.mp3"]
        Download an Internet Archive item's audio with the `ia` CLI.
    python download_audio.py --url URL OUTDIR
        Direct-download a single audio file.
    python download_audio.py --ytdlp URL OUTDIR
        Download audio from a (Creative-Commons) video URL via yt-dlp.
    python download_audio.py --convert OUTDIR
        Convert every non-mp3 audio file in OUTDIR to 128 kbps mp3 with ffmpeg.

All modes are safe to re-run; existing files are left in place.
"""
import os
import subprocess
import sys

AUDIO_EXT = (".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus", ".mp3", ".wma")


def run(cmd: list) -> int:
    print("+ " + " ".join(cmd), file=sys.stderr)
    return subprocess.run(cmd).returncode


def ensure(pip_pkg: str, probe: list) -> bool:
    try:
        subprocess.run(probe, capture_output=True, check=True)
        return True
    except Exception:
        print("Installing %s ..." % pip_pkg, file=sys.stderr)
        rc = run([sys.executable, "-m", "pip", "install", "--user", pip_pkg])
        return rc == 0


def convert_dir(outdir: str) -> None:
    for fn in sorted(os.listdir(outdir)):
        path = os.path.join(outdir, fn)
        ext = os.path.splitext(fn)[1].lower()
        if ext in AUDIO_EXT and ext != ".mp3":
            mp3 = os.path.splitext(path)[0] + ".mp3"
            if os.path.exists(mp3):
                continue
            run(["ffmpeg", "-y", "-i", path, "-c:a", "libmp3lame", "-b:a",
                 "128k", mp3])


def main() -> int:
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    mode = a[0]
    if mode == "--convert":
        convert_dir(a[1])
        return 0
    if mode == "--ia":
        ident, outdir = a[1], a[2]
        glob = "*.mp3"
        if "--glob" in a:
            glob = a[a.index("--glob") + 1]
        os.makedirs(outdir, exist_ok=True)
        if not ensure("internetarchive", ["ia", "--version"]):
            print("ERROR: could not install/find `ia`", file=sys.stderr)
            return 1
        return run(["ia", "download", ident, "--glob", glob,
                    "--destdir", outdir, "--no-directories"])
    if mode == "--ytdlp":
        url, outdir = a[1], a[2]
        os.makedirs(outdir, exist_ok=True)
        if not ensure("yt-dlp", ["yt-dlp", "--version"]):
            print("ERROR: could not install/find yt-dlp", file=sys.stderr)
            return 1
        return run(["yt-dlp", "-x", "--audio-format", "mp3", "-o",
                    os.path.join(outdir, "%(title)s.%(ext)s"), url])
    if mode == "--url":
        import urllib.request
        url, outdir = a[1], a[2]
        os.makedirs(outdir, exist_ok=True)
        name = os.path.basename(url.split("?")[0]) or "track.mp3"
        out = os.path.join(outdir, name)
        print("downloading %s -> %s" % (url, out), file=sys.stderr)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(out, "wb") as f:
            f.write(r.read())
        print(out)
        return 0
    print("unknown mode: %s" % mode, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
