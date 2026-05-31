# Playlist cover art + print-ready file

Two outputs from one image:
1. the card's **playlist cover** (shown in the Yoto app), set via the API; and
2. a **print-ready PDF** sized to cut out and tape onto the physical MYO card.

Covers are generated deterministically with Pillow (no model, no network needed)
— the reliable choice for a small local model. Run from your active workspace.
SCRIPTS = the skill's `scripts/` dir. Token verified (SKILL Step 0).

## 1. Generate the cover image
Reuse the playlist's own track icons as the cover motif (recognisable + free):
```
python SCRIPTS/make_cover.py gen --title "My Playlist" \
    --subtitle "optional line" --icons "icons/<playlist_name>" --out "album_artwork/<playlist_name>/cover.png"
```
- `--icons` = a folder (or glob) of the track 16x16 PNGs; up to 9 are tiled as a
  grid above the title. Omit `--icons` for a plain title-only cover.
- Square PNG (default 1000x1000). Background colour is derived from the title;
  override with `--color "#RRGGBB"`. Title auto-wraps/shrinks into a reserved
  bottom band so it's always prominent.
- LOOK at `album_artwork/<playlist_name>/cover.png` before setting it; regenerate with a different
  `--color`/`--subtitle` if you don't like it.

## 2. Set it as the card's cover (API)
```
python SCRIPTS/yoto_api.py set-cover <cardId> "album_artwork/<playlist_name>/cover.png"
```
Prints `set-cover ok=True url=...`. Uploads the image and sets
`metadata.cover.imageL`. Idempotent — re-running replaces it. Verify in the Yoto
app or `yoto_api.py get <cardId>`.

## 3. Make the print file
One card:
```
python SCRIPTS/make_cover.py print --image "album_artwork/<playlist_name>/cover.png" --out "album_artwork/<playlist_name>/print.pdf" [--mm 48]
```
Many cards on one multi-page sheet (best for a series):
```
python SCRIPTS/make_cover.py sheet --images "album_artwork/*/cover.png" --out "album_artwork/series_print.pdf" [--mm 48]
```
- Default 48mm square fits a Yoto card (~85.6x54mm; 48mm leaves margin on the
  54mm height). Adjust `--mm` to taste.
- 300 DPI, US-Letter, with a thin cut border + corner marks and a caption.
  **Print at 100% / "actual size"** (NOT "fit to page"), cut on the line, tape on.

## Where this fits in a build
- YouTube / new-card flows: after the card's tracks + icons exist, do steps 1–3.
  For a multi-card series, generate one cover per card into `album_artwork/<playlist_name>/`,
  `set-cover` each, then one `sheet` PDF for the whole series.
- Existing card (`from-folder.md`): same steps 1–3 against the live card id.

## Notes / gotchas
- Cover upload endpoint: `POST /media/coverImage/user/me/upload?autoconvert=true&
  filename=<urlencoded-fn>` with RAW image bytes + `Content-Type: image/png` (NOT
  multipart); returns `{coverImage:{mediaId, mediaUrl}}`. Card field is
  `metadata.cover = {"imageL": "<mediaUrl>"}`. (`set-cover` does all this.)
- ALWAYS url-encode the filename in upload query strings — spaces/accents
  otherwise raise "URL can't contain control characters". (yoto_api handles it.)
- Yoto's built-in covers look like `cdn.yoto.io/myo-cover/<name>.gif`; a custom
  cover's url is on `card-content.yotoplay.com`. Either is valid in `imageL`.
- Keep titles short for legibility at print size; the generator wraps long ones.
- Quote paths with spaces on the command line.
