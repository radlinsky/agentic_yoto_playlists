# Add icons + bilingual description to a card that already has audio

Use when a card exists (created via this skill, the Yoto app, or YouTube flow)
and you want per-track 16x16 icons and/or a description. Idempotent: tracks that
already have real art are skipped.

Prereqs: token verified (AGENT_INSTRUCTIONS Step 0). Run from your active workspace.
SCRIPTS = the skill's `scripts/` dir. Use `audio/<playlist_name>` for audio and `icons/<playlist_name>` for icons.

## 1. Audit (never overwrite real art)
```
python SCRIPTS/yoto_api.py get <cardId>
```
Each line: `<index>  <iconTail|NONE>  <title>`. Needs an icon if `NONE` or if the
tail is the default placeholder `#aUm9i3e`. A distinct tail = real art → leave it.

## 2. Prepare icons (offline)
For each track needing one, derive an English keyword from its (often French)
title — see `reference/icon-keywords.md` (e.g. "La guitare"→guitar, "le hibou"→
owl, "petit bateau en papier"→paper boat, "l'école"→school).
```
mkdir -p icons/<playlist_name>
python SCRIPTS/fetch_icon.py "<keyword>" "icons/tmp" --n 1   # community icon
# copy the chosen file to icons/<playlist_name>/<index><keyword>.png
# if nothing fits: python SCRIPTS/gen_icon.py "<keyword>" "icons/<playlist_name>/<n>.png"
```
(`fetch_icon.py` / `gen_icon.py` need network → ensure network access is enabled.)

## 3. PREVIEW before applying (important)
yotoicons' first hit is sometimes wrong (a "boat" once came back a snail). Build
a montage and LOOK at it; re-fetch any bad ones:
```python
from PIL import Image; import os
d="icons/<playlist_name>"; ims=sorted(f for f in os.listdir(d) if f.endswith(".png"))
s=10; sheet=Image.new("RGBA",(16*s*len(ims)+4*(len(ims)+1),16*s+8),(235,235,235,255)); x=4
for f in ims:
    im=Image.open(os.path.join(d,f)).convert("RGBA").resize((16*s,16*s),Image.NEAREST)
    sheet.alpha_composite(im,(x,4)); x+=16*s+4
sheet.convert("RGB").save("icons/_prev.png")
```
View `icons/_prev.png`.

## 4. Apply (icons + optional description, one command)
Write `icons/<playlist_name>/plan.json` (1-based track indices; list ONLY tracks to
change):
```json
{
  "description": "Description in inferred language(s).",
  "icons": { "1": "icons/<playlist_name>/1sheep.png", "5": "icons/<playlist_name>/5wolf.png" }
}
```
```
python SCRIPTS/yoto_api.py apply <cardId> --plan "icons/<playlist_name>/plan.json"
```
Success: `apply ok changed=[...] icons=N/N descOk=True`. Tracks with real art are
skipped (pass `--force` to override). Omit `"description"` to leave it unchanged.

## 5. Verify
`python SCRIPTS/yoto_api.py get <cardId>` — every intended track shows a distinct
tail (none left `#aUm9i3e`), description length looks right.

## Piecemeal alternative (smallest steps for a tiny model)
- Description only: `yoto_api.py set-desc <cardId> --file desc.txt`
- One icon: `yoto_api.py upload-icon icon.png` → `mediaId=<id>`, then
  `yoto_api.py set-icon <cardId> <trackIndex> <id>`

Icon spec: 16x16 PNG, transparent background, avoid pure black (won't render).

## Cover art (optional but recommended)
After icons, give the playlist a cover + a print-ready file to tape on the card —
see `reference/cover-art.md`:
`make_cover.py gen --title ... --icons "icons/<playlist_name>" --out "album_artwork/<playlist_name>/cover.png"` →
`yoto_api.py set-cover <cardId> "album_artwork/<playlist_name>/cover.png"` →
`make_cover.py print --image "album_artwork/<playlist_name>/cover.png" --out "album_artwork/<playlist_name>/print.pdf"`.
