"""
Generates the browser-extension toolbar icons (16/48/128 px PNGs) from the
same shield-mark geometry used by Logo.tsx (admin-dashboard) and
components/Logo.tsx (browser-extension), so the toolbar icon, popup header,
and dashboard sidebar all show one consistent PromptShield AI brand mark.

Usage:
    python3 generate_icons.py
"""
from PIL import Image, ImageDraw
import math
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "public", "icons")
SIZES = [16, 48, 128]

BG_TOP = (134, 59, 255)      # #863bff
BG_BOTTOM = (76, 26, 219)    # #4c1adb
SHIELD_WHITE = (255, 255, 255, 245)
CHECK_COLOR = (126, 20, 255, 255)  # #7e14ff


def rounded_rect_gradient(size: int, radius_ratio: float = 0.22) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        t = y / max(size - 1, 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        for x in range(size):
            grad.putpixel((x, y), (r, g, b, 255))
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    radius = max(2, int(size * radius_ratio))
    mdraw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)
    return img


def shield_polygon(size: int):
    # Matches the SVG path M24 4 L40 10 V22 C40 33 33.5 41 24 45 C14.5 41 8 33 8 22 V10 Z
    # scaled from a 48x48 viewbox to `size`.
    s = size / 48.0
    top = (24 * s, 4 * s)
    right_top = (40 * s, 10 * s)
    right_mid = (40 * s, 22 * s)
    right_bottom_ctrl = (33.5 * s, 41 * s)
    bottom = (24 * s, 45 * s)
    left_bottom_ctrl = (14.5 * s, 41 * s)
    left_mid = (8 * s, 22 * s)
    left_top = (8 * s, 10 * s)

    def bezier(p0, p1, p2, steps=10):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
            pts.append((x, y))
        return pts

    pts = [top, right_top, right_mid]
    ctrl_r = (40 * s, 33 * s)
    pts += bezier(right_mid, ctrl_r, bottom)[1:]
    ctrl_l = (8 * s, 33 * s)
    pts += bezier(bottom, ctrl_l, left_mid)[1:]
    pts += [left_top]
    return pts


def make_icon(size: int) -> Image.Image:
    base = rounded_rect_gradient(size)
    shield_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shield_layer)
    poly = shield_polygon(size)
    sdraw.polygon(poly, fill=SHIELD_WHITE)

    s = size / 48.0
    check_pts = [(17 * s, 23.5 * s), (21.8 * s, 28.5 * s), (31.5 * s, 17.5 * s)]
    width = max(1, int(3.4 * s))
    sdraw.line(check_pts, fill=CHECK_COLOR, width=width, joint="curve")
    r = width / 2
    for p in [check_pts[0], check_pts[-1]]:
        sdraw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=CHECK_COLOR)

    base.alpha_composite(shield_layer)
    return base


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for size in SIZES:
        icon = make_icon(size)
        path = os.path.join(OUT_DIR, f"icon{size}.png")
        icon.save(path)
        print(f"wrote {path} ({size}x{size})")


if __name__ == "__main__":
    main()
