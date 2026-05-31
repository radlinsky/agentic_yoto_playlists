# yoto_api.py command reference + API facts

All commands: `python SCRIPTS/yoto_api.py <cmd> ...` (SCRIPTS = skill `scripts/`).
Token comes from `$YOTO_TOKEN` or `.yoto_token.txt`; never printed.

## Commands
| Command | What it does | Prints |
|---|---|---|
| `whoami` | verify token (scopes + live check) | `... scopes_has_content=True scopes_has_icons=True live_http=200` |
| `get <cardId>` | audit: title, descLen, tracks + icon tails | one line per track |
| `dump <cardId> <out.json>` | full raw card JSON (backup/debug) | `wrote <file>` |
| `set-desc <cardId> --file <txt>` | replace description (≤500 chars) | `set-desc ok=True len=N` |
| `upload-icon <png>` | upload a 16x16 PNG | `mediaId=<id>` |
| `set-icon <cardId> <trackIdx> <mediaId>` | set one track's icon (1-based) | `set-icon ok track=N -> yoto:#...` |
| `apply <cardId> --plan <json> [--force]` | description + many icons at once, idempotent | `apply ok changed=[...] icons=N/N descOk=True` |
| `upload-audio <file>` | upload+transcode one audio, get its sha | `sha=... duration=... fileSize=... channels=... format=...` |
| `create --manifest <json> [--title T] [--desc-file d.txt]` | NEW card from a manifest of audio | `created cardId=<id> tracks=N` |
| `delete <cardId>` | delete a card | `delete <id> -> HTTP 200` |
| `set-cover <cardId> <image>` | upload an image + set it as the playlist cover | `set-cover ok=True url=...` |

Cover art generation/printing is a separate script, `make_cover.py`:
`gen --title T [--subtitle S] [--icons DIR] [--color #RRGGBB] --out cover.png`,
`print --image cover.png --out one.pdf [--mm 48]`,
`sheet --images DIR --out series.pdf [--mm 48]`. See `reference/cover-art.md`.

`yt_to_manifest.py`: `list <URL>` and
`fetch <URL> <outdir> [--indices 1-5,9] [--max-min 60]` (see `reference/youtube.md`).

## Manifest shape (create)
```json
{"title":"...", "description":"EN\n\nFR",
 "tracks":[{"file":"path.mp3","title":"Track title"}, ...]}
```
`create` writes a `<manifest>.uploads.json` cache so re-runs skip already-uploaded
files (resumable). One chapter per track.

## Plan shape (apply)
```json
{"description":"EN\n\nFR", "icons":{"1":"a.png","3":"b.png"}}
```
Indices are 1-based across the whole card. Only listed tracks change. Omit
`description` to leave it. Real-art tracks skipped unless `--force`.

## Verified API contract (api.yotoplay.com, bearer token)
- **Read card**: `GET /content/<cardId>` → `{card:{title, metadata.description,
  content.chapters[].tracks[]}}`.
- **Save/create card**: `POST /content` with
  `{cardId?, title, content:{chapters:[{key,title,overlayLabel,tracks:[...]}]},
  metadata:{description}}`. Omit `cardId` to create; include to update.
- **Track object**: `{key, title, overlayLabel, trackUrl:"yoto:#<transcodedSha>",
  type:"audio", format:"opus", duration, fileSize, channels:"stereo",
  display:{icon16x16:"yoto:#<mediaId>"}}`.
- **Upload audio** (3 steps):
  1. `GET /media/transcode/audio/uploadUrl?sha256=<sha>&filename=<fn>` →
     `{upload:{uploadId, uploadUrl}}` (uploadUrl null if already uploaded).
  2. `PUT <uploadUrl>` raw bytes, `Content-Type: audio/mpeg` (S3 signed URL).
  3. Poll `GET /media/upload/<uploadId>/transcoded?loudnorm=false` → 202 while
     transcoding, 200 with `transcode.transcodedSha256` and
     `transcode.transcodedInfo{duration,channels,fileSize,format}`. Use
     transcodedSha256 as the track's `trackUrl` (`yoto:#<sha>`).
- **Upload icon**: `POST /media/displayIcons/user/me/upload?autoConvert=true&filename=<fn>`
  with RAW PNG bytes and `Content-Type: image/png` (NOT multipart) →
  `{displayIcon:{mediaId}}`.
- **Upload cover**: `POST /media/coverImage/user/me/upload?autoconvert=true&filename=<urlencoded-fn>`
  with RAW image bytes and `Content-Type: image/png` → `{coverImage:{mediaId,
  mediaUrl}}`. Set on the card via `metadata.cover = {"imageL": "<mediaUrl>"}`.
  ALWAYS url-encode the filename (spaces/accents → "URL can't contain control
  characters" otherwise).
- **Delete card**: `DELETE /content/<cardId>` → `{status:"ok"}`.

## Gotchas (all learned the hard way)
- Icon/track refs MUST be `yoto:#<id>` — the `#` is required (mediaId is 43
  chars). `yoto_ref()` adds it.
- Newly created cards return `display: null` on tracks (not missing) → coerce to
  `{}` before assigning (handled by `set_track_icon`).
- Default placeholder icon id `#aUm9i3ex3qqAMYBv-i-O-pYMKuMJGICtR3Vhf289u2Q` =
  "no real icon"; used for idempotency.
- Token scopes needed: `user:content:manage`, `user:icons:manage`. Lasts ~24h.
- Do NOT call the API from inside a browser tab (CORS + the browser automation tool
  extension stalls page fetches). Shell only.
- yt-dlp: default player client often 404s ("video not available"); use
  `--extractor-args youtube:player_client=android` (yt_to_manifest does this).
