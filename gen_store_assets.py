#!/usr/bin/env python3
"""Gumroad store images per theme: a horizontal cover and a square thumbnail."""
import json, os, glob
from PIL import Image, ImageDraw, ImageFont

import pins  # palette map + mini_grid_image + font helpers

HERE = os.path.dirname(os.path.abspath(__file__))
KDP_DIR = os.environ.get("KDP_DIR") or os.path.join(HERE, "..", "kdp")
if not os.path.isdir(KDP_DIR):  # live dir moved; fall back to the canonical KDP engine location
    KDP_DIR = os.path.expanduser("~/Desktop/clauwork/kdp")
THEMES_DIR = os.path.join(KDP_DIR, "themes")
SUP = "/System/Library/Fonts/Supplemental/"


def cover(data, palette, slug, out_path):
    bg, band, accent, ink = palette
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img, "RGBA")

    # left text column
    d.rectangle([0, 0, 760, H], fill=band)
    f_eyebrow = pins.font(SUP + "Arial Bold.ttf", 30)
    eyebrow_fill = accent if pins._lum(accent) > 0.45 else bg
    d.text((70, 90), "PRINTABLE PUZZLE PACK", font=f_eyebrow, fill=eyebrow_fill)

    title = data.get("title", "Word Search")
    f_title = pins.font(SUP + "Georgia Bold.ttf", 64)
    lines = pins.wrap_to_width(d, title, f_title, 620)
    y = 160
    for ln in lines:
        d.text((70, y), ln, font=f_title, fill="#ffffff")
        y += 74

    n = len(data.get("puzzles", []))
    f_sub = pins.font(SUP + "Arial.ttf", 30)
    y += 24
    for line in [f"{n} large-print puzzles + full solutions",
                 "Instant download PDF • US Letter",
                 "Print unlimited copies, forever"]:
        d.ellipse([70, y + 10, 84, y + 24], fill=accent)
        d.text((102, y), line, font=f_sub, fill="#f2efe6")
        y += 52

    f_brand = pins.font(SUP + "Georgia Bold.ttf", 32)
    d.text((70, H - 110), data.get("author", "Evergreen Puzzle Press"),
           font=f_brand, fill=eyebrow_fill)

    # right: real grid preview card
    all_words = [w for p in data["puzzles"] for w in p["words"]]
    grid_img, _ = pins.mini_grid_image(all_words, n=10, seed=42)
    card = (820, 70, 1540, 830)
    d.rounded_rectangle([card[0] + 10, card[1] + 12, card[2] + 10, card[3] + 12],
                        radius=24, fill=(0, 0, 0, 30))
    d.rounded_rectangle(card, radius=24, fill="#ffffff", outline="#e3ded2", width=2)
    gsize = 640
    grid_img = grid_img.resize((gsize, gsize), Image.LANCZOS)
    img.paste(grid_img, (card[0] + (card[2] - card[0] - gsize) // 2,
                         card[1] + (card[3] - card[1] - gsize) // 2))

    img.save(out_path)


def thumb(data, palette, slug, out_path):
    bg, band, accent, ink = palette
    S = 600
    img = Image.new("RGB", (S, S), band)
    d = ImageDraw.Draw(img, "RGBA")
    all_words = [w for p in data["puzzles"] for w in p["words"]]
    grid_img, _ = pins.mini_grid_image(all_words, n=10, seed=42)
    gsize = 420
    grid_img = grid_img.resize((gsize, gsize), Image.LANCZOS)
    d.rounded_rectangle([(S - gsize) / 2 - 14, 60 - 14, (S + gsize) / 2 + 14, 60 + gsize + 14],
                        radius=18, fill="#ffffff")
    img.paste(grid_img, ((S - gsize) // 2, 60))
    n = len(data.get("puzzles", []))
    f = pins.font(SUP + "Arial Bold.ttf", 34)
    t = f"{n} LARGE-PRINT PUZZLES"
    tw = d.textlength(t, font=f)
    fill = accent if pins._lum(accent) > 0.45 else "#ffffff"
    d.text(((S - tw) / 2, S - 74), t, font=f, fill=fill)
    img.save(out_path)


def main():
    for tp in sorted(glob.glob(os.path.join(THEMES_DIR, "*.json"))):
        slug = os.path.splitext(os.path.basename(tp))[0]
        data = json.load(open(tp))
        palette = pins.PALETTES.get(slug, pins.PALETTES.get(data.get("palette"), pins.DEFAULT_PALETTE))
        outdir = os.path.join(HERE, "out", slug)
        os.makedirs(outdir, exist_ok=True)
        cover(data, palette, slug, os.path.join(outdir, "cover.png"))
        thumb(data, palette, slug, os.path.join(outdir, "thumb.png"))
        print(f"ASSETS -> out/{slug}/cover.png + thumb.png")


if __name__ == "__main__":
    main()
