from PIL import Image
import os, glob

d = "icons/White-Album"
files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
cols = 10
rows = (len(files) + cols - 1) // cols
s = 4
w = cols * 16 * s + (cols - 1) * 4
h = rows * 16 * s + rows * 8
sheet = Image.new("RGBA", (w, h), (235, 235, 235, 255))
x, y = 4, 4
for i, f in enumerate(files):
    im = Image.open(os.path.join(d, f)).convert("RGBA").resize((16 * s, 16 * s), Image.NEAREST)
    sheet.alpha_composite(im, (x, y))
    x += 16 * s + 4
    if (i + 1) % cols == 0:
        x = 4
        y += 16 * s + 8
sheet.convert("RGB").save("icons/White-Album/_prev.png")
print(f"Preview saved: {len(files)} icons in {cols}x{rows} grid")
