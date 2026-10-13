"""atrium wallpaper 2: Gustave Boulanger, "Rehearsal of 'The Flute Player' in the atrium of the
Pompeian house of Prince Napoleon" (1861, public domain), as a 3840x2160 desktop with a small
ATRIUM caption (font Cinzel, SIL OFL 1.1 - Cinzel-OFL.txt).

python make_painting_wallpaper.py          ->  atrium-painting-v2-4k.png (+ atrium-painting-v2-preview.jpg)
python make_painting_wallpaper.py evening  ->  atrium-painting-evening-v2-4k.png (+ ...-evening-v2-preview.jpg)

- the painting (1920x1235) is enlarged exactly 2x and cropped to 16:9 mostly from the top
  (ceiling under the GNOME top bar); people, floor and the painter's signature stay;
- "evening" (2026-10-04, the day version was too bright): lower exposure, warm lamp light around
  the brazier and the people in the middle, darker cool edges, dusk blue in the roof opening;
- a soft vignette, a bit stronger at the top (black top bar), fits the dark theme;
- the caption sits in the bottom right corner, outside the dock;
- v2 (2026-10-08): the dock grew with the apps and reached the caption -> caption raised above the
  dock band (MARGIN_BOTTOM 62 -> 250 px; dock at scale 2.5 is ~170 px high), files *-v2-*.
"""
import pathlib
import sys

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = pathlib.Path(__file__).parent
SRC = HERE / "boulanger-1861-atrium.webp"
FONT = HERE / "Cinzel-wght.ttf"
EVENING = "evening" in sys.argv[1:]
NAME = ("atrium-painting-evening" if EVENING else "atrium-painting") + "-v2"
OUT = HERE / f"{NAME}-4k.png"
PREVIEW = HERE / f"{NAME}-preview.jpg"

W, H = 3840, 2160
CROP_BOTTOM = 20          # px of the 2x image cut at the bottom (signature stays)
TEXT = "ATRIUM"
FONT_SIZE = 92
FONT_WEIGHT = 500
TRACKING = 0.34           # letter spacing, in em
MARGIN_RIGHT, MARGIN_BOTTOM = 120, 250
INK = (244, 234, 212)     # warm ivory, like the marble in the painting


def painting():
    img = Image.open(SRC).convert("RGB")
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=35, threshold=2))
    top = img.height - H - CROP_BOTTOM
    return img.crop((0, top, W, top + H))


def channels(img, r, g, b, gamma=1.0):
    """multiply the channels (0..1+) and darken midtones with gamma > 1"""
    out = []
    for band, k in zip(img.split(), (r, g, b)):
        out.append(band.point(lambda v, k=k: min(255, int(255 * ((v / 255) ** gamma) * k))))
    return Image.merge("RGB", out)


def glow(cx, cy, rx, ry, power=1.6):
    """elliptic light mask: 255 in the centre -> 0 at the ellipse edge"""
    g = ImageOps.invert(Image.radial_gradient("L")).resize((2 * rx, 2 * ry), Image.BICUBIC)
    g = g.point(lambda v: int(255 * (v / 255) ** power))
    m = Image.new("L", (W, H), 0)
    m.paste(g, (cx - rx, cy - ry))
    return m.filter(ImageFilter.GaussianBlur(60))


def evening(img):
    img = ImageEnhance.Color(img).enhance(0.85)
    lit = channels(img, 0.98, 0.80, 0.58, gamma=1.15)     # warm lamp light
    dark = channels(img, 0.26, 0.27, 0.36, gamma=1.35)    # dim, slightly cool
    light = ImageChops.lighter(
        glow(int(W * 0.57), int(H * 0.66), int(W * 0.46), int(H * 0.62)),            # brazier, people
        glow(int(W * 0.12), int(H * 0.74), int(W * 0.16), int(H * 0.30)).point(lambda v: v * 6 // 10),
    )
    out = Image.composite(lit, dark, light)
    # dusk in the opening of the roof (top of the picture)
    sky = channels(img, 0.16, 0.22, 0.42, gamma=1.2)
    lin = Image.linear_gradient("L").resize((W, H))         # 0 at the top -> 255 at the bottom
    top = lin.point(lambda v: int(max(0, 70 - v) * 3.6))     # strongest at the very top
    return Image.composite(sky, out, top)


def vignette():
    # radial: 0 in the centre -> 255 at the corners, darkening starts halfway
    g = Image.radial_gradient("L").resize((int(W * 1.2), int(H * 1.35)), Image.BICUBIC)
    g = g.crop(((g.width - W) // 2, (g.height - H) // 2, (g.width - W) // 2 + W, (g.height - H) // 2 + H))
    radial = g.point(lambda v: int(max(0, v - 120) * 0.6))
    # top: a little darker under the black top bar
    lin = Image.linear_gradient("L").resize((W, H))          # 0 at the top -> 255 at the bottom
    top = lin.point(lambda v: int(max(0, 60 - v) * 1.6))      # first ~23% of the height
    return ImageChops.lighter(radial, top)


def caption(base):
    font = ImageFont.truetype(str(FONT), FONT_SIZE)
    font.set_variation_by_axes([FONT_WEIGHT])
    spacing = FONT_SIZE * TRACKING
    widths = [font.getlength(ch) for ch in TEXT]
    total = sum(widths) + spacing * (len(TEXT) - 1)
    ascent, descent = font.getmetrics()
    x0 = W - MARGIN_RIGHT - total
    y0 = H - MARGIN_BOTTOM - ascent

    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    x = x0
    for ch, w in zip(TEXT, widths):
        d.text((x, y0), ch, font=font, fill=255)
        x += w + spacing

    shadow = mask.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.75))
    shadow = ImageChops.offset(shadow, 0, 5)
    base.paste((0, 0, 0), (0, 0), shadow)
    base.paste(INK, (0, 0), mask)
    return base


def main():
    img = painting()
    if EVENING:
        img = evening(img)
    img.paste((0, 0, 0), (0, 0), vignette())
    img = caption(img)
    img.save(OUT, optimize=True)
    img.resize((1280, 720), Image.LANCZOS).save(PREVIEW, quality=90)
    print(OUT, img.size)


if __name__ == "__main__":
    main()
