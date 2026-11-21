#!/usr/bin/env python3
"""VELMORA — The Glass Tide Coast.

Deterministic 1024x1024 travel poster, drawn entirely with Pillow.
Standard library + Pillow only, no network. Run: python3 main.py
Writes /output/entry.png (creates /output if needed).
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W = H = 1024
OUT = "/output/entry.png"
SEED = 20261121
FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(name, size):
    path = os.path.join(FONT_DIR, name)
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(width, height, stops):
    """Vertical gradient through color stops [(pos, rgb), ...]."""
    grad = Image.new("RGB", (1, height))
    px = grad.load()
    for y in range(height):
        t = y / max(1, height - 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                px[0, y] = lerp(c0, c1, f)
                break
        else:
            px[0, y] = stops[-1][1]
    return grad.resize((width, height))


def glow_layer(size, color, rings=48):
    """Radial glow: bright center fading to transparent."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = size[0] // 2, size[1] // 2
    rmax = size[0] // 2
    for i in range(rings, 0, -1):
        r = rmax * i / rings
        a = int(10 * (1 - i / rings) ** 2) + 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (a,))
    return layer


def tracked(draw, center_x, y, text, fnt, fill, tracking=0, shadow=None):
    """Draw text centered with letter tracking."""
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = center_x - total / 2
    for ch, w in zip(text, widths):
        if shadow:
            draw.text((x + shadow[0], y + shadow[1]), ch, font=fnt, fill=shadow[2])
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += w + tracking
    return total


def main():
    rng = random.Random(SEED)
    horizon = 640
    img = Image.new("RGB", (W, H))

    # ---- sky: deep indigo -> violet -> amber dusk ----
    sky = vgrad(W, horizon + 1, [
        (0.00, (16, 10, 46)),
        (0.45, (58, 32, 96)),
        (0.78, (122, 62, 110)),
        (1.00, (232, 150, 74)),
    ])
    img.paste(sky, (0, 0))

    # ---- stars (upper sky only) ----
    stars = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stars)
    for _ in range(190):
        x = rng.uniform(0, W)
        y = rng.uniform(0, horizon * 0.55)
        r = rng.choice([0.7, 0.9, 1.1, 1.4])
        a = rng.randint(60, 210)
        sd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 244, 214, a))
    img = Image.alpha_composite(img.convert("RGBA"), stars)

    # ---- moon with glow (low, right of center) ----
    mx, my, mr = 700, 330, 66
    img.paste(glow_layer((560, 560), (255, 196, 110)), (mx - 280, my - 280), glow_layer((560, 560), (255, 196, 110)))
    d = ImageDraw.Draw(img)
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(255, 233, 176))
    d.ellipse([mx - mr + 12, my - mr + 10, mx + mr - 26, my + mr - 14], fill=(255, 240, 196))
    # faint moon maria
    for (ox, oy, rr) in [(-18, -8, 12), (14, 18, 9), (22, -20, 7)]:
        d.ellipse([mx + ox - rr, my + oy - rr, mx + ox + rr, my + oy + rr], fill=(238, 214, 158))

    # ---- sea: deep teal -> glass-green glow at horizon ----
    sea = vgrad(W, H - horizon, [
        (0.00, (64, 166, 138)),
        (0.25, (24, 104, 102)),
        (0.65, (10, 52, 66)),
        (1.00, (6, 30, 46)),
    ])
    img.paste(sea, (0, horizon))

    # ---- moonlight path on the water ----
    refl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(refl)
    for _ in range(260):
        y = rng.uniform(horizon + 6, H - 60)
        spread = 26 + (y - horizon) * 0.42
        x = rng.gauss(mx, spread)
        ln = rng.uniform(8, 46) * (1 + (y - horizon) / 260)
        a = int(rng.uniform(28, 120) * max(0.25, 1 - (y - horizon) / 520))
        rd.line([x - ln / 2, y, x + ln / 2, y], fill=(255, 214, 140, a), width=2)
    img = Image.alpha_composite(img, refl)
    d = ImageDraw.Draw(img)

    # ---- wave foam arcs ----
    for yy, alpha in [(700, 60), (790, 46), (900, 34)]:
        for seg in range(7):
            x0 = rng.uniform(0, W - 260)
            ln = rng.uniform(90, 260)
            d.arc([x0, yy - 10, x0 + ln, yy + 10], 200, 340, fill=(190, 235, 220, alpha) if False else (190, 235, 220), width=2)

    # ---- right rock arch framing the moon ----
    arch = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ad = ImageDraw.Draw(arch)
    ad.ellipse([548, 96, 916, 700], fill=(18, 13, 30, 255))
    # punch the opening (moon shows through)
    ad.ellipse([618, 190, 852, 690], fill=(0, 0, 0, 0))
    # rocky top edge: jittered dark boulders along the outer rim
    for ang in range(195, 345, 6):
        rad = math.radians(ang)
        cx = 732 + 184 * math.cos(rad) + rng.uniform(-8, 8)
        cy = 398 + 302 * math.sin(rad) + rng.uniform(-8, 8)
        rr = rng.uniform(14, 30)
        ad.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(18, 13, 30, 255))
    # right cliff mass
    ad.polygon([(880, 300), (1024, 240), (1024, H), (880, H)], fill=(14, 10, 26, 255))
    for (bx, by, rr) in [(920, 330, 26), (990, 300, 30), (905, 430, 22), (975, 520, 26)]:
        ad.ellipse([bx - rr, by - rr, bx + rr, by + rr], fill=(14, 10, 26, 255))
    # amber rim light on the arch inner edge
    rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rmd = ImageDraw.Draw(rim)
    rmd.arc([618, 190, 852, 690], 205, 335, fill=(255, 190, 110, 170), width=5)
    rim = rim.filter(ImageFilter.GaussianBlur(2))
    img = Image.alpha_composite(img, arch)
    img = Image.alpha_composite(img, rim)
    d = ImageDraw.Draw(img)

    # ---- left cliff + lighthouse ----
    d.polygon([(0, 470), (120, 430), (230, 520), (260, 700), (180, H), (0, H)], fill=(16, 11, 28))
    d.polygon([(0, 470), (120, 430), (230, 520), (150, 560), (0, 560)], fill=(24, 17, 40))
    # lighthouse tower on the cliff top
    lx, ly = 118, 356
    d.rectangle([lx - 13, ly, lx + 13, ly + 78], fill=(232, 222, 196))
    d.rectangle([lx - 13, ly + 22, lx + 13, ly + 34], fill=(150, 40, 40))
    d.rectangle([lx - 13, ly + 52, lx + 13, ly + 64], fill=(150, 40, 40))
    d.rectangle([lx - 17, ly - 8, lx + 17, ly], fill=(30, 24, 48))
    d.ellipse([lx - 11, ly - 24, lx + 11, ly - 2], fill=(255, 214, 130))
    d.ellipse([lx - 8, ly - 21, lx + 8, ly - 5], fill=(255, 240, 190))
    # beam across the sea
    beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beam)
    bd.polygon([(lx + 8, ly - 12), (760, ly + 96), (760, ly + 150), (lx + 8, ly - 2)], fill=(255, 214, 130, 52))
    bd.polygon([(lx + 8, ly - 12), (420, ly + 26), (420, ly + 44), (lx + 8, ly - 2)], fill=(255, 226, 160, 90))
    beam = beam.filter(ImageFilter.GaussianBlur(6))
    img = Image.alpha_composite(img, beam)
    d = ImageDraw.Draw(img)

    # ---- foreground shore ----
    shore = vgrad(W, H - 880, [(0.0, (20, 26, 34)), (1.0, (8, 10, 18))])
    img.paste(shore, (0, 880))
    d = ImageDraw.Draw(img)
    d.line([0, 880, W, 880], fill=(200, 235, 220), width=2)
    for _ in range(60):
        x = rng.uniform(0, W)
        y = rng.uniform(882, 900)
        d.line([x, y, x + rng.uniform(6, 26), y], fill=(210, 238, 224), width=1)
    for (rx, ry, rr) in [(90, 950, 26), (150, 985, 18), (880, 960, 30), (950, 990, 20)]:
        d.ellipse([rx - rr, ry - rr * 0.6, rx + rr, ry + rr * 0.6], fill=(12, 12, 22))

    # ---- one person on the shore, facing the glowing sea ----
    px, py = 430, 884  # feet
    d.ellipse([px - 6, py - 62, px + 6, py - 50], fill=(10, 8, 16))          # head
    d.polygon([(px - 9, py - 50), (px + 9, py - 50), (px + 7, py - 16), (px - 7, py - 16)], fill=(10, 8, 16))  # coat
    d.line([px - 4, py - 16, px - 6, py], fill=(10, 8, 16), width=4)         # legs
    d.line([px + 4, py - 16, px + 6, py], fill=(10, 8, 16), width=4)
    d.line([px + 9, py - 46, px + 15, py - 30], fill=(10, 8, 16), width=3)   # arm
    d.line([px + 7, py - 48, px + 8, py - 16], fill=(255, 190, 110), width=1)  # amber rim light
    d.ellipse([px - 9, py + 2, px + 9, py + 8], fill=(30, 60, 58))           # wet-sand reflection
    d.ellipse([px - 7, py + 9, px + 7, py + 13], fill=(24, 48, 48))

    # ---- titles (travel-poster type) ----
    title_f = font("DejaVuSerif-Bold.ttf", 118)
    tag_f = font("DejaVuSans.ttf", 34)
    small_f = font("DejaVuSans-Bold.ttf", 24)
    tracked(d, W // 2, 64, "VELMORA", title_f, (247, 234, 208), tracking=14,
            shadow=(4, 5, (10, 6, 26)))
    tracked(d, W // 2, 196, "THE GLASS TIDE COAST", tag_f, (242, 192, 120), tracking=8)
    d.line([W // 2 - 130, 246, W // 2 + 130, 246], fill=(242, 192, 120), width=2)
    # bottom line
    tracked(d, W // 2, 962, "VISIT THE UNSEEN", small_f, (232, 220, 196), tracking=10)
    d.line([W // 2 - 210, 1004, W // 2 - 150, 1004], fill=(242, 192, 120), width=2)
    d.line([W // 2 + 150, 1004, W // 2 + 210, 1004], fill=(242, 192, 120), width=2)

    # ---- grain (seeded, subtle) + vignette ----
    noise = Image.new("L", (256, 256))
    npx = noise.load()
    for y in range(256):
        for x in range(256):
            npx[x, y] = 128 + rng.randint(-14, 14)
    noise = noise.resize((W, H))
    gray = Image.merge("RGB", (noise, noise, noise))
    img = Image.blend(img.convert("RGB"), gray, 0.045)

    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    for i in range(60, 0, -1):
        a = int(150 * (1 - i / 60) ** 2)
        r = 760 * i / 60
        vd.ellipse([W // 2 - r, H // 2 - r * 0.92, W // 2 + r, H // 2 + r * 0.92], fill=a)
    black = Image.new("RGB", (W, H), (6, 4, 14))
    img = Image.composite(black, img, vig)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
