#!/usr/bin/env python3
"""
gen_promo.py — pins + store assets for the two funnel products:
  out/sampler/    FREE 10-puzzle sampler (lead magnet — the algorithm fuel)
  out/collection/ $14.99 Complete Collection (the AOV raiser)

    /usr/bin/python3 gen_promo.py
"""
import json, os, glob

import pins, gen_store_assets

HERE = os.path.dirname(os.path.abspath(__file__))
_KDP = os.environ.get("KDP_DIR") or os.path.join(HERE, "..", "kdp")
if not os.path.isdir(_KDP):  # live dir moved; fall back to the canonical KDP engine location
    _KDP = os.path.expanduser("~/Desktop/clauwork/kdp")
THEMES = os.path.join(_KDP, "themes")


def combined_data(title):
    """A pseudo-theme drawing words from every real theme (for grid previews)."""
    puzzles = []
    for tp in sorted(glob.glob(os.path.join(THEMES, "*.json"))):
        puzzles.extend(json.load(open(tp))["puzzles"][:2])
    return {"title": title, "puzzles": puzzles, "author": "Evergreen Puzzle Press"}


SAMPLER_PINS = [
    ("FREE Printable Word Search — Large Print", "100% FREE  •  INSTANT DOWNLOAD"),
    ("10 Free Large-Print Puzzles to Print at Home", "100% FREE  •  NO SIGNUP NEEDED"),
    ("Free Word Search Printables for Seniors", "100% FREE  •  LARGE PRINT"),
    ("Free Screen-Free Activity — Print Tonight", "100% FREE  •  FULL SOLUTIONS"),
    ("FREE 10-Puzzle Word Search Pack (PDF)", "100% FREE  •  PRINT FOREVER"),
]

COLLECTION_PINS = [
    ("329 Large-Print Puzzles — The Complete Collection", "ALL 7 PACKS  •  SAVE 57%"),
    ("Every Word Search Pack We Make — One Download", "329 PUZZLES  •  $14.99"),
    ("The Ultimate Printable Puzzle Library", "ALL 7 PACKS  •  FULL SOLUTIONS"),
]


def main():
    sampler = combined_data("The Evergreen Puzzle Sampler")
    collection = combined_data("Word Search Complete Collection")

    # sampler: green palette, FREE pills
    pal = pins.PALETTES["nature"]
    outdir = os.path.join(HERE, "out", "sampler", "pins")
    os.makedirs(outdir, exist_ok=True)
    s_pins = []
    for i, (head, pill) in enumerate(SAMPLER_PINS):
        path = os.path.join(outdir, f"pin_{i+1:02d}.png")
        pins.render_pin(sampler, pal, head, seed=300 + i * 11, out_path=path,
                        pill_text=pill, cta_text="Free PDF  •  Print at Home  •  Large Print")
        s_pins.append({"file": path, "headline": head})
        print("PIN  ->", path)

    # collection: gold-on-green USA palette feel, value pills
    pal2 = pins.PALETTES["animals"]
    outdir2 = os.path.join(HERE, "out", "collection", "pins")
    os.makedirs(outdir2, exist_ok=True)
    c_pins = []
    for i, (head, pill) in enumerate(COLLECTION_PINS):
        path = os.path.join(outdir2, f"pin_{i+1:02d}.png")
        pins.render_pin(collection, pal2, head, seed=400 + i * 13, out_path=path,
                        pill_text=pill, cta_text="329 Puzzles  •  Instant Download")
        c_pins.append({"file": path, "headline": head})
        print("PIN  ->", path)

    # store assets (cover + thumb) for both
    for slug, data, pal_ in (("sampler", sampler, pal), ("collection", collection, pal2)):
        outdir3 = os.path.join(HERE, "out", slug)
        gen_store_assets.cover(data, pal_, slug, os.path.join(outdir3, "cover.png"))
        gen_store_assets.thumb(data, pal_, slug, os.path.join(outdir3, "thumb.png"))
        print(f"ASSETS -> out/{slug}/cover.png + thumb.png")

    # manifests
    json.dump({
        "theme": "sampler",
        "product": {"title": "FREE Large Print Word Search Sampler — 10 Printable Puzzles (PDF)",
                    "price_usd": 0, "pdf": "out/sampler/sampler.pdf", "puzzles": 10,
                    "gumroad_status": "NOT_LISTED",
                    "url": "https://evergreenpuzzlepress.gumroad.com/l/free-word-search-sampler"},
        "pins": [{"image": os.path.relpath(p["file"], HERE), "headline_on_image": p["headline"],
                  "title": t, "description": d, "posted": False}
                 for p, (t, d) in zip(s_pins, [
            ("FREE Printable Word Search — 10 Large Print Puzzles PDF (Instant Download)",
             "Grab 10 free large-print word search puzzles — animals, nature, food, kids and more. Instant download PDF, print at home as many times as you like, full solutions included. Perfect for seniors, caregivers, teachers, and rainy days. Tap to get your free pack."),
            ("Free Large Print Word Search Printables for Seniors — PDF Download",
             "A completely free 10-puzzle word search sampler in extra-large print that's easy on the eyes. Print unlimited copies for yourself, your family, or your care-home activity group. Solutions included. Download free today — no catch."),
            ("Free Printable Puzzles — Screen-Free Activity for All Ages",
             "Need a calm, screen-free activity tonight? Download 10 free large-print word search puzzles across 7 fun themes. US Letter PDF, printer-friendly, answers at the back. Free instant download — save this pin for later!"),
            ("FREE Word Search Pack — Print at Home Tonight (10 Puzzles)",
             "Free 10-puzzle word search pack in big, easy-to-read print. Seven themes: animals, nature, food, faith, kids, USA, Christmas. Print at home forever, full solutions included. Tap for your free instant download."),
            ("Free Brain Games for Adults — 10 Printable Word Searches",
             "Keep your mind sharp the relaxing way — free! 10 large-print word search puzzles, printable PDF, full answer keys. Loved by seniors, caregivers, and puzzle fans. Download your free sampler now."),
        ])],
        "copy_source": "handwritten",
    }, open(os.path.join(HERE, "out", "sampler", "manifest.json"), "w"), indent=2)

    json.dump({
        "theme": "collection",
        "product": {"title": "Word Search Complete Collection — All 7 Packs (329 Puzzles PDF)",
                    "price_usd": 14.99, "pdf": "(7 pack PDFs attached)", "puzzles": 329,
                    "gumroad_status": "NOT_LISTED",
                    "url": "https://evergreenpuzzlepress.gumroad.com/l/complete-collection"},
        "pins": [{"image": os.path.relpath(p["file"], HERE), "headline_on_image": p["headline"],
                  "title": t, "description": d, "posted": False}
                 for p, (t, d) in zip(c_pins, [
            ("Word Search Complete Collection — 329 Large Print Puzzles PDF (All 7 Packs)",
             "Every large-print word search pack we make, in one instant download: 329 puzzles across animals, nature, food, Bible, kids, USA, and Christmas themes. Save 57% versus buying separately. Print at home forever, full solutions included. The ultimate gift for puzzle lovers."),
            ("329 Printable Word Search Puzzles — Ultimate Large Print Bundle",
             "One download, a year of puzzles: 329 large-print word searches across 7 themed packs. US Letter PDFs, printer-friendly, all solutions included. Perfect for seniors, care homes, classrooms, and road trips. Tap to see the complete collection."),
            ("The Only Puzzle Bundle You'll Ever Need — All 7 Word Search Packs",
             "Stop printing one puzzle at a time. Get all 7 of our large-print word search packs — 329 puzzles — in a single instant download at 57% off. Full solutions, unlimited printing, every theme from animals to Christmas. A thoughtful gift that lasts all year."),
        ])],
        "copy_source": "handwritten",
    }, open(os.path.join(HERE, "out", "collection", "manifest.json"), "w"), indent=2)
    print("MANIFESTS -> out/sampler + out/collection")


if __name__ == "__main__":
    main()
