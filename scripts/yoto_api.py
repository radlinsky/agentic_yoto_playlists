#!/usr/bin/env python3
"""Yoto API client for building/updating playlists. Shell-based, no browser.

This is the RELIABLE path (the web editor's in-page fetches get stalled by the
browser-automation extension; the API from the shell does not). It is written to
be driven step-by-step by a small local model: every subcommand does ONE thing
and prints a short, parseable result.

TOKEN: never pass the token on the command line or print it. The script reads it
from (in order): $YOTO_TOKEN, then a token file (default: a `.yoto_token.txt`
next to your playlists, or ~/.yoto_token). Get the token from the logged-in web
app: open https://my.yotoplay.com, DevTools (F12) > Console >
`copy(localStorage.access_token)`, paste into the token file. Tokens last ~24h.

Base URL: https://api.yotoplay.com

Subcommands
-----------
  whoami
      Verify the token works; prints token scopes + expiry. No card data.

  get <cardId>
      Print title, description length, and each track with its current icon
      (yoto:<mediaId> or 'none'). Use this to audit before/after.

  dump <cardId> <outfile.json>
      Save the full raw card JSON (for debugging / backup).

  set-desc <cardId> --file <desc.txt>
      Replace metadata.description with the file's contents (UTF-8). <=500 chars.

  upload-icon <file.png>
      Upload a 16x16 PNG as a custom display icon. Prints `mediaId=<id>` — feed
      that to set-icon. Idempotent: same image returns the same id.

  set-icon <cardId> <trackIndex> <mediaId>
      Set ONE track's 16x16 icon. trackIndex is 1-based across the whole card.

  apply <cardId> --plan <plan.json>
      Do a whole card in one shot. plan.json:
        {
          "description": "EN...\n\nFR...",        # optional
          "icons": { "1": "path/seashell.png",    # 1-based track index -> PNG
                     "3": "path/owl.png" }          # only listed tracks change
        }
      Skips any track that already has an icon unless --force is given.

Exit code 0 on success, non-zero on error. All errors print `ERROR: ...`.
"""
import json
import mimetypes
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

API = "https://api.yotoplay.com"

# Yoto's generic default/placeholder track icon. Tracks showing this have NO
# real custom art, so treat it as "no icon" for idempotency.
DEFAULT_ICON = "yoto:#aUm9i3ex3qqAMYBv-i-O-pYMKuMJGICtR3Vhf289u2Q"


def has_real_icon(track):
    ic = (track.get("display") or {}).get("icon16x16")
    return bool(ic) and ic != DEFAULT_ICON


def set_track_icon(chapter, track, mid):
    """Assign an icon ref to a track (and its chapter), coercing display:null
    -> {} — newly created cards have display=None, not a missing key."""
    if not isinstance(track.get("display"), dict):
        track["display"] = {}
    track["display"]["icon16x16"] = mid
    if not isinstance(chapter.get("display"), dict):
        chapter["display"] = {}
    chapter["display"].setdefault("icon16x16", mid)


# ---------- token & http ----------
def find_token():
    t = os.environ.get("YOTO_TOKEN")
    if t:
        return t.strip()
    candidates = [
        os.environ.get("YOTO_TOKEN_FILE"),
        ".yoto_token.txt",
        os.path.expanduser("~/.yoto_token"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            with open(c, "r", encoding="utf-8") as f:
                return f.read().strip()
    raise SystemExit("ERROR: no token. Set $YOTO_TOKEN or create .yoto_token.txt "
                     "(see module docstring).")


def req(method, path, token, body=None, headers=None, raw=False):
    url = path if path.startswith("http") else API + path
    data = None
    h = {"authorization": "Bearer " + token, "accept": "application/json"}
    if headers:
        h.update(headers)
    if body is not None and not raw:
        data = json.dumps(body).encode("utf-8")
        h["content-type"] = "application/json"
    elif raw and body is not None:
        data = body
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            txt = resp.read().decode("utf-8", "replace")
            return resp.status, txt
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, "EXC " + str(e)


def get_card(cardId, token):
    st, txt = req("GET", "/content/" + cardId, token)
    if st != 200:
        raise SystemExit("ERROR: GET card %s -> HTTP %s: %s" % (cardId, st, txt[:200]))
    j = json.loads(txt)
    return j.get("card", j)


def iter_tracks(card):
    """Yield (chapterIdx, trackIdx_global, chapter, track)."""
    g = 0
    for ci, ch in enumerate(card.get("content", {}).get("chapters", [])):
        for tr in ch.get("tracks", []):
            g += 1
            yield ci, g, ch, tr


def save_card(card, token):
    """POST the (modified) card back. Yoto expects the content envelope."""
    payload = {
        "cardId": card.get("cardId") or card.get("id"),
        "title": card.get("title"),
        "content": card.get("content"),
        "metadata": card.get("metadata", {}),
    }
    st, txt = req("POST", "/content", token, body=payload)
    if st not in (200, 201):
        raise SystemExit("ERROR: save card -> HTTP %s: %s" % (st, txt[:300]))
    return json.loads(txt) if txt.strip().startswith("{") else {}


# ---------- audio upload + card creation ----------
def upload_audio(path, token, poll_max=120, poll_interval=2.0):
    """Upload one audio file and wait for transcoding. Returns a dict with the
    fields a track needs: {sha, duration, fileSize, channels, format}.

    Flow (verified against the live API):
      1. GET /media/transcode/audio/uploadUrl?sha256=<sha>&filename=<fn>
         -> {upload:{uploadId, uploadUrl}}  (uploadUrl null if already uploaded)
      2. PUT the raw bytes to uploadUrl (S3 signed URL).
      3. Poll GET /media/upload/<uploadId>/transcoded?loudnorm=false
         -> 202 while transcoding, 200 when done with transcode.transcodedSha256
            and transcode.transcodedInfo {duration, channels, fileSize, format}.
    """
    import hashlib
    import time
    with open(path, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    fn = os.path.basename(path)
    st, txt = req("GET", "/media/transcode/audio/uploadUrl?sha256=%s&filename=%s"
                  % (sha, urllib.parse.quote(fn)), token)
    if st != 200:
        raise SystemExit("ERROR: get uploadUrl for %s -> HTTP %s: %s"
                         % (fn, st, txt[:200]))
    up = json.loads(txt)["upload"]
    uid = up["uploadId"]
    if up.get("uploadUrl"):
        put = urllib.request.Request(up["uploadUrl"], data=data,
                                     headers={"Content-Type": "audio/mpeg"},
                                     method="PUT")
        try:
            with urllib.request.urlopen(put, timeout=300) as r:
                if r.status not in (200, 204):
                    raise SystemExit("ERROR: PUT %s -> HTTP %s" % (fn, r.status))
        except urllib.error.HTTPError as e:
            raise SystemExit("ERROR: PUT %s -> HTTP %s: %s"
                             % (fn, e.code, e.read()[:200]))
    for _ in range(poll_max):
        st, txt = req("GET", "/media/upload/%s/transcoded?loudnorm=false" % uid, token)
        if st == 200 and "transcodedSha256" in txt:
            tc = json.loads(txt)["transcode"]
            info = tc.get("transcodedInfo", {})
            return {
                "sha": tc["transcodedSha256"],
                "duration": info.get("duration"),
                "fileSize": info.get("fileSize"),
                "channels": info.get("channels", "stereo"),
                "format": info.get("format", "opus"),
            }
        time.sleep(poll_interval)
    raise SystemExit("ERROR: transcode timed out for %s" % fn)


def make_track(key, title, up, overlay=None):
    """Build a track object from an upload_audio() result."""
    t = {
        "key": key, "title": title,
        "trackUrl": yoto_ref(up["sha"]),
        "type": "audio", "format": up.get("format", "opus"),
        "duration": up.get("duration"), "fileSize": up.get("fileSize"),
        "channels": up.get("channels", "stereo"),
    }
    if overlay:
        t["overlayLabel"] = overlay
    return t


def create_card(title, tracks, token, description=None):
    """Create a NEW card; one chapter per track. Returns the new cardId."""
    chapters = []
    for i, tr in enumerate(tracks, 1):
        k = "%02d" % i
        chapters.append({"key": k, "title": tr["title"],
                         "overlayLabel": str(i), "tracks": [tr]})
    payload = {"title": title, "content": {"chapters": chapters},
               "metadata": {"description": description or ""}}
    st, txt = req("POST", "/content", token, body=payload)
    if st not in (200, 201):
        raise SystemExit("ERROR: create card -> HTTP %s: %s" % (st, txt[:300]))
    card = json.loads(txt).get("card", {})
    return card.get("cardId") or card.get("id")


# ---------- subcommands ----------
def cmd_whoami(args, token):
    import base64
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        info = json.loads(base64.urlsafe_b64decode(payload))
    except Exception as e:
        print("ERROR: cannot decode token: %s" % e)
        return 1
    # live check
    st, _ = req("GET", "/card/family/library", token)
    print("token_ok_format=yes aud=%s exp=%s scopes_has_content=%s "
          "scopes_has_icons=%s live_http=%s" % (
              info.get("aud"), info.get("exp"),
              "user:content:manage" in (info.get("scope", "")),
              "user:icons:manage" in (info.get("scope", "")), st))
    return 0


def cmd_get(args, token):
    card = get_card(args[0], token)
    desc = (card.get("metadata", {}) or {}).get("description", "") or ""
    print("title=%s descLen=%d" % (card.get("title"), len(desc)))
    for _, g, _, tr in iter_tracks(card):
        ic = ((tr.get("display") or {}).get("icon16x16")) or "none"
        print("%2d  %-8s  %s" % (g, ic.replace("yoto:", "")[:8] if ic != "none"
                                 else "NONE", (tr.get("title") or "")[:48]))
    return 0


def cmd_dump(args, token):
    card = get_card(args[0], token)
    with open(args[1], "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=2)
    print("wrote %s" % args[1])
    return 0


def cmd_set_desc(args, token):
    cardId = args[0]
    fpath = args[args.index("--file") + 1]
    with open(fpath, "r", encoding="utf-8") as f:
        desc = f.read().strip()
    if len(desc) > 500:
        print("ERROR: description %d chars > 500 limit" % len(desc))
        return 1
    card = get_card(cardId, token)
    card.setdefault("metadata", {})["description"] = desc
    save_card(card, token)
    # verify
    back = get_card(cardId, token)
    ok = (back.get("metadata", {}).get("description", "") == desc)
    print("set-desc ok=%s len=%d" % (ok, len(desc)))
    return 0 if ok else 1


def upload_icon(path, token):
    """Upload a 16x16 PNG. The endpoint wants the RAW image bytes as the body
    with an image content-type (NOT multipart/form-data)."""
    with open(path, "rb") as f:
        data = f.read()
    fn = os.path.basename(path)
    ctype = mimetypes.guess_type(fn)[0] or "image/png"
    st, txt = req("POST",
                  "/media/displayIcons/user/me/upload?autoConvert=true&filename="
                  + urllib.parse.quote(fn),
                  token, body=data, raw=True,
                  headers={"content-type": ctype})
    if st not in (200, 201):
        raise SystemExit("ERROR: upload-icon -> HTTP %s: %s" % (st, txt[:300]))
    j = json.loads(txt)
    di = j.get("displayIcon", j)
    mid = di.get("mediaId") or di.get("displayIconId") or di.get("id")
    if not mid:
        raise SystemExit("ERROR: no mediaId in upload response: %s" % txt[:300])
    return mid


def cmd_upload_icon(args, token):
    mid = upload_icon(args[0], token)
    print("mediaId=%s" % mid)
    return 0


def upload_cover(path, token):
    """Upload a square cover image; return its public mediaUrl.
    Endpoint wants RAW image bytes with an image content-type (not multipart)."""
    with open(path, "rb") as f:
        data = f.read()
    fn = os.path.basename(path)
    ctype = mimetypes.guess_type(fn)[0] or "image/png"
    st, txt = req("POST",
                  "/media/coverImage/user/me/upload?autoconvert=true&filename="
                  + urllib.parse.quote(fn),
                  token, body=data, raw=True, headers={"content-type": ctype})
    if st not in (200, 201):
        raise SystemExit("ERROR: upload-cover -> HTTP %s: %s" % (st, txt[:300]))
    ci = json.loads(txt).get("coverImage", {})
    url = ci.get("mediaUrl") or ci.get("url")
    if not url:
        raise SystemExit("ERROR: no mediaUrl in cover response: %s" % txt[:200])
    return url


def cmd_set_cover(args, token):
    """set-cover <cardId> <image> -- upload an image and set it as the card's
    playlist cover (metadata.cover.imageL)."""
    cardId, path = args[0], args[1]
    url = upload_cover(path, token)
    card = get_card(cardId, token)
    card.setdefault("metadata", {})["cover"] = {"imageL": url}
    save_card(card, token)
    back = get_card(cardId, token)
    got = ((back.get("metadata", {}) or {}).get("cover", {}) or {}).get("imageL")
    print("set-cover ok=%s url=%s" % (bool(got), (got or "")[:60]))
    return 0 if got else 1


def yoto_ref(mid):
    """Normalise a raw mediaId into the required 'yoto:#<mediaId>' form."""
    mid = mid.strip()
    if mid.startswith("yoto:"):
        mid = mid[len("yoto:"):]
    if not mid.startswith("#"):
        mid = "#" + mid
    return "yoto:" + mid


def cmd_set_icon(args, token):
    cardId, idx, mid = args[0], int(args[1]), yoto_ref(args[2])
    card = get_card(cardId, token)
    done = False
    for _, g, ch, tr in iter_tracks(card):
        if g == idx:
            set_track_icon(ch, tr, mid)
            done = True
            break
    if not done:
        print("ERROR: track index %d not found" % idx)
        return 1
    save_card(card, token)
    print("set-icon ok track=%d -> %s" % (idx, mid))
    return 0


def cmd_apply(args, token):
    cardId = args[0]
    plan = json.load(open(args[args.index("--plan") + 1], "r", encoding="utf-8"))
    force = "--force" in args
    card = get_card(cardId, token)

    # description
    if plan.get("description") is not None:
        d = plan["description"].strip()
        if len(d) > 500:
            print("ERROR: description %d > 500" % len(d)); return 1
        card.setdefault("metadata", {})["description"] = d

    # icons: upload once per distinct PNG, then assign
    icons = plan.get("icons", {})
    cache = {}
    changed = []
    for _, g, ch, tr in iter_tracks(card):
        key = str(g)
        if key not in icons:
            continue
        if has_real_icon(tr) and not force:
            continue
        png = icons[key]
        if png not in cache:
            cache[png] = upload_icon(png, token)
            print("uploaded %s -> %s" % (os.path.basename(png), cache[png]))
        mid = yoto_ref(cache[png])
        set_track_icon(ch, tr, mid)
        changed.append(g)

    save_card(card, token)
    # verify
    back = get_card(cardId, token)
    have = sum(1 for _, _, _, tr in iter_tracks(back) if has_real_icon(tr))
    total = sum(1 for _ in iter_tracks(back))
    descok = (plan.get("description") is None or
              back.get("metadata", {}).get("description", "").strip()
              == plan["description"].strip())
    print("apply ok changed=%s icons=%d/%d descOk=%s" %
          (changed, have, total, descok))
    return 0


def cmd_upload_audio(args, token):
    """upload-audio <file> -- upload+transcode one audio file; print its sha."""
    up = upload_audio(args[0], token)
    print("sha=%s duration=%s fileSize=%s channels=%s format=%s" %
          (up["sha"], up["duration"], up["fileSize"], up["channels"], up["format"]))
    return 0


def cmd_create(args, token):
    """create --manifest <m.json>  [--title T] [--desc-file d.txt]

    Manifest: {"title": "...", "description": "...",   # optional here
               "tracks": [{"file": "path.mp3", "title": "Track title"}, ...]}
    Uploads each file (resumable: a .uploads.json cache next to the manifest
    stores sha results so re-runs skip already-uploaded files), creates a new
    card, prints `created cardId=<id> tracks=N`.
    """
    mpath = args[args.index("--manifest") + 1]
    man = json.load(open(mpath, "r", encoding="utf-8"))
    title = man.get("title")
    if "--title" in args:
        title = args[args.index("--title") + 1]
    desc = man.get("description")
    if "--desc-file" in args:
        desc = open(args[args.index("--desc-file") + 1], "r",
                    encoding="utf-8").read().strip()
    if not title:
        print("ERROR: no title (in manifest or --title)"); return 1

    cache_path = mpath + ".uploads.json"
    cache = {}
    if os.path.isfile(cache_path):
        cache = json.load(open(cache_path, "r", encoding="utf-8"))
    icon_cache_path = mpath + ".icons.json"
    icon_cache = {}
    if os.path.isfile(icon_cache_path):
        icon_cache = json.load(open(icon_cache_path, "r", encoding="utf-8"))

    tracks = []
    for i, t in enumerate(man["tracks"], 1):
        f = t["file"]
        if f in cache:
            up = cache[f]
        else:
            print("uploading %d/%d %s" % (i, len(man["tracks"]),
                                          os.path.basename(f)))
            up = upload_audio(f, token)
            cache[f] = up
            json.dump(cache, open(cache_path, "w", encoding="utf-8"))
        tr = make_track("%02d" % i, t["title"], up, overlay=str(i))
        ic = t.get("icon")
        if ic and os.path.isfile(ic):
            if ic not in icon_cache:
                icon_cache[ic] = upload_icon(ic, token)
                json.dump(icon_cache, open(icon_cache_path, "w", encoding="utf-8"))
            tr["display"] = {"icon16x16": yoto_ref(icon_cache[ic])}
        tracks.append(tr)

    cardId = create_card(title, tracks, token, description=desc)
    # Guard: the API occasionally double-writes a freshly created card, leaving
    # duplicated tracks. Read it back and verify the count matches.
    back = get_card(cardId, token)
    live = sum(1 for _ in iter_tracks(back))
    if live != len(tracks):
        print("WARNING cardId=%s tracks=%d EXPECTED=%d (duplicated/short — run "
              "`dedupe %s` or delete+recreate)" % (cardId, live, len(tracks), cardId))
    else:
        print("created cardId=%s tracks=%d" % (cardId, len(tracks)))
    return 0


def cmd_dedupe(args, token):
    """dedupe <cardId> -- drop duplicate tracks (same trackUrl) and duplicate
    chapters, collapsing an accidentally multiplied card to its unique tracks."""
    cardId = args[0]
    card = get_card(cardId, token)
    seen_ch = set()
    chs = []
    for ch in card.get("content", {}).get("chapters", []):
        seen = set()
        uniq = []
        for tr in ch.get("tracks", []):
            u = tr.get("trackUrl")
            if u in seen:
                continue
            seen.add(u)
            uniq.append(tr)
        ch["tracks"] = uniq
        sig = tuple(t.get("trackUrl") for t in uniq)
        if sig in seen_ch:
            continue
        seen_ch.add(sig)
        chs.append(ch)
    card["content"]["chapters"] = chs
    save_card(card, token)
    back = get_card(cardId, token)
    print("dedupe %s -> tracks=%d" % (cardId, sum(1 for _ in iter_tracks(back))))
    return 0


def cmd_delete(args, token):
    """delete <cardId> -- delete a card (POST /content makes, DELETE removes)."""
    st, txt = req("DELETE", "/content/" + args[0], token)
    print("delete %s -> HTTP %s %s" % (args[0], st, txt[:80]))
    return 0 if st == 200 else 1


CMDS = {
    "whoami": cmd_whoami, "get": cmd_get, "dump": cmd_dump,
    "set-desc": cmd_set_desc, "upload-icon": cmd_upload_icon,
    "set-icon": cmd_set_icon, "apply": cmd_apply,
    "upload-audio": cmd_upload_audio, "create": cmd_create, "delete": cmd_delete,
    "dedupe": cmd_dedupe, "set-cover": cmd_set_cover,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        return 2
    token = find_token()
    return CMDS[sys.argv[1]](sys.argv[2:], token)


if __name__ == "__main__":
    raise SystemExit(main())
