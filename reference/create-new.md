# Create a new Yoto card from a folder of audio files

Use when you have local audio (mp3/m4a/etc.) and want a brand-new card. (For
YouTube, see `reference/youtube.md`; it produces the same manifest.)

Prereqs: token verified (AGENT_INSTRUCTIONS Step 0), `ffmpeg` on PATH. Run from your active workspace.
SCRIPTS = the skill's `scripts/` dir.

## 1. Normalise to a folder
Put the audio in `audio/<playlist_name>`, named in play order (e.g. `01 - ....mp3`). Convert
non-mp3 if you like (Yoto also accepts m4a/aac/flac/wav/opus, and re-transcodes
anyway): `python SCRIPTS/download_audio.py --convert "audio/<playlist_name>"`.

## 2. Build a manifest
Create `audio/<playlist_name>/manifest.json`:
```json
{
  "title": "My Playlist",
  "description": "Description in inferred language(s).",
  "tracks": [
    {"file": "audio/<playlist_name>/01 - First.mp3", "title": "First story"},
    {"file": "audio/<playlist_name>/02 - Second.mp3", "title": "Second story"}
  ]
}
```
- `title` required; `description` ≤500 chars (omit to leave blank).
- Order in `tracks` = order on the card. Keep titles meaningful (they show on the
  player/app).

## 3. Create the card
```
python SCRIPTS/yoto_api.py create --manifest "audio/<playlist_name>/manifest.json"
```
Uploads + transcodes each file (resumable via `manifest.json.uploads.json`),
creates the card, prints `created cardId=<id> tracks=N`. Large batches take a
while — run in background. Verify: `python SCRIPTS/yoto_api.py get <cardId>`.

## 4. Add icons
The card now has audio; decorate it exactly like an existing card —
see `reference/from-folder.md` (prepare icons → preview → apply).

## 5. Cover art
Generate a playlist cover, set it, and make a print-ready file to tape on the
physical card — see `reference/cover-art.md` (`make_cover.py gen` →
`yoto_api.py set-cover` → `make_cover.py print`).

## Notes
- Yoto limits: ≤100 tracks, ≤5 h, ≤500 MB per card, ≤60 min per track. For big
  collections, propose to the user how to split the songs across multiple cards
  and await their approval.
- `create` makes one chapter per track (a flat playlist), which is what MYO
  playlists use.
