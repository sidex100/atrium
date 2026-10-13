"""atrium edge test (2026-10-08): 3840x2160 wallpaper to check, pixel by pixel, whether the TV
shows the whole picture.

v2 - "ladders" (the colour stairs of v1 were unreadable in phone photos): at the left and right
edges, rows numbered 0..15; bar k touches the edge and is k+1 px wide (k=0 - only the outermost
column, k=3 - columns 0..3). If the TV cuts N px at that edge, bars 0..N-1 vanish completely,
so the smallest visible number = how many pixels are cut. The same at the bottom edge (left of the
dock). The top edge is under the GNOME top bar - not tested.

python make_edge_test.py  ->  atrium-edge-test-4k.png (+ atrium-edge-test-preview.jpg)
"""
import pathlib

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
OUT = HERE / "atrium-edge-test-4k.png"
PREVIEW = HERE / "atrium-edge-test-preview.jpg"

W, H = 3840, 2160
BG = (0, 0, 0)
INK = (255, 255, 255)
LABEL = (200, 200, 200)
STEPS = 16          # bars 0..15
ROW, GAP = 40, 22   # bar thickness along the edge and the gap between bars


def font(size):
    for name in ("DejaVuSansMono.ttf", "consola.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_lab, f_mid, f_big = font(34), font(40), font(64)

    # left and right edges: rows from y0 down
    y0 = 300
    for k in range(STEPS):
        y = y0 + k * (ROW + GAP)
        d.rectangle([0, y, k, y + ROW - 1], fill=INK)                    # left: columns 0..k
        d.rectangle([W - 1 - k, y, W - 1, y + ROW - 1], fill=INK)        # right: columns W-1-k..W-1
        d.text((70, y + 2), str(k), font=f_lab, fill=LABEL)
        d.text((W - 70 - d.textlength(str(k), font=f_lab), y + 2), str(k), font=f_lab, fill=LABEL)

    # bottom edge: columns from x0 to the right, left of the dock
    x0 = 60
    for k in range(STEPS):
        x = x0 + k * (ROW + GAP)
        d.rectangle([x, H - 1 - k, x + ROW - 1, H - 1], fill=INK)         # rows H-1-k..H-1
        t = str(k)
        d.text((x + (ROW - d.textlength(t, font=f_lab)) / 2, H - 90), t, font=f_lab, fill=LABEL)

    lines = [
        "atrium edge test  3840 x 2160",
        "bar k touches the edge and is k+1 px wide",
        "smallest visible bar number = pixels cut at that edge",
        "left / right: numbered rows    bottom: numbered columns",
    ]
    ty = 880
    for k, t in enumerate(lines):
        fnt = f_big if k == 0 else f_mid
        d.text(((W - d.textlength(t, font=fnt)) / 2, ty), t, font=fnt, fill=(235, 235, 235))
        ty += 90 if k == 0 else 62

    img.save(OUT, optimize=True)
    img.resize((1600, 900), Image.LANCZOS).save(PREVIEW, quality=90)
    print(OUT, img.size)


if __name__ == "__main__":
    main()
