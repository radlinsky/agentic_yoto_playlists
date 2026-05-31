#!/usr/bin/env python3
"""Generate a fallback 16x16 Yoto track icon.

Usage:
    python gen_icon.py KEYWORD OUTPATH [--shape circle|square|letter]

Produces a 16x16 RGBA PNG with a transparent background and a non-black
foreground (pure black does not render on the Yoto display). The colour is
derived deterministically from KEYWORD so re-runs are stable. By default a
single uppercase letter (first letter of KEYWORD) is drawn centred; pass
--shape circle/square for a simple filled glyph instead.

Primary implementation uses Pillow. If Pillow is unavailable it falls back to
ImageMagick's `magick` CLI. Exits non-zero with a message if neither works.
"""
import hashlib
import subprocess
import sys


def color_for(keyword: str) -> tuple:
    """Deterministic, reasonably bright, non-black RGB from a keyword."""
    h = hashlib.sha256(keyword.encode("utf-8")).digest()
    r, g, b = h[0], h[1], h[2]
    # Lift each channel so the result is never near-black / invisible.
    r = 80 + (r % 176)
    g = 80 + (g % 176)
    b = 80 + (b % 176)
    return (r, g, b)


def gen_pillow(keyword: str, outpath: str, shape: str) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return False
    rgb = color_for(keyword)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shape == "circle":
        d.ellipse([2, 2, 13, 13], fill=rgb + (255,))
    elif shape == "square":
        d.rectangle([3, 3, 12, 12], fill=rgb + (255,))
    else:  # letter
        ch = (keyword.strip()[:1] or "?").upper()
        font = None
        # Try a small truetype font for a crisper glyph; fall back to default.
        for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
            try:
                font = ImageFont.truetype(name, 14)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        try:
            bbox = d.textbbox((0, 0), ch, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            pos = ((16 - tw) / 2 - bbox[0], (16 - th) / 2 - bbox[1])
        except Exception:
            pos = (4, 1)
        d.text(pos, ch, fill=rgb + (255,), font=font)
    img.save(outpath, "PNG")
    return True


def gen_magick(keyword: str, outpath: str, shape: str) -> bool:
    rgb = color_for(keyword)
    hexcol = "#%02x%02x%02x" % rgb
    if shape == "circle":
        draw = "circle 7,7 7,2"
    elif shape == "square":
        draw = "rectangle 3,3 12,12"
    else:
        ch = (keyword.strip()[:1] or "?").upper()
        draw = None
    try:
        if draw:
            cmd = ["magick", "-size", "16x16", "xc:none", "-fill", hexcol,
                   "-draw", draw, outpath]
        else:
            cmd = ["magick", "-size", "16x16", "xc:none", "-fill", hexcol,
                   "-gravity", "center", "-pointsize", "14", "-annotate", "0",
                   ch, outpath]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception:
        return False


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shape = "letter"
    for a in sys.argv[1:]:
        if a.startswith("--shape"):
            shape = a.split("=", 1)[1] if "=" in a else "letter"
    if "--shape" in sys.argv:
        i = sys.argv.index("--shape")
        if i + 1 < len(sys.argv):
            shape = sys.argv[i + 1]
            args = [a for a in args if a != shape]
    if len(args) < 2:
        print("usage: gen_icon.py KEYWORD OUTPATH [--shape circle|square|letter]",
              file=sys.stderr)
        return 2
    keyword, outpath = args[0], args[1]
    if gen_pillow(keyword, outpath, shape):
        print(outpath)
        return 0
    if gen_magick(keyword, outpath, shape):
        print(outpath)
        return 0
    print("ERROR: neither Pillow nor ImageMagick available to generate icon",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
