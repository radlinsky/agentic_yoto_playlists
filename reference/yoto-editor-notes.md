# Yoto web-editor cheat sheet (my.yotoplay.com)

Use a **browser automation tool** to drive the editor. The site is a single-page
app; **CSS/DOM selectors change** so never hardcode them. Instead, after every
navigation or click, call `read_page` (accessibility tree) and/or
`get_page_text` and locate elements by their **visible text / role**. The track
titles are known ahead of time (from the audio filenames), so use them as
anchors to find each track row.

## Connection & login
- First call `tabs_context_mcp` (with `createIfEmpty: true`) to get/create a tab,
  capture the `tabId`, and pass it to every subsequent browser call.
- If the extension reports "not connected", retry once; if still failing, ask the
  user to open Chrome with the extension signed in.
- The user logs into Yoto via **Google sign-in**. NEVER attempt to log in or
  enter credentials. If the page shows a login/sign-in screen, STOP and ask the
  user to sign in, then continue.

## Data model
- Card -> one Playlist -> Tracks. **One MYO card = one playlist.**
- A user's cards live at `https://my.yotoplay.com/my-cards`.
- Open an existing card editor at `https://my.yotoplay.com/card/<cardId>/edit`
  (e.g. `dWAMo`). Confirm by reading the page which tracks are present before
  doing anything.

## Create / add audio
1. New card: from `/my-cards` click **"Make Your Own"**. Existing: open the
   `/card/<id>/edit` URL.
2. Set the **playlist name** (mandatory) in the title field.
3. **"Add Audio"** opens a file picker; select files (use `file_upload` MCP tool
   to set the chosen file paths). Upload in alphabetical batches.
4. Each track goes downloading -> uploading -> **transcoding**. WAIT until a
   track shows ready before adding more or editing it -- poll with
   `get_page_text`/`read_page`. Clicking too early can drop/reorder tracks.
5. Reorder via the drag handles (blue lines); rename by clicking a track title;
   per-track "..." menu has delete/loop.

## Per-track 16x16 icon (VERIFIED 2026-05 against live editor)
1. Each track row has a small **"Choose icon" image button** (the pixel-art
   thumbnail, `img[alt="Choose icon"]`), sitting between the drag handle and the
   track title. The 3-dot button to the right is the options menu (Continue/
   Pause/Repeat/Delete) -- NOT the icon. Get all icon buttons' coordinates with:
   `Array.from(document.querySelectorAll('img[alt="Choose icon"]'))` and click by
   coordinate (they are not exposed as buttons in the accessibility tree).
2. A dialog (`[role=dialog]`) opens with two tabs: **Yoto Icons** and
   **My Icons**, plus an "Apply to all tracks" checkbox (do NOT tick it).
   - **Yoto Icons**: a large scrollable GRID of ~500 `img.trackIcon` tiles.
     IMPORTANT: in the current build there is **NO keyword search box**, and the
     tiles have **no alt/title/tags** (src is an opaque hash). So you cannot pick
     a specific themed icon by keyword here -- only by eyeballing the grid.
   - **My Icons**: has a hidden `input[type=file]` (accept=image/*). This is the
     reliable path for "unique & relevant": prepare an exact 16x16 PNG offline
     (yotoicons.com via `fetch_icon.py`, else `gen_icon.py`), then `file_upload`
     to that input and click the uploaded thumbnail to select.
3. The icon grid loads thumbnails from `media-secure-v2.api.yotoplay.com/icons/*`.
   These are MANY requests; while they're in flight the page never reaches
   "document_idle", so `find` / `read_page` / `file_upload` (which wait for idle)
   TIME OUT. `javascript_tool` still works. Mitigation: operate via JS, or clear
   incomplete grid `<img>` srcs to let the page settle.
4. Icon spec: **16x16 PNG, transparent background, avoid pure black** (black does
   not render). PNG/GIF/JPG/TIF/SVG accepted; Yoto auto-resizes but we provide
   exact 16x16.
5. **Saving gates on the media service.** Clicking Update fires
   `POST api.yotoplay.com/media/user/icons`. If Yoto's media backend is degraded
   (icon CDN returning HTTP 503), this request hangs "pending" forever and NOTHING
   persists (neither icons NOR the description, even though description edits don't
   themselves need media). Before a run, health-check the media API; if icons 503,
   STOP and tell the user it's a Yoto outage -- retry later.
6. After setting, reload and confirm the row shows a custom (non default) icon.
   **Idempotent:** if a row already has a custom icon, skip it.

## Title & description
- Title = the playlist name (already set).
- **Description is a single free-text field, MAX 500 characters.** Put the
  description in the inferred language(s) of the playlist in this field. A
  bilingual EN+FR blurb must fit in 500 chars, so keep each language to ~2
  sentences.
- **CRITICAL — React-controlled fields:** the title/description are React inputs.
  Setting their value with `form_input` (or a plain `.value =`) updates the DOM
  but NOT React state, so clicking Update saves the OLD text. Set them with the
  native setter + dispatched input event via `javascript_tool`, e.g.:
  ```js
  const ta=document.querySelector('textarea');
  const set=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
  set.call(ta, NEW_TEXT);
  ta.dispatchEvent(new Event('input',{bubbles:true}));
  ta.dispatchEvent(new Event('change',{bubbles:true}));
  ```
  (Use `HTMLInputElement` for the title textbox.) Then click Update and RELOAD
  the page and re-read the value to confirm it persisted.

## Cards & playlists data model (confirmed)
- Playlists are listed at `https://my.yotoplay.com/my-cards/playlists`; each is a
  separate card with its own id and `/card/<id>/edit` URL.
- Read the list page and map names -> `/card/<id>/edit` hrefs to find a card id.

## Save
- Click the orange **Create** (new card) / **Save** / **Update** (existing)
  button. There is no separate publish step. Confirm success (toast or the URL
  changing to `/card/<id>/edit`) and reload to verify persistence.

## Runtime discovery strategy (robust loop)
1. `read_page` with `filter: interactive` to list buttons/inputs with refs.
2. Match by visible text ("Add Audio", "Make Your Own", "Save", track titles).
3. To act on a specific track, first `find` its title text, then read that row's
   subtree (`read_page` with the row `ref_id`) to locate its palette button.
4. Act (`computer` click / `form_input` / `file_upload`), then re-read to verify
   the expected state change before the next step. Pace actions; never fire blind
   clicks.
