# Free / legal kids-audio sources (for Mode B)

Only download **public-domain** or **Creative-Commons** audio. Mainstream
commercial kids music (Disney, Peppa Pig, Frozen, etc.) is copyrighted -- there
is no legal free download; do not attempt it. When in doubt, prefer public domain
/ CC0 and note the licence + creator.

## Internet Archive (archive.org) -- biggest catalogue
- Search API (JSON):
  `https://archive.org/advancedsearch.php?q=<QUERY>&fl[]=identifier&fl[]=title&fl[]=licenseurl&rows=50&output=json`
  Example queries:
  - `subject:"nursery rhymes" AND mediatype:audio`
  - `subject:children AND subject:stories AND mediatype:audio`
  - add ` AND licenseurl:(*creativecommons* OR *publicdomain*)` to filter licence.
- Item metadata + file list: `https://archive.org/metadata/<identifier>`
- Download (installs `internetarchive` on demand):
  `python scripts/download_audio.py --ia <identifier> <outdir> --glob "*.mp3"`

## LibriVox -- public-domain audiobooks / stories (great for 4+)
- API (JSON): `https://librivox.org/api/feed/audiobooks/?title=^<TITLE>&format=json&extended=1`
- All content is public domain. Files are usually also mirrored on archive.org,
  so you can grab the archive.org identifier and use the `--ia` mode above.

## Openverse -- unified CC search (audio)
- API: `https://api.openverse.org/v1/audio/?q=<QUERY>&license_type=all`
  Returns direct download URLs; filter by `license`/`source`.
- Download a direct URL: `python scripts/download_audio.py --url <URL> <outdir>`

## Pixabay Music / Free Music Archive
- Pixabay kids music: https://pixabay.com/music/search/kids/ (Pixabay licence,
  free, no attribution). Manual browse; download then `--url`.
- Free Music Archive: https://freemusicarchive.org/genre/Kid-Friendly/ (CC).

## YouTube (only Creative-Commons-licensed videos)
- Verify the video is CC-licensed first. Then:
  `python scripts/download_audio.py --ytdlp <URL> <outdir>` (installs yt-dlp).

## Normalise to mp3 for Yoto
- After downloading, convert anything non-mp3:
  `python scripts/download_audio.py --convert <outdir>`
- Yoto limits: <=100 tracks, <=500 MB / 5 h per card, <=100 MB / 60 min per
  track. 128 kbps mp3 is a good default.

## Licence quick guide
- Public domain / CC0: free for any use.
- CC BY / CC BY-SA: free; credit the creator (note it in the description).
- CC BY-NC: free for personal/family (non-commercial) use -- fine here.
- Anything post-1929 with no explicit free licence: assume copyrighted, skip.
