#!/usr/bin/env python3
"""Create playlist COVER artwork for a Yoto card, plus a print-ready file.

Deterministic generation with Pillow (no model/no network needed) — the reliable
choice for a small local model. The cover is a square image: a colour derived
from the title, the title text, and (optionally) a grid of the playlist's own
track icons as a motif so the art is recognisable.

Subcommands
-----------
  gen --title "Name" --out cover.png [--subtitle "..."] [--icons DIR_or_glob]
      [--size 1000] [--color "#RRGGBB"]
      Make a square cover PNG (default 1000x1000). If --icons points at a folder
      (or glob) of 16x16 PNGs, up to 9 are arranged as a motif band. Title text
      auto-wraps and shrinks to fit. Background colour is derived from the title
      unless --color is given. Never pure black.

  print --image cover.png --out cover_print.pdf [--mm 48]
      Place ONE cover on a US-Letter page at exactly <mm> millimetres square
      (default 48mm — fits a Yoto card's 54mm height) with thin cut marks and a
      caption, at 300 DPI. Print at 100% / "actual size", cut out, tape to the
      MYO card.

  sheet --images DIR_or_glob --out covers_sheet.pdf [--mm 48]
      Tile MANY covers onto a multi-page US-Letter PDF (300 DPI), each at <mm>
      square with cut marks and its filename as caption. Best for printing a
      whole playlist series at once.

All output paths are printed on success. Errors print `ERROR: ...`.
"""
import glob
import hashlib
import os
import sys

from PIL import Image, ImageDraw, ImageFont


# ---------- helpers ----------
def color_for(title):
    """Derive a pleasant, not-too-dark, not-too-light RGB tuple from a title.

    Args:
        title: The playlist title string.

    Returns:
        An (r, g, b) tuple with each channel in [50, 189].
    """
    h = hashlib.sha256(title.encode("utf-8")).digest()
    # pleasant, not-too-dark, not-too-light
    r = 50 + h[0] % 140
    g = 50 + h[1] % 140
    b = 50 + h[2] % 140
    return (r, g, b)


def load_font(size, bold=True):
    """Load a TrueType font at the given size, falling back to default.

    Args:
        size: Font size in pixels.
        bold: If True, prefer bold variants.

    Returns:
        A PIL ImageFont instance.
    """
    names = (["arialbd.ttf", "Arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold
             else ["arial.ttf", "DejaVuSans.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    return ImageFont.load_default()


def text_size(d, s, font):
    """Measure the pixel width and height of a text string.

    Args:
        d:    A PIL ImageDraw instance.
        s:    The text string to measure.
        font: A PIL ImageFont instance.

    Returns:
        A (width, height) tuple in pixels.
    """
    b = d.textbbox((0, 0), s, font=font)
    return b[2] - b[0], b[3] - b[1]


def wrap(d, text, font, maxw):
    """Word-wrap text to fit within a maximum pixel width.

    Args:
        d:    A PIL ImageDraw instance.
        text: The text string to wrap.
        font: A PIL ImageFont instance.
        maxw: Maximum width in pixels.

    Returns:
        A list of line strings.
    """
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_size(d, t, font)[0] <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def lighten(c, f=0.5):
    """Lighten an RGB colour toward white.

    Args:
        c: An (r, g, b) tuple.
        f: Blend factor (0.0 = unchanged, 1.0 = white).

    Returns:
        A lightened (r, g, b) tuple.
    """
    return tuple(int(x + (255 - x) * f) for x in c)


def darken(c, f=0.4):
    """Darken an RGB colour toward black.

    Args:
        c: An (r, g, b) tuple.
        f: Blend factor (0.0 = unchanged, 1.0 = black).

    Returns:
        A darkened (r, g, b) tuple.
    """
    return tuple(int(x * (1 - f)) for x in c)


# ---------- gen ----------
def cmd_gen(args):
    """Subcommand: generate a square cover PNG with title, optional subtitle,
    and optional grid of track icons as a motif.

    Args:
        args: CLI args after the subcommand: --title, --out, [--subtitle],
              [--icons DIR_or_glob], [--size N], [--color '#RRGGBB'].

    Returns:
        Exit code (0 success, 1 missing required args).
    """
    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default
    title = opt("--title")
    out = opt("--out")
    if not title or not out:
        print("ERROR: --title and --out required")
        return 1
    subtitle = opt("--subtitle")
    size = int(opt("--size", "1000"))
    color = opt("--color")
    icons_spec = opt("--icons")

    bg = color_for(title)
    if color:
        color = color.lstrip("#")
        bg = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    img = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(img)
    # soft vertical gradient for depth
    top = lighten(bg, 0.18)
    bot = darken(bg, 0.28)
    for y in range(size):
        f = y / size
        col = tuple(int(top[i] + (bot[i] - top[i]) * f) for i in range(3))
        d.line([(0, y), (size, y)], fill=col)

    margin = int(size * 0.08)
    # Reserve a fixed title band at the bottom so the title is always prominent.
    title_band_top = int(size * (0.66 if subtitle else 0.70))

    # motif: grid of track icons, fitted into the top region above the band
    icons = []
    if icons_spec:
        if os.path.isdir(icons_spec):
            icons = sorted(glob.glob(os.path.join(icons_spec, "*.png")))
        else:
            icons = sorted(glob.glob(icons_spec))
    icons = icons[:9]
    if icons:
        n = len(icons)
        cols = 3 if n >= 3 else n
        rows = (n + cols - 1) // cols
        gap = int(size * 0.03)
        region_top = int(size * 0.10)
        region_h = title_band_top - region_top - int(size * 0.03)
        region_w = size - 2 * margin
        cell = min((region_w - (cols - 1) * gap) // cols,
                   (region_h - (rows - 1) * gap) // rows)
        gw = cols * cell + (cols - 1) * gap
        gh = rows * cell + (rows - 1) * gap
        x0 = (size - gw) // 2
        y0 = region_top + max(0, (region_h - gh) // 2)
        for i, p in enumerate(icons):
            r, c = divmod(i, cols)
            try:
                ic = Image.open(p).convert("RGBA").resize((cell, cell),
                                                          Image.NEAREST)
            except Exception:
                continue
            tile = Image.new("RGBA", (cell, cell), lighten(bg, 0.85) + (255,))
            tile.alpha_composite(ic)
            img.paste(tile.convert("RGB"),
                      (x0 + c * (cell + gap), y0 + r * (cell + gap)))
    motif_bottom = title_band_top

    # title text block (in the reserved bottom band)
    maxw = size - 2 * margin
    fs = int(size * 0.16)
    while fs > 18:
        font = load_font(fs, bold=True)
        lines = wrap(d, title, font, maxw)
        lh = text_size(d, "Ag", font)[1] + int(fs * 0.3)
        block_h = lh * len(lines)
        if motif_bottom + block_h + (int(size * 0.06) if subtitle else 0) \
                <= size - margin:
            break
        fs -= 4
    font = load_font(fs, bold=True)
    lines = wrap(d, title, font, maxw)
    lh = text_size(d, "Ag", font)[1] + int(fs * 0.3)
    block_h = lh * len(lines)
    avail_top = motif_bottom
    avail_bot = size - margin - (int(size * 0.07) if subtitle else 0)
    ty = avail_top + max(0, (avail_bot - avail_top - block_h) // 2)
    fg = (255, 255, 255)
    sh = darken(bg, 0.6)
    for ln in lines:
        w, _ = text_size(d, ln, font)
        x = (size - w) // 2
        d.text((x + 2, ty + 2), ln, font=font, fill=sh)
        d.text((x, ty), ln, font=font, fill=fg)
        ty += lh
    if subtitle:
        sf = load_font(int(size * 0.045), bold=False)
        w, h = text_size(d, subtitle, sf)
        d.text(((size - w) // 2, size - margin - h), subtitle, font=sf,
               fill=lighten(bg, 0.7))

    img.save(out, "PNG")
    print(out)
    return 0


# ---------- print ----------
def cmd_print(args):
    """Subcommand: place one cover on a US-Letter page as a print-ready PDF.

    Args:
        args: CLI args after the subcommand: --image, --out, [--mm N].

    Returns:
        Exit code (0 success, 1 missing required args).
    """
    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default
    image = opt("--image")
    out = opt("--out")
    if not image or not out:
        print("ERROR: --image and --out required")
        return 1
    mm = float(opt("--mm", "48"))
    dpi = 300
    px_per_mm = dpi / 25.4
    art = int(round(mm * px_per_mm))
    # US Letter at 300 dpi
    pw, ph = int(8.5 * dpi), int(11 * dpi)
    page = Image.new("RGB", (pw, ph), (255, 255, 255))
    d = ImageDraw.Draw(page)
    cover = Image.open(image).convert("RGB").resize((art, art), Image.LANCZOS)
    x = (pw - art) // 2
    y = int(1.2 * dpi)
    page.paste(cover, (x, y))
    # cut border + corner marks
    d.rectangle([x, y, x + art, y + art], outline=(150, 150, 150), width=2)
    m = int(0.12 * dpi)
    for (cx, cy) in [(x, y), (x + art, y), (x, y + art), (x + art, y + art)]:
        d.line([(cx - m, cy), (cx + m, cy)], fill=(120, 120, 120), width=1)
        d.line([(cx, cy - m), (cx, cy + m)], fill=(120, 120, 120), width=1)
    cap = load_font(40, bold=False)
    d.text((x, y + art + int(0.15 * dpi)),
           "Print at 100%% (actual size). Cut on the line: %dx%dmm. "
           "Tape to your Yoto card." % (int(mm), int(mm)), font=cap,
           fill=(60, 60, 60))
    page.save(out, "PDF", resolution=float(dpi))
    print(out)
    return 0


# ---------- sheet (many covers -> one multi-page PDF) ----------
def cmd_sheet(args):
    """Subcommand: tile many covers onto a multi-page US-Letter PDF.

    Args:
        args: CLI args after the subcommand: --images DIR_or_glob, --out,
              [--mm N].

    Returns:
        Exit code (0 success, 1 missing required args or no images found).
    """
    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default
    spec = opt("--images")   # dir or glob of cover PNGs
    out = opt("--out")
    if not spec or not out:
        print("ERROR: --images (dir or glob) and --out required")
        return 1
    mm = float(opt("--mm", "48"))
    if os.path.isdir(spec):
        imgs = sorted(glob.glob(os.path.join(spec, "*.png")))
    else:
        imgs = sorted(glob.glob(spec))
    if not imgs:
        print("ERROR: no images match %s" % spec)
        return 1
    dpi = 300
    ppm = dpi / 25.4
    art = int(round(mm * ppm))
    pw, ph = int(8.5 * dpi), int(11 * dpi)
    gap = int(8 * ppm)            # 8mm gutter
    capgap = int(6 * ppm)
    cell_h = art + capgap
    mx, my = int(0.5 * dpi), int(0.5 * dpi)
    cols = max(1, (pw - 2 * mx + gap) // (art + gap))
    rows = max(1, (ph - 2 * my + gap) // (cell_h + gap))
    per = cols * rows
    cap = load_font(28, bold=False)
    pages = []
    for i in range(0, len(imgs), per):
        page = Image.new("RGB", (pw, ph), (255, 255, 255))
        d = ImageDraw.Draw(page)
        for k, path in enumerate(imgs[i:i + per]):
            r, c = divmod(k, cols)
            x = mx + c * (art + gap)
            y = my + r * (cell_h + gap)
            try:
                cov = Image.open(path).convert("RGB").resize((art, art),
                                                             Image.LANCZOS)
            except Exception:
                continue
            page.paste(cov, (x, y))
            d.rectangle([x, y, x + art, y + art], outline=(150, 150, 150),
                        width=2)
            mk = int(0.1 * dpi)
            for (cx, cy) in [(x, y), (x + art, y), (x, y + art),
                             (x + art, y + art)]:
                d.line([(cx - mk, cy), (cx + mk, cy)], fill=(120, 120, 120))
                d.line([(cx, cy - mk), (cx, cy + mk)], fill=(120, 120, 120))
            name = os.path.splitext(os.path.basename(path))[0][:28]
            d.text((x, y + art + int(0.02 * dpi)), name, font=cap,
                   fill=(90, 90, 90))
        d.text((mx, ph - my + int(0.04 * dpi)),
               "Print at 100%% (actual size). Each square %dmm. Cut & tape to "
               "Yoto cards." % int(mm), font=cap, fill=(60, 60, 60))
        pages.append(page)
    pages[0].save(out, "PDF", resolution=float(dpi), save_all=True,
                  append_images=pages[1:])
    print("%s pages=%d covers=%d" % (out, len(pages), len(imgs)))
    return 0


def main():
    """CLI entry point. Parse subcommand (gen/print/sheet) from argv.

    Returns:
        Exit code (0 success, 2 usage).
    """
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == "gen":
        return cmd_gen(sys.argv[2:])
    if sys.argv[1] == "print":
        return cmd_print(sys.argv[2:])
    if sys.argv[1] == "sheet":
        return cmd_sheet(sys.argv[2:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
