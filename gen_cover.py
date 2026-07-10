#!/usr/bin/env python3
"""
gen_cover.py — generate the two Gumroad cover images that gen_store_assets.py never
produced: the per-theme ocean-life cover (it was added after assets were last built)
and a dedicated premium cover for the Everything Pack mega-bundle.

Read-only on the KDP theme/engine dependency (same as pins.py/pack.py/the daily poster);
writes only into this project's out/. Deterministic.

    /usr/bin/python3 gen_cover.py            # both
    /usr/bin/python3 gen_cover.py ocean      # just ocean-life
    /usr/bin/python3 gen_cover.py everything # just the bundle
"""
import json, os, sys

import pins  # palette + grid/font helpers (resolves the KDP engine itself)
import gen_store_assets as G  # cover()/thumb() for single packs
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
KDP_DIR = os.path.dirname(pins.ws.__file__)          # resolved KDP engine dir
THEMES_DIR = os.path.join(KDP_DIR, "themes")
SUP = "/System/Library/Fonts/Supplemental/"

# Packs inside the Everything Pack, in reading order (mirrors build_bundle.PACKS).
BUNDLE_PACKS = ["animals", "bible", "christmas", "food", "gardening",
                "kids", "nature", "ocean-life", "sports", "usa"]
GREEN = ("#f3f1e7", "#28503c", "#d9a441", "#1d1d1b")  # bg, band, accent, ink


def gen_ocean():
    """Per-theme cover + thumb in the exact gen_store_assets house style."""
    tp = os.path.join(THEMES_DIR, "ocean-life.json")
    data = json.load(open(tp))
    palette = pins.PALETTES.get("ocean-life",
                                pins.PALETTES.get(data.get("palette"), pins.DEFAULT_PALETTE))
    outdir = os.path.join(OUT, "ocean-life")
    os.makedirs(outdir, exist_ok=True)
    G.cover(data, palette, "ocean-life", os.path.join(outdir, "cover.png"))
    G.thumb(data, palette, "ocean-life", os.path.join(outdir, "thumb.png"))
    print("ASSETS -> out/ocean-life/cover.png + thumb.png")


def gen_everything():
    """Dedicated 1600x900 hero for the $19.99 flagship bundle: left value column +
    right real-grid card (consistent with the single-pack covers)."""
    m = json.load(open(os.path.join(OUT, "everything", "manifest.json")))
    p = m["product"]
    total = int(p.get("puzzles", 0))
    n_packs = len(p.get("packs_included", BUNDLE_PACKS))

    bg, band, accent, ink = GREEN
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img, "RGBA")

    # left value column
    d.rectangle([0, 0, 820, H], fill=band)
    f_eyebrow = pins.font(SUP + "Arial Bold.ttf", 30)
    d.text((70, 84), "THE COMPLETE COLLECTION", font=f_eyebrow, fill=accent)

    f_title = pins.font(SUP + "Georgia Bold.ttf", 78)
    y = 150
    for ln in ["The Everything", "Pack"]:
        d.text((70, y), ln, font=f_title, fill="#ffffff")
        y += 88

    f_lead = pins.font(SUP + "Georgia Bold.ttf", 34)
    d.text((70, y + 14), f"All {n_packs} themed packs in one PDF", font=f_lead, fill="#f2efe6")

    f_sub = pins.font(SUP + "Arial.ttf", 30)
    yy = y + 92
    for line in [f"{total} large-print puzzles + full solutions",
                 f"{n_packs} themes — animals to USA",
                 "Instant download PDF • US Letter",
                 "Print unlimited copies, forever"]:
        d.ellipse([70, yy + 11, 84, yy + 25], fill=accent)
        d.text((104, yy), line, font=f_sub, fill="#f2efe6")
        yy += 50

    # "BEST VALUE" pill
    f_pill = pins.font(SUP + "Arial Bold.ttf", 28)
    pill = "BEST VALUE IN THE SHOP"
    pw = d.textlength(pill, font=f_pill) + 56
    d.rounded_rectangle([70, H - 188, 70 + pw, H - 188 + 56], radius=28, fill=accent)
    d.text((98, H - 174), pill, font=f_pill, fill="#241a07")

    f_brand = pins.font(SUP + "Georgia Bold.ttf", 32)
    d.text((70, H - 96), "Evergreen Puzzle Press", font=f_brand, fill=accent)

    # right: real aggregated grid preview card (same card system as gen_store_assets.cover)
    all_words = []
    for slug in BUNDLE_PACKS:
        tp = os.path.join(THEMES_DIR, f"{slug}.json")
        if os.path.exists(tp):
            td = json.load(open(tp))
            all_words += [w for pz in td.get("puzzles", []) for w in pz["words"]]
    grid_img, _ = pins.mini_grid_image(all_words, n=10, seed=42)
    card = (880, 70, 1540, 830)
    d.rounded_rectangle([card[0] + 10, card[1] + 12, card[2] + 10, card[3] + 12],
                        radius=24, fill=(0, 0, 0, 30))
    d.rounded_rectangle(card, radius=24, fill="#ffffff", outline="#e3ded2", width=2)
    gsize = 600
    grid_img = grid_img.resize((gsize, gsize), Image.LANCZOS)
    img.paste(grid_img, (card[0] + (card[2] - card[0] - gsize) // 2,
                         card[1] + (card[3] - card[1] - gsize) // 2))

    out_path = os.path.join(OUT, "everything", "cover.png")
    img.save(out_path)
    print(f"ASSETS -> out/everything/cover.png  ({total} puzzles, {n_packs} packs)")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("both", "ocean"):
        gen_ocean()
    if which in ("both", "everything"):
        gen_everything()


if __name__ == "__main__":
    main()
