#!/usr/bin/env python3
"""Fetch candidate 16x16 icons from the community library at yotoicons.com.

Usage:
    python fetch_icon.py TAG OUTDIR [--n 3]

Searches https://yotoicons.com for TAG, downloads up to N of the most popular
matching PNGs into OUTDIR (named TAG_1.png, TAG_2.png, ...), and normalises each
to a 16x16 PNG. Prints the saved file paths, one per line. Prints nothing and
exits 0 if there are no matches (caller should then fall back to gen_icon.py).

Uses only the Python standard library for fetching; uses Pillow for resizing if
available (otherwise leaves the downloaded PNG as-is).

Note: yotoicons.com is a community gallery. These icons are user-contributed for
Yoto MYO use; this script downloads them for personal/family use only.
"""
import os
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (yoto-playlist-builder skill; personal use)"
BASE = "https://yotoicons.com"


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def find_icon_ids(tag: str) -> list:
    """Return ordered, de-duplicated icon IDs from the search results page."""
    url = "%s/icons?tag=%s&sort=popular" % (BASE, urllib.parse.quote(tag))
    try:
        html = http_get(url).decode("utf-8", "replace")
    except Exception as e:
        print("WARN: search failed: %s" % e, file=sys.stderr)
        return []
    ids = []
    # Match references like /static/uploads/123.png or icons/123 popups.
    for m in re.finditer(r"/static/uploads/(\d+)\.png", html):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    if not ids:
        for m in re.finditer(r"populate_icon_modal\((\d+)", html):
            if m.group(1) not in ids:
                ids.append(m.group(1))
    return ids


def normalize_16(path: str) -> None:
    try:
        from PIL import Image
    except Exception:
        return
    try:
        img = Image.open(path).convert("RGBA")
        if img.size != (16, 16):
            img = img.resize((16, 16), Image.NEAREST)
            img.save(path, "PNG")
    except Exception:
        pass


def main() -> int:
    import urllib.parse  # noqa: F401 (used via urllib.parse below)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = 3
    if "--n" in sys.argv:
        i = sys.argv.index("--n")
        if i + 1 < len(sys.argv):
            n = int(sys.argv[i + 1])
            args = [a for a in args if a != sys.argv[i + 1]]
    if len(args) < 2:
        print("usage: fetch_icon.py TAG OUTDIR [--n 3]", file=sys.stderr)
        return 2
    tag, outdir = args[0], args[1]
    os.makedirs(outdir, exist_ok=True)
    ids = find_icon_ids(tag)[:n]
    saved = []
    for idx, icon_id in enumerate(ids, 1):
        out = os.path.join(outdir, "%s_%d.png" % (re.sub(r"\W+", "_", tag), idx))
        try:
            data = http_get("%s/static/uploads/%s.png" % (BASE, icon_id))
            with open(out, "wb") as f:
                f.write(data)
            normalize_16(out)
            saved.append(out)
        except Exception as e:
            print("WARN: download %s failed: %s" % (icon_id, e), file=sys.stderr)
    for s in saved:
        print(s)
    return 0


# urllib.parse must be importable at module load for find_icon_ids
import urllib.parse  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
