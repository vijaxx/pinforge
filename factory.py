#!/usr/bin/env python3
"""Builds one theme end to end -- pack PDF, five pins, SEO copy, manifest.

    python3 factory.py --theme animals
    python3 factory.py --all
"""
import argparse, glob, json, os, time

import pack, pins, pincopy

HERE = os.path.dirname(os.path.abspath(__file__))
KDP_DIR = os.environ.get("KDP_DIR") or os.path.join(HERE, "..", "kdp")
if not os.path.isdir(KDP_DIR):  # fallback to canonical non-Desktop path
    KDP_DIR = os.path.expanduser("~/clauwork/kdp")
THEMES_DIR = os.path.join(KDP_DIR, "themes")
OUT_DIR = os.path.join(HERE, "out")
PRICE_USD = 4.99


def run_theme(theme):
    themes_path = os.path.join(THEMES_DIR, f"{theme}.json")
    if not os.path.exists(themes_path):
        raise SystemExit(f"no such theme: {themes_path}")
    outdir = os.path.join(OUT_DIR, theme)
    os.makedirs(outdir, exist_ok=True)

    data = json.load(open(themes_path))
    info = pack.build(themes_path, os.path.join(outdir, "pack.pdf"))
    pin_list = pins.build(themes_path, os.path.join(outdir, "pins"), count=5)
    variants, src = pincopy.generate(data.get("title", "Word Search"), len(data["puzzles"]), 5)

    # 2026-06-30 FIX: rebuilding an already-listed theme used to silently OVERWRITE the
    # manifest, wiping gumroad_status/gumroad_url (run_batch would then drop the pack from
    # the pin queue, or list_gumroad could create a DUPLICATE listing) and resetting every
    # pin's posted=False (duplicate posts). Now MERGE onto any existing manifest: preserve
    # the product's gumroad_* fields and each pin's prior posted state by matching index.
    mpath = os.path.join(outdir, "manifest.json")
    prior = json.load(open(mpath)) if os.path.exists(mpath) else {}
    prior_product = prior.get("product", {})
    prior_pins = prior.get("pins", [])

    manifest = {
        "theme": theme,
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "product": {
            "title": info["title"],
            "price_usd": PRICE_USD,
            "pdf": os.path.relpath(info["pdf"], HERE),
            "puzzles": info["puzzles"],
            "gumroad_status": prior_product.get("gumroad_status", "NOT_LISTED"),
            **{k: v for k, v in prior_product.items()
               if k.startswith("gumroad_") and k != "gumroad_status"},
        },
        "pins": [
            {"image": os.path.relpath(p["file"], HERE),
             "headline_on_image": p["headline"],
             "title": v["title"],
             "description": v["description"],
             "posted": (prior_pins[i].get("posted", False) if i < len(prior_pins) else False),
             **({"posted_at": prior_pins[i]["posted_at"]}
                if i < len(prior_pins) and prior_pins[i].get("posted_at") else {})}
            for i, (p, v) in enumerate(zip(pin_list, variants))
        ],
        "copy_source": src,
    }
    json.dump(manifest, open(mpath, "w"), indent=2)
    print(f"MANIFEST -> {mpath}")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        themes = sorted(os.path.splitext(os.path.basename(t))[0]
                        for t in glob.glob(os.path.join(THEMES_DIR, "*.json")))
        for t in themes:
            print(f"\n=== {t} ===")
            run_theme(t)
    elif a.theme:
        run_theme(a.theme)
    else:
        ap.error("pass --theme <name> or --all")


if __name__ == "__main__":
    main()
