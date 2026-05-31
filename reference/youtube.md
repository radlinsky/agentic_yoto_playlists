# YouTube → Yoto (full pipeline)

Goal: turn a YouTube video or playlist URL into one or more Yoto cards, each
track an mp3 with a fitting 16x16 icon and a bilingual description.

Personal/family use only — respect copyright.

Prereqs: token verified (`whoami`, see SKILL Step 0), `ffmpeg` on PATH. `yt-dlp`
auto-installs. Run from your active workspace. SCRIPTS = the `scripts/` dir.

## 1. List & plan
```
python SCRIPTS/yt_to_manifest.py list "<playlist-or-video URL>"
```
Prints `index|duration_s|title`. Apply Yoto limits (≤5 h / ≤100 tracks / ≤500 MB
per card; ≤60 min per track). Skip `[Private video]` / `[Deleted video]`.
Make a proposal to the user of which songs to combine into which playlists
(considering the limits), and await the user's approval before proceeding.

## 2. Fetch one card's audio + manifest
```
python SCRIPTS/yt_to_manifest.py fetch "<URL>" "audio/<playlist_name>" --indices 1-5 --max-min 20
```
- Downloads selected items as `NN - Title.mp3` and writes
  `audio/<playlist_name>/manifest.json` (tracks list with file+title).
- Resumable: already-downloaded files are skipped. `--max-min` skips items longer
  than N minutes (default 60).
- It auto-tries multiple YouTube player clients (android/ios/tv/web_safari) to
  dodge the recurring "video not available / formats may be missing" breakage.
- If some items still FAIL, re-run the same command (resumable) or download those
  ids manually with `python -m yt_dlp -x --audio-format mp3
  --extractor-args youtube:player_client=android -o "<folder>/NN - Title.%(ext)s" <watch-url>`.

## 3. Set title + bilingual description in the manifest
Edit `audio/<playlist_name>/manifest.json`: set `"title"` and `"description"` (inferred
language paragraph, optionally multi-language; ≤500 chars total). See
`reference/icon-keywords.md` style. Keep track titles meaningful.

## 4. Create the card
```
python SCRIPTS/yoto_api.py create --manifest "audio/<playlist_name>/manifest.json"
```
Uploads + transcodes each mp3 (resumable via a `.uploads.json` cache beside the
manifest), creates the card, prints `created cardId=<id> tracks=N`. This can take
a while for many/large files — run it in the background and wait.
Verify: `python SCRIPTS/yoto_api.py get <cardId>` (tracks listed, icons NONE).

## 5. Icons
Derive an English keyword per track from its (often French) title
(`reference/icon-keywords.md`), fetch + PREVIEW, then apply. See
`reference/from-folder.md` Steps "prepare icons" and "apply" — identical from
here (the card now exists with audio).

## 6. Cover art (per card)
After a card's tracks + icons exist, give it a cover from its own track icons and
stage it for printing (see `reference/cover-art.md`):
```
python SCRIPTS/make_cover.py gen --title "Name N" --icons "icons/<playlist_name>" --out "album_artwork/<playlist_name>/cover.png"
python SCRIPTS/yoto_api.py set-cover <cardId> "album_artwork/<playlist_name>/cover.png"
```
For a series, you can generate one print sheet for all covers: `python SCRIPTS/make_cover.py sheet --images "album_artwork/*/cover.png" --out "album_artwork/series_print.pdf"`.

## 7. Repeat for the next card
Use the next index range and folder name ("Name 2", …). Tell the user each
cardId. To put several cards under one "series", they link each card to a
physical MYO card in the Yoto app (then tape on the printed cover from step 6).

## Multi-card batches — do this safely
- Run the batch ONCE. NEVER start a second create run while one is going: a
  killed wrapper can leave a detached `python` alive, and two runs racing on the
  same card produce DUPLICATED tracks. Before (re)launching, confirm no stray
  python is running; a lock file is wise.
- After the batch, VERIFY every card: `get <cardId>` track count == manifest
  count, no track twice. Short card → stale `.uploads.json` (delete card, remove
  cache, recreate). Doubled tracks → `dedupe <cardId>`.

## Gotchas seen in practice
- ~14 h playlist (75 vids) → multiple cards; the long 45–60 min "compilation"
  items each become a single track (fine, <60 min) but eat the hour budget fast.
- Titles may contain emojis/odd chars; `fetch` cleans them for display + filename.
- One private video in a playlist is normal; it's skipped automatically.
