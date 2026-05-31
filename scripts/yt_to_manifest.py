#!/usr/bin/env python3
"""Download a YouTube video/playlist to mp3 and build a Yoto create-manifest.

Personal/family use only. Respect copyright; this is for putting audio a family
already wants onto their own Yoto.

Usage
-----
  list <URL>
      Print the playlist as `index|duration_s|title` lines (no download).
      Use this to plan: Yoto caps a card at ~100 tracks / 5h / 500MB and 60min
      per track, so split long playlists across cards.

  fetch <URL> <outdir> [--indices 1,2,5-9] [--max-min 60]
      Download selected items to <outdir> as zero-padded mp3s
      (NN - Title.mp3) and write <outdir>/manifest.json ready for
      `yoto_api.py create --manifest`. Skips files already downloaded
      (resumable). --indices selects playlist positions (1-based, ranges ok).
      --max-min skips items longer than N minutes (default 60, Yoto's per-track
      limit). A single-video URL is treated as one item.

Notes
- Requires yt-dlp (auto-installed via `python -m pip install --user yt-dlp`)
  and ffmpeg on PATH.
- Titles are cleaned for display (strip emojis/leading junk) but kept meaningful.
- The manifest's "title"/"description" are left blank for you to fill (the model
  should set a playlist title and bilingual description before `create`).
"""
import json
import os
import re
import subprocess
import sys


def ensure_ytdlp():
    """Ensure yt-dlp is importable, installing via pip if needed."""
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       capture_output=True, check=True)
    except Exception:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user",
                        "yt-dlp"], check=True)


# YouTube periodically breaks the default player client ("video not available /
# formats may be missing"). These clients reliably work around it; try in order.
PLAYER_CLIENTS = ["android", "ios", "tv", "web_safari"]


def ytdlp(args):
    """Run yt-dlp as a subprocess with the given arguments.

    Args:
        args: List of CLI arguments to pass to yt-dlp.

    Returns:
        A subprocess.CompletedProcess instance.
    """
    return subprocess.run([sys.executable, "-m", "yt_dlp"] + args,
                          capture_output=True, text=True, encoding="utf-8")


def ytdlp_dl(base_args, url):
    """Run a download trying each player client until one succeeds.

    Args:
        base_args: Base yt-dlp arguments (format/output options).
        url:       The YouTube URL to download.

    Returns:
        The CompletedProcess from the last (or successful) attempt.
    """
    last = None
    for pc in PLAYER_CLIENTS:
        r = ytdlp(base_args + ["--extractor-args",
                               "youtube:player_client=" + pc, url])
        last = r
        if r.returncode == 0:
            return r
    return last


def clean_title(t):
    """Strip emojis, tidy whitespace, and truncate a track title.

    Args:
        t: Raw title string from YouTube.

    Returns:
        Cleaned title, max 120 characters.
    """
    # drop common emoji and tidy whitespace; keep letters/accents/punctuation
    t = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", t)
    t = re.sub(r"\s+", " ", t).strip(" -–—\t")
    return t[:120] or "Untitled"


def parse_indices(spec):
    """Parse a comma-separated index spec like '1,3,5-9' into a set of ints.

    Args:
        spec: Index specification string (1-based, ranges with '-').

    Returns:
        A set of integer indices.
    """
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


def cmd_list(url):
    """Subcommand: list playlist items as index|duration_s|title lines.

    Args:
        url: YouTube video or playlist URL.

    Returns:
        yt-dlp's exit code.
    """
    ensure_ytdlp()
    r = ytdlp(["--flat-playlist", "--print",
               "%(playlist_index)s|%(duration)s|%(title)s", url])
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-500:])
    return r.returncode


def cmd_fetch(url, outdir, indices=None, max_min=60):
    """Subcommand: download selected items as mp3 and write a manifest.

    Args:
        url:     YouTube video or playlist URL.
        outdir:  Directory to save mp3 files and manifest.json.
        indices: Optional index spec string (e.g. '1-5,9') to select items.
        max_min: Skip items longer than this many minutes (default 60).

    Returns:
        Exit code (always 0).
    """
    ensure_ytdlp()
    os.makedirs(outdir, exist_ok=True)
    # enumerate items
    r = ytdlp(["--flat-playlist", "--print",
               "%(playlist_index)s\t%(duration)s\t%(id)s\t%(title)s", url])
    items = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        idx, dur, vid, title = parts[0], parts[1], parts[2], "\t".join(parts[3:])
        try:
            idx = int(idx)
        except ValueError:
            idx = len(items) + 1
        items.append({"idx": idx, "dur": dur, "id": vid, "title": title})
    if not items:  # single video
        r = ytdlp(["--print", "%(duration)s\t%(id)s\t%(title)s", url])
        p = r.stdout.strip().split("\t")
        if len(p) >= 3:
            items = [{"idx": 1, "dur": p[0], "id": p[1], "title": p[2]}]

    sel = parse_indices(indices) if indices else None
    tracks = []
    for it in items:
        if sel and it["idx"] not in sel:
            continue
        if "[Private video]" in it["title"] or "[Deleted video]" in it["title"]:
            print("skip %02d private/deleted" % it["idx"]); continue
        try:
            dur = int(it["dur"])
        except (ValueError, TypeError):
            dur = 0
        if max_min and dur and dur > max_min * 60:
            print("skip %02d too long (%dmin > %dmin): %s"
                  % (it["idx"], dur // 60, max_min, it["title"][:40]))
            continue
        title = clean_title(it["title"])
        safe = re.sub(r"[^\w\s-]", "", title).strip()[:60]
        base = "%02d - %s" % (it["idx"], safe)
        mp3 = os.path.join(outdir, base + ".mp3")
        if not os.path.isfile(mp3):
            print("downloading %02d %s" % (it["idx"], title[:50]))
            dr = ytdlp_dl(["-x", "--audio-format", "mp3", "--audio-quality", "5",
                           "-o", os.path.join(outdir, base + ".%(ext)s")],
                          "https://www.youtube.com/watch?v=" + it["id"])
            if dr.returncode != 0 or not os.path.isfile(mp3):
                print("  FAILED %02d: %s" % (it["idx"], dr.stderr[-160:]))
                continue
        tracks.append({"file": mp3, "title": title})

    manifest = {"title": "", "description": "", "tracks": tracks}
    mpath = os.path.join(outdir, "manifest.json")
    json.dump(manifest, open(mpath, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("manifest %s tracks=%d" % (mpath, len(tracks)))
    return 0


def main():
    """CLI entry point. Parse subcommand (list/fetch) from argv.

    Returns:
        Exit code (0 success, 2 usage).
    """
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 2
    if a[0] == "list" and len(a) >= 2:
        return cmd_list(a[1])
    if a[0] == "fetch" and len(a) >= 3:
        indices = a[a.index("--indices") + 1] if "--indices" in a else None
        max_min = int(a[a.index("--max-min") + 1]) if "--max-min" in a else 60
        return cmd_fetch(a[1], a[2], indices, max_min)
    print(__doc__); return 2


if __name__ == "__main__":
    raise SystemExit(main())
