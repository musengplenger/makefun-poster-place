#!/usr/bin/env python3
"""VELMORA — The Glass Tide Coast. Painterly travel poster generator.

Draws a 1024x1024 travel poster for a fictional place, Pillow only, fully
offline and deterministic. The scene follows the winning pattern of the
top-ranked posters: one giant landmark (a moon arch) as centerpiece, warm
saturated dusk light, rich texture (value noise, glow, grain) on every
surface, people living in the scene, and a huge serif title in a cream
frame. Run: python3 main.py  ->  writes /output/entry.png
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = H = 1024
OUT = "/output/entry.png"
SEED = 20261121

SERIF_BLACK = "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Black.ttf"
SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"

CREAM = (238, 226, 198)
GOLD = (244, 222, 170)
GOLD_DEEP = (216, 178, 110)


def rng(seed):
    return random.Random(SEED + seed)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def vgrad(w, h, stops):
    """Vertical gradient. stops: list of (pos 0..1, (r,g,b))."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                d.line([(0, y), (w, y)], fill=lerp(c0, c1, f))
                break
        else:
            d.line([(0, y), (w, y)], fill=stops[-1][1])
    return img


def noise_field(w, h, seed, octaves=((8, 0.55), (16, 0.30), (32, 0.15))):
    """Multi-octave value noise, deterministic. Returns an 'L' image."""
    acc = Image.new("L", (w, h), 0)
    total = sum(wt for _, wt in octaves)
    for gw, wt in octaves:
        r = rng(seed + gw)
        gh = max(2, int(gw * h / w))
        grid = Image.new("L", (gw, gh))
        grid.putdata([r.randrange(256) for _ in range(gw * gh)])
        layer = grid.resize((w, h), Image.BICUBIC)
        acc = Image.blend(acc, layer, wt / total)
    return acc


def tinted(noise, dark, light):
    """Map an 'L' noise field between two colours -> RGB image."""
    dark_img = Image.new("RGB", noise.size, dark)
    light_img = Image.new("RGB", noise.size, light)
    return Image.composite(light_img, dark_img, noise)


def blotch(base, mask, seed, dark, light, alpha, scales=((5, 0.5), (11, 0.3), (26, 0.2))):
    """Large-scale blotchy texture: coarse value-noise patches (100px+ down
    to ~40px) blended hard, clipped to mask — so no surface reads as one
    flat colour. Fine grain alone does NOT do this."""
    n = noise_field(W, H, seed, scales)
    tex = tinted(n, dark, light)
    base.paste(Image.blend(base, tex, alpha), (0, 0), mask)


def soft_layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def paste(base, layer, blur=0):
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.paste(layer, (0, 0), layer)
    return base


def glow_sprite(radius, color, peak=170):
    """Radial glow sprite, RGBA, size 2r+1."""
    s = radius * 2 + 1
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    steps = 24
    for i in range(steps, 0, -1):
        a = int(peak * (1 - i / steps) ** 2)
        rr = radius * i / steps
        d.ellipse([radius - rr, radius - rr, radius + rr, radius + rr],
                  fill=color + (a,))
    return img


def draw_glow(base, cx, cy, radius, color, peak=150, blur=0):
    spr = glow_sprite(radius, color, peak)
    layer = soft_layer()
    layer.paste(spr, (int(cx - radius), int(cy - radius)), spr)
    paste(base, layer, blur)


def tracked_width(draw, text, font, tracking):
    return sum(draw.textlength(ch, font=font) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(draw, cx, y, text, font, fill, tracking=0):
    w = tracked_width(draw, text, font, tracking)
    x = cx - w / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def font(path, size):
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- sky
def paint_sky(base):
    sky = vgrad(W, 600, [
        (0.00, (14, 20, 48)),
        (0.30, (44, 32, 82)),
        (0.55, (96, 48, 104)),
        (0.75, (164, 72, 96)),
        (0.90, (216, 116, 78)),
        (1.00, (242, 172, 100)),
    ])
    base.paste(sky, (0, 16))
    # soft warm clouds: LARGE soft masses (coarse noise, 100px+ scale),
    # pink-amber lit, blurred — no flat sky band
    for (y0, y1, seed, col, alpha) in [
        (150, 330, 11, (226, 138, 130), 95),
        (380, 560, 23, (244, 178, 120), 110),
    ]:
        n = noise_field(W, y1 - y0, seed, ((5, 0.65), (12, 0.35)))
        n = n.point(lambda v: 0 if v < 95 else int((v - 95) * 1.5))
        band = Image.new("RGB", (W, y1 - y0), col)
        layer = soft_layer()
        layer.paste(band, (0, y0), n)
        paste(base, layer, blur=12)
    # horizon haze: warm amber glow band above the sea line
    n = noise_field(W, 90, 29, ((4, 0.7), (9, 0.3)))
    n = n.point(lambda v: int(v * 0.55))
    layer = soft_layer()
    layer.paste(Image.new("RGB", (W, 90), (250, 186, 120)), (0, 540), n)
    paste(base, layer, blur=10)
    # faint high violet clouds
    n = noise_field(W, 220, 37, ((6, 0.7), (14, 0.3)))
    n = n.point(lambda v: 0 if v < 150 else int((v - 150) * 0.9))
    layer = soft_layer()
    layer.paste(Image.new("RGB", (W, 220), (70, 52, 110)), (0, 30), n)
    paste(base, layer, blur=10)


def paint_stars(base):
    r = rng(5)
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    for _ in range(260):
        x = r.randrange(28, 996)
        y = r.randrange(28, 400)
        s = r.choice([1, 1, 1, 2, 2, 3])
        a = r.randrange(90, 235)
        d.ellipse([x, y, x + s, y + s], fill=(255, 244, 214, a))
        if s == 3:
            d.line([(x - 3, y + 1), (x + 6, y + 1)], fill=(255, 244, 214, 90))
            d.line([(x + 1, y - 3), (x + 1, y + 6)], fill=(255, 244, 214, 90))
    paste(base, layer)


# ---------------------------------------------------------------- moon
MOON = (655, 485)
MOON_R = 92


def paint_moon(base):
    draw_glow(base, MOON[0], MOON[1], 250, (255, 214, 140), peak=110)
    draw_glow(base, MOON[0], MOON[1], 130, (255, 232, 180), peak=150)
    # moon disc: radial gold gradient built from concentric circles
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    cx, cy = MOON
    for i in range(28, 0, -1):
        t = i / 28
        col = lerp((255, 246, 214), (226, 188, 122), 1 - t)
        rr = MOON_R * t
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (255,))
    paste(base, layer)
    # soft craters, blurred so they read as texture, not stickers
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    r = rng(9)
    for _ in range(16):
        a = r.uniform(0, math.pi * 2)
        dist = r.uniform(0, MOON_R * 0.72)
        cr = r.uniform(6, 20)
        x = cx + math.cos(a) * dist
        y = cy + math.sin(a) * dist
        d.ellipse([x - cr, y - cr * 0.8, x + cr, y + cr * 0.8],
                  fill=(203, 164, 102, r.randrange(28, 62)))
    paste(base, layer, blur=3)


# ---------------------------------------------------------------- sea
def paint_sea(base):
    sea = vgrad(W, 270, [
        (0.00, (34, 116, 108)),
        (0.45, (20, 88, 92)),
        (1.00, (12, 56, 64)),
    ])
    base.paste(sea, (0, 600))
    # amber glow where the moon path falls on the water
    draw_glow(base, MOON[0], 650, 280, (244, 176, 100), peak=85, blur=2)
    # large wave texture: coarse blotches, deep teal <-> bright teal, hard blend
    seamask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(seamask).rectangle([0, 600, W, 870], fill=255)
    blotch(base, seamask, 41, (6, 30, 38), (72, 168, 150), 0.55,
           scales=((6, 0.5), (15, 0.3), (34, 0.2)))
    blotch(base, seamask, 43, (14, 62, 66), (214, 158, 92), 0.22,
           scales=((4, 0.6), (10, 0.4)))
    # big soft wave masses across the sea, not just near the moon path
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    r = rng(47)
    for _ in range(12):
        x = r.uniform(40, 620)
        y = r.uniform(620, 840)
        rw = r.uniform(60, 150)
        rh = r.uniform(6, 14)
        col = ((180, 225, 205, r.randrange(20, 55)) if r.random() < 0.6
               else (8, 40, 48, r.randrange(30, 70)))
        d.ellipse([x - rw, y - rh, x + rw, y + rh], fill=col)
    paste(base, layer, blur=4)
    # distant headland, right horizon, hazy purple
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    d.polygon([(800, 600), (880, 552), (950, 566), (1008, 548), (1008, 600)],
              fill=(96, 72, 112, 210))
    paste(base, layer, blur=4)
    # moonlight reflection path: shimmering dashes widening toward viewer
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    r = rng(17)
    y = 612
    while y < 852:
        spread = 14 + (y - 600) * 0.42
        for _ in range(r.randrange(1, 4)):
            x = MOON[0] + r.uniform(-spread, spread)
            ln = r.uniform(10, 70) * (0.6 + (y - 600) / 400)
            a = r.randrange(60, 210)
            d.line([(x - ln / 2, y), (x + ln / 2, y)],
                   fill=(255, 228, 164, a), width=r.choice([1, 2, 2, 3, 4]))
        y += r.randrange(5, 9)
    paste(base, layer, blur=1)
    # bright glow knots on the moon path
    for gy in (640, 690, 745, 800):
        draw_glow(base, MOON[0] + rng(31).uniform(-30, 30), gy, 26,
                  (255, 222, 150), peak=90)
    # gentle wave streaks
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    r = rng(19)
    for _ in range(46):
        y = r.randrange(612, 848)
        x = r.randrange(30, 900)
        ln = r.uniform(18, 90)
        a = r.randrange(26, 80)
        col = (200, 235, 220, a) if r.random() < 0.6 else (8, 40, 48, a)
        d.line([(x, y), (x + ln, y)], fill=col, width=1)
    paste(base, layer, blur=1)


# ---------------------------------------------------------------- arch
def arch_mask():
    """Giant rock arch silhouette, white on black 'L' mask."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    # legs
    d.rectangle([436, 385, 528, 723], fill=255)
    d.rectangle([762, 385, 854, 723], fill=255)
    # dome: outer half-ellipse minus inner opening
    d.pieslice([436, 238, 854, 630], 180, 360, fill=255)
    d.pieslice([540, 322, 750, 630], 180, 360, fill=0)
    d.rectangle([540, 440, 750, 723], fill=0)
    # roughen the silhouette: bites and bumps along the outer edges and
    # the dome arc, so the arch edge reads as wavy rock, not a cut-out
    r = rng(49)
    for y in range(260, 720, 14):
        rr = r.randrange(3, 11)
        d.ellipse([436 - rr, y - rr, 436 + rr, y + rr],
                  fill=0 if r.random() < 0.5 else 255)
        d.ellipse([854 - rr, y - rr, 854 + rr, y + rr],
                  fill=0 if r.random() < 0.5 else 255)
    for k in range(26):
        a = math.pi + k * math.pi / 25
        x = 645 + 209 * math.cos(a)
        y = 434 + 196 * math.sin(a)
        rr = r.randrange(3, 10)
        d.ellipse([x - rr, y - rr, x + rr, y + rr],
                  fill=0 if r.random() < 0.5 else 255)
    return m


def paint_arch(base):
    mask = arch_mask()
    # rock body: warm vertical gradient, moonlit on top
    rock = vgrad(W, H, [
        (0.00, (224, 182, 124)),
        (0.45, (176, 128, 84)),
        (1.00, (82, 54, 38)),
    ])
    base.paste(rock, (0, 0), mask)
    # large blotchy stone: coarse patches, hard contrast — never one flat tan
    blotch(base, mask, 51, (56, 32, 20), (238, 196, 132), 0.55,
           scales=((4, 0.5), (9, 0.35), (22, 0.15)))
    blotch(base, mask, 55, (120, 74, 44), (250, 216, 160), 0.30,
           scales=((7, 0.6), (18, 0.4)))
    # cool shadow wash on the outer-left face (away from the moon)
    shl = Image.new("L", (W, H), 0)
    dsl = ImageDraw.Draw(shl)
    for x in range(430, 650):
        a = int(120 * (650 - x) / 220)
        dsl.line([(x, 238), (x, 723)], fill=a)
    shl = shl.filter(ImageFilter.GaussianBlur(20))
    cool = Image.new("RGB", (W, H), (46, 34, 58))
    base.paste(Image.composite(cool, base, shl), (0, 0), mask)
    # horizontal strata, wavy and irregular, clipped to the arch
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    r = rng(53)
    for y in range(300, 720, 46):
        pts = []
        for k in range(9):
            x = 430 + k * 54
            pts.append((x, y + r.randrange(-7, 8) + 10 * math.sin(k * 0.9)))
        d.line(pts, fill=(70, 44, 30, 48), width=2)
        d.line([(x, yy + 3) for (x, yy) in pts], fill=(240, 200, 140, 26), width=2)
    # a few short vertical cracks, each with a dark line and a light
    # companion line so they read as shadowed depth, not drawn strokes
    for _ in range(7):
        x = r.randrange(460, 830)
        y = r.randrange(300, 620)
        ln = r.randrange(18, 44)
        dx = r.randrange(-6, 7)
        d.line([(x, y), (x + dx, y + ln)],
               fill=(64, 40, 28, 70), width=3)
        d.line([(x + 3, y), (x + dx + 3, y + ln)],
               fill=(240, 200, 140, 60), width=2)
    strata = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    strata.paste(layer, (0, 0), mask)
    paste(base, strata, blur=2)
    # warm rim light along the inner edge (moon side), stronger now
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    d.arc([540, 322, 750, 630], 180, 360, fill=(255, 226, 160, 235), width=12)
    d.line([(540, 440), (540, 720)], fill=(255, 226, 160, 200), width=8)
    d.line([(750, 440), (750, 720)], fill=(255, 226, 160, 180), width=7)
    rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rim.paste(layer, (0, 0), mask)
    paste(base, rim, blur=2)
    # soft shadow wash on the right side of the arch (away from the moon)
    sh = Image.new("L", (W, H), 0)
    ds = ImageDraw.Draw(sh)
    for x in range(645, 860):
        a = int(110 * (x - 645) / 215)
        ds.line([(x, 238), (x, 723)], fill=a)
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    dark = Image.new("RGB", (W, H), (52, 32, 24))
    base.paste(Image.composite(dark, base, sh), (0, 0), mask)
    # waterline foam where the legs meet the sea
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    r = rng(57)
    for (x0, x1) in [(436, 528), (762, 854)]:
        for _ in range(14):
            x = r.uniform(x0 - 8, x1 + 8)
            ln = r.uniform(8, 26)
            d.line([(x - ln / 2, 723), (x + ln / 2, 723)],
                   fill=(220, 240, 230, r.randrange(60, 130)), width=2)
    paste(base, layer, blur=1)
    # soft moonlight wash on the arch face
    wash = soft_layer()
    wash.paste(glow_sprite(190, (255, 210, 140), 46),
               (MOON[0] - 190, MOON[1] - 190), glow_sprite(190, (255, 210, 140), 46))
    wash2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wash2.paste(wash, (0, 0), mask)
    paste(base, wash2, blur=6)
    # (no town on the crown: it collided with the tagline — the lit town
    # already climbs the left cliff)


# ---------------------------------------------------------------- cliff town
def paint_cliff_town(base):
    # cliff mass, textured dark warm brown
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.polygon([(16, 470), (120, 420), (240, 452), (330, 520), (352, 640),
               (330, 700), (16, 700)], fill=255)
    cliff = vgrad(W, H, [
        (0.00, (122, 74, 60)),
        (0.55, (88, 52, 46)),
        (1.00, (52, 32, 32)),
    ])
    base.paste(cliff, (0, 0), mask)
    # large blotchy cliff rock, hard contrast + warm light from the top
    blotch(base, mask, 61, (40, 24, 22), (186, 126, 92), 0.62,
           scales=((4, 0.5), (10, 0.3), (24, 0.2)))
    draw_glow(base, 180, 440, 200, (255, 196, 120), peak=55, blur=2)
    # warm rim on the cliff top edge
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    d.line([(16, 470), (120, 420), (240, 452), (330, 520)],
           fill=(255, 196, 120, 150), width=4)
    rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rim.paste(layer, (0, 0), mask)
    paste(base, rim, blur=2)
    # houses climbing the cliff, lit windows
    r = rng(67)
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    houses = [(40, 470, 46, 40), (104, 448, 42, 36), (168, 470, 48, 42),
              (232, 498, 44, 38), (60, 530, 52, 42), (132, 556, 46, 40),
              (206, 580, 50, 42), (270, 560, 44, 36), (96, 612, 54, 44),
              (180, 632, 48, 40), (258, 620, 46, 38)]
    walls = [(244, 220, 178), (232, 196, 150), (214, 170, 138), (200, 214, 208)]
    for (x, y, hw, hh) in houses:
        d.rectangle([x, y, x + hw, y + hh], fill=r.choice(walls) + (255,))
        d.polygon([(x - 3, y), (x + hw / 2, y - 12), (x + hw + 3, y)],
                  fill=(96, 58, 44, 255))
        # lit face (left) vs shadow face (right third) — no flat walls
        d.rectangle([x + hw - hw // 3, y, x + hw, y + hh], fill=(0, 0, 0, 70))
        d.line([(x, y), (x, y + hh)], fill=(255, 220, 160, 130), width=2)
        for wx in (8, hw - 16):
            d.rectangle([x + wx, y + 10, x + wx + 8, y + 20],
                        fill=(255, 198, 92, 255))
            d.ellipse([x + wx - 3, y + 7, x + wx + 11, y + 23],
                      outline=(255, 210, 120, 90))
    # string lights draped between houses
    for (x0, y0, x1, y1) in [(40, 512, 210, 540), (110, 566, 300, 596),
                             (60, 626, 250, 652)]:
        for t in [i / 22 for i in range(23)]:
            bx = x0 + (x1 - x0) * t
            by = y0 + (y1 - y0) * t + 16 * math.sin(math.pi * t)
            d.ellipse([bx - 2, by - 2, bx + 2, by + 2],
                      fill=(255, 206, 110, 235))
    paste(base, layer, blur=1)
    for (x0, y0, x1, y1) in [(40, 512, 210, 540), (110, 566, 300, 596),
                             (60, 626, 250, 652)]:
        for t in [i / 22 for i in range(23)]:
            bx = x0 + (x1 - x0) * t
            by = y0 + (y1 - y0) * t + 16 * math.sin(math.pi * t)
            draw_glow(base, bx, by, 5, (255, 200, 100), peak=90)


def paint_sailboats(base):
    for (bx, by, s) in [(392, 700, 1.0), (884, 726, 0.82)]:
        layer = soft_layer()
        d = ImageDraw.Draw(layer)
        # hull
        d.polygon([(bx - 26 * s, by), (bx + 26 * s, by),
                   (bx + 16 * s, by + 10 * s), (bx - 16 * s, by + 10 * s)],
                  fill=(40, 28, 34, 255))
        # mast + sails, cream lit by moonlight
        d.line([(bx, by - 58 * s), (bx, by)], fill=(30, 22, 26, 255), width=2)
        d.polygon([(bx + 2, by - 56 * s), (bx + 2, by - 4),
                   (bx + 24 * s, by - 4)], fill=(246, 232, 200, 255))
        d.polygon([(bx - 2, by - 50 * s), (bx - 2, by - 4),
                   (bx - 20 * s, by - 4)], fill=(228, 206, 168, 255))
        d.polygon([(bx + 2, by - 56 * s), (bx + 2, by - 4),
                   (bx + 24 * s, by - 4)],
                  outline=(255, 226, 160, 160))
        paste(base, layer, blur=1)
        draw_glow(base, bx, by - 30 * s, 26, (255, 220, 150), peak=60)


# ---------------------------------------------------------------- terrace
def paint_terrace(base):
    # stone terrace floor and wall, textured warm stone
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.rectangle([16, 862, 1008, 1008], fill=255)
    stone = vgrad(W, 150, [
        (0.00, (96, 74, 58)),
        (0.50, (76, 58, 46)),
        (1.00, (52, 40, 34)),
    ])
    base.paste(stone, (0, 862))
    # large blotchy stone floor — no flat band; moon-side light pool
    blotch(base, mask, 71, (36, 28, 22), (150, 118, 88), 0.50,
           scales=((5, 0.5), (12, 0.3), (28, 0.2)))
    draw_glow(base, 700, 920, 220, (255, 200, 130), peak=40, blur=2)
    # tile seams on the floor
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    for x in range(60, 1000, 92):
        d.line([(x, 866), (x - 26, 1008)], fill=(30, 22, 18, 90), width=2)
    d.line([(16, 930), (1008, 930)], fill=(30, 22, 18, 70), width=2)
    paste(base, layer, blur=1)
    # balustrade: top rail + balusters + warm top light
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    d.rectangle([16, 856, 1008, 872], fill=(168, 140, 108, 255))
    d.rectangle([16, 856, 1008, 860], fill=(238, 214, 170, 255))
    for x in range(36, 1000, 34):
        d.rectangle([x, 872, x + 12, 918], fill=(150, 124, 94, 255))
        d.rectangle([x, 872, x + 4, 918], fill=(196, 168, 128, 255))
    d.rectangle([16, 918, 1008, 926], fill=(140, 114, 86, 255))
    paste(base, layer, blur=1)


def paint_couple(base):
    """Couple from behind at the balustrade, soft-shaded, moon rim light."""
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    # woman, straw hat, terracotta dress (left)
    wx = 296
    # hair falling below the hat
    d.ellipse([wx - 15, 798, wx + 15, 836], fill=(52, 34, 28, 255))
    d.ellipse([wx - 34, 792, wx + 34, 806], fill=(217, 176, 106, 255))  # brim
    d.ellipse([wx - 20, 772, wx + 20, 798], fill=(217, 176, 106, 255))  # dome
    d.rectangle([wx - 20, 788, wx + 20, 796], fill=(90, 52, 36, 255))   # band
    d.ellipse([wx - 12, 802, wx + 12, 824], fill=(198, 140, 102, 255))  # face edge
    # rounded shoulders + A-line dress with soft shading
    d.ellipse([wx - 30, 826, wx + 30, 856], fill=(178, 86, 60, 255))
    d.polygon([(wx - 30, 844), (wx - 24, 830), (wx + 24, 830), (wx + 30, 844),
               (wx + 34, 922), (wx - 34, 922)], fill=(178, 86, 60, 255))
    d.polygon([(wx + 8, 830), (wx + 24, 830), (wx + 30, 844), (wx + 34, 922),
               (wx + 16, 922)], fill=(140, 62, 44, 255))                # shade side
    d.polygon([(wx - 30, 844), (wx - 24, 830), (wx - 6, 830), (wx - 10, 922),
               (wx - 34, 922)], fill=(214, 116, 84, 255))               # lit side
    d.line([(wx - 28, 872), (wx + 28, 872)], fill=(120, 52, 38, 255), width=3)  # belt
    # hair highlight on her hat brim edge
    d.arc([wx - 34, 788, wx + 34, 810], 200, 340, fill=(255, 226, 170, 220), width=3)
    # her arm resting on the rail
    d.line([(wx + 22, 852), (wx + 52, 866)], fill=(178, 86, 60, 255), width=9)
    d.ellipse([wx + 46, 860, wx + 58, 872], fill=(198, 140, 102, 255))
    # man, white shirt, dark hair (right)
    mx = 392
    d.ellipse([mx - 13, 796, mx + 13, 822], fill=(206, 152, 112, 255))   # head
    d.pieslice([mx - 14, 792, mx + 14, 816], 180, 360, fill=(40, 28, 24, 255))
    d.ellipse([mx - 32, 822, mx + 32, 852], fill=(232, 220, 196, 255))   # shoulders
    d.polygon([(mx - 32, 840), (mx - 26, 826), (mx + 26, 826), (mx + 32, 840),
               (mx + 34, 922), (mx - 34, 922)], fill=(232, 220, 196, 255))
    d.polygon([(mx + 10, 826), (mx + 26, 826), (mx + 32, 840), (mx + 34, 922),
               (mx + 16, 922)], fill=(196, 182, 152, 255))              # shade side
    d.polygon([(mx - 32, 840), (mx - 26, 826), (mx - 8, 826), (mx - 12, 922),
               (mx - 34, 922)], fill=(250, 242, 222, 255))              # lit side
    d.line([(mx - 12, 826), (mx + 12, 826)], fill=(180, 166, 136, 255), width=3)  # collar
    # skin shading: darker edge on the right of his head, light on the left
    d.arc([mx - 13, 796, mx + 13, 822], 300, 60, fill=(150, 100, 70, 200), width=3)
    d.arc([mx - 13, 796, mx + 13, 822], 120, 240, fill=(255, 224, 180, 200), width=3)
    # his arm resting on the rail
    d.line([(mx - 22, 852), (mx - 52, 866)], fill=(232, 220, 196, 255), width=9)
    d.ellipse([mx - 58, 860, mx - 46, 872], fill=(206, 152, 112, 255))
    # warm moon rim light on their right edges
    d.line([(wx + 28, 832), (wx + 33, 918)], fill=(255, 224, 160, 200), width=3)
    d.line([(mx + 30, 826), (mx + 33, 918)], fill=(255, 224, 160, 200), width=3)
    # soft shadow under them on the floor
    d.ellipse([wx - 46, 918, mx + 52, 934], fill=(20, 14, 12, 110))
    paste(base, layer, blur=2)


def paint_table(base):
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    tx, ty = 492, 902
    # soft drop shadow on the floor under the table
    d.ellipse([tx - 56, ty + 38, tx + 56, ty + 52], fill=(20, 14, 12, 130))
    d.ellipse([tx - 52, ty - 10, tx + 52, ty + 10], fill=(210, 184, 148, 255))
    d.ellipse([tx - 52, ty - 10, tx + 52, ty + 2], fill=(238, 216, 178, 255))
    d.line([(tx, ty + 6), (tx, ty + 40)], fill=(90, 68, 48, 255), width=5)
    d.ellipse([tx - 16, ty + 38, tx + 16, ty + 46], fill=(90, 68, 48, 255))
    # bottle + two wine glasses, pale gold wine
    d.rounded_rectangle([tx - 26, ty - 34, tx - 16, ty - 10], 3,
                        fill=(40, 58, 40, 255))
    d.rectangle([tx - 23, ty - 42, tx - 19, ty - 34], fill=(40, 58, 40, 255))
    for gx in (tx + 8, tx + 30):
        d.line([(gx, ty - 10), (gx, ty - 26)], fill=(240, 230, 200, 255), width=2)
        d.ellipse([gx - 6, ty - 34, gx + 6, ty - 24], fill=(240, 222, 170, 230))
        d.ellipse([gx - 6, ty - 29, gx + 6, ty - 24], fill=(232, 190, 110, 255))
    paste(base, layer, blur=1)
    draw_glow(base, tx + 19, ty - 28, 14, (255, 210, 130), peak=70)


def paint_flowers(base):
    """Bougainvillea clusters on both terrace ends."""
    r = rng(83)
    for (cx, cy, rx, ry) in [(78, 920, 84, 62), (946, 918, 84, 62),
                             (60, 872, 60, 40), (962, 868, 60, 40)]:
        # soft drop shadow on the floor under each cluster
        layer = soft_layer()
        d = ImageDraw.Draw(layer)
        d.ellipse([cx - rx, cy + ry - 10, cx + rx, cy + ry + 12],
                  fill=(20, 14, 12, 110))
        paste(base, layer, blur=3)
        layer = soft_layer()
        d = ImageDraw.Draw(layer)
        for _ in range(46):
            a = r.uniform(0, math.pi * 2)
            dist = r.uniform(0, 1) ** 0.5
            x = cx + math.cos(a) * dist * rx
            y = cy + math.sin(a) * dist * ry
            s = r.uniform(7, 15)
            d.ellipse([x - s, y - s * 0.7, x + s, y + s * 0.7],
                      fill=(34, 72, 40, 235))
        paste(base, layer, blur=2)
        layer = soft_layer()
        d = ImageDraw.Draw(layer)
        for _ in range(150):
            a = r.uniform(0, math.pi * 2)
            dist = r.uniform(0, 1) ** 0.5
            x = cx + math.cos(a) * dist * rx
            y = cy + math.sin(a) * dist * ry
            s = r.uniform(2, 5)
            col = r.choice([(214, 51, 108), (232, 93, 154), (194, 24, 91),
                            (240, 130, 170)])
            d.ellipse([x - s, y - s, x + s, y + s], fill=col + (235,))
        paste(base, layer, blur=1)


def paint_lanterns(base):
    for (lx, ly) in [(150, 846), (838, 846)]:
        draw_glow(base, lx, ly + 12, 34, (255, 190, 100), peak=120)
        layer = soft_layer()
        d = ImageDraw.Draw(layer)
        d.line([(lx, ly - 14), (lx, ly)], fill=(30, 22, 18, 255), width=3)
        d.rectangle([lx - 9, ly, lx + 9, ly + 26], fill=(24, 18, 14, 255))
        d.rectangle([lx - 6, ly + 3, lx + 6, ly + 23],
                    fill=(255, 196, 100, 255))
        d.line([(lx - 6, ly + 12), (lx + 6, ly + 12)],
               fill=(255, 226, 150, 255), width=2)
        paste(base, layer, blur=1)


# ---------------------------------------------------------------- title
def paint_title(base):
    layer = soft_layer()
    d = ImageDraw.Draw(layer)
    big = font(SERIF_BLACK, 138)
    draw_tracked(d, 512, 46, "VELMORA", big, (20, 14, 30, 170), tracking=10)
    paste(base, layer, blur=4)
    d = ImageDraw.Draw(base)
    draw_tracked(d, 512, 42, "VELMORA", big, GOLD, tracking=10)
    # tagline with side rules
    small = font(SERIF_BOLD, 34)
    draw_tracked(d, 512, 196, "THE GLASS TIDE COAST", small, GOLD, tracking=8)
    tw = tracked_width(d, "THE GLASS TIDE COAST", small, 8)
    d.line([(512 - tw / 2 - 120, 212), (512 - tw / 2 - 24, 212)],
           fill=GOLD_DEEP, width=2)
    d.line([(512 + tw / 2 + 24, 212), (512 + tw / 2 + 120, 212)],
           fill=GOLD_DEEP, width=2)
    # small bottom line on the terrace wall
    tiny = font(SERIF, 22)
    draw_tracked(d, 512, 962, "VISIT THE UNSEEN", tiny, (232, 214, 180), tracking=6)


# ---------------------------------------------------------------- finish
def paint_finish(base):
    # film grain: seeded noise at low res, upscaled smooth (compressible)
    r = rng(97)
    data = r.randbytes(128 * 128)
    grain = Image.frombytes("L", (128, 128), data).resize((W, H), Image.BICUBIC)
    base.paste(Image.blend(base, tinted(grain, (0, 0, 0), (255, 255, 255)), 0.05),
               (0, 0))
    # vignette: darkened edges
    vig = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vig)
    dv.rectangle([0, 0, W, H], fill=70)
    dv.ellipse([-160, -160, W + 160, H + 160], fill=0)
    vig = vig.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGB", (W, H), (12, 8, 18))
    base.paste(Image.composite(dark, base, vig), (0, 0))
    # warm grade
    base.paste(Image.blend(base, Image.new("RGB", (W, H), (255, 196, 130)), 0.04),
               (0, 0))
    # cream frame + thin inner rule
    d = ImageDraw.Draw(base)
    d.rectangle([0, 0, W - 1, H - 1], outline=CREAM, width=16)
    d.rectangle([26, 26, W - 27, H - 27], outline=(60, 44, 30), width=2)


def main():
    base = Image.new("RGB", (W, H), CREAM)
    paint_sky(base)
    paint_stars(base)
    paint_moon(base)
    paint_sea(base)
    paint_arch(base)
    paint_cliff_town(base)
    paint_sailboats(base)
    paint_terrace(base)
    paint_couple(base)
    paint_table(base)
    paint_flowers(base)
    paint_lanterns(base)
    paint_title(base)
    paint_finish(base)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base.save(OUT, format="PNG", optimize=True, compress_level=9)
    print("wrote", OUT, os.path.getsize(OUT), "bytes", base.size)


if __name__ == "__main__":
    main()
