#!/usr/bin/env python3
"""Merges the existing pack PDFs into one bundle for Gumroad. Only reads
out/<theme>/pack.pdf and writes out/everything/ -- doesn't touch the live store.
"""
import io, json, os, time

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# Sellable single packs, in reading order. (sampler is the free funnel product;
# collection is itself a bundle — neither belongs inside the mega-bundle.)
PACKS = ["animals", "bible", "christmas", "food", "gardening",
         "kids", "nature", "ocean-life", "sports", "usa"]

BUNDLE_SLUG = "everything"
PRICE_USD = 19.99
BRAND = "Evergreen Puzzle Press"
GUMROAD_NOTE = "evergreenpuzzlepress.gumroad.com"
PAGE_W, PAGE_H = letter
GREEN = (0.16, 0.32, 0.25)


def _meta(theme):
    m = json.load(open(os.path.join(OUT, theme, "manifest.json")))
    p = m["product"]
    # the human-facing pack title, minus our internal "— Printable Pack" suffix
    title = p["title"].replace(" — Printable Pack", "").replace(" - Printable Pack", "")
    return {"title": title, "puzzles": int(p.get("puzzles", 0))}


def _front_matter(themes, total_puzzles):
    """Cover + 'what's inside' contents page as an in-memory PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    # --- cover ---
    c.setFillColorRGB(0.96, 0.95, 0.91)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    c.setFillColorRGB(*GREEN)
    c.rect(0, PAGE_H - 210, PAGE_W, 210, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 64, "THE EVERYTHING PACK")
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 110, "EVERY PRINTABLE WORD")
    c.drawCentredString(PAGE_W / 2, PAGE_H - 146, "SEARCH PACK WE MAKE")
    c.setFillColorRGB(*GREEN)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 262,
                        f"{total_puzzles} LARGE-PRINT PUZZLES  •  {len(themes)} THEMED PACKS")
    perks = [
        "Every theme in one instant download — animals to USA",
        "Big, easy-to-read letters — kind to the eyes",
        "Full solutions included for every puzzle",
        "Print at home on US Letter, unlimited copies, forever",
        "Personal, family, classroom & care-home use",
    ]
    c.setFont("Helvetica", 12)
    y = PAGE_H - 322
    for p in perks:
        c.setFillColorRGB(*GREEN)
        c.circle(PAGE_W / 2 - 205, y + 4, 3, stroke=0, fill=1)
        c.setFillColorRGB(0.15, 0.15, 0.15)
        c.drawString(PAGE_W / 2 - 193, y, p)
        y -= 26
    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(*GREEN)
    c.drawCentredString(PAGE_W / 2, 140, BRAND)
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.45, 0.45, 0.45)
    c.drawCentredString(PAGE_W / 2, 120, GUMROAD_NOTE)
    c.showPage()

    # --- contents / "what's inside" ---
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 120, "WHAT'S INSIDE")
    y = PAGE_H - 172
    for t in themes:
        c.setFont("Helvetica-Bold", 13)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.drawString(80, y, t["title"])
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawRightString(PAGE_W - 80, y, f"{t['puzzles']} puzzles")
        y -= 27
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(80, y + 6, PAGE_W - 80, y + 6)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(*GREEN)
    c.drawString(80, y - 16, "TOTAL")
    c.drawRightString(PAGE_W - 80, y - 16, f"{total_puzzles} puzzles")
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.45, 0.45, 0.45)
    c.drawCentredString(PAGE_W / 2, 96,
                        "Tip: print at 100% ('Actual Size') on US Letter. Grayscale is fine.")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def build():
    themes = [_meta(t) for t in PACKS]
    total = sum(t["puzzles"] for t in themes)

    writer = PdfWriter()
    for page in PdfReader(_front_matter(themes, total)).pages:
        writer.add_page(page)
    for t in PACKS:
        src = os.path.join(OUT, t, "pack.pdf")
        if not os.path.isfile(src):
            raise SystemExit(f"missing built pack: {src} (run factory.py --theme {t})")
        for page in PdfReader(src).pages:
            writer.add_page(page)

    outdir = os.path.join(OUT, BUNDLE_SLUG)
    os.makedirs(outdir, exist_ok=True)
    pdf_path = os.path.join(outdir, "everything-pack.pdf")
    with open(pdf_path, "wb") as f:
        writer.write(f)
    n_pages = len(writer.pages)
    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)

    title = f"The Everything Pack — All {len(PACKS)} Word Search Packs ({total} Large Print Puzzles PDF)"
    listing = (
        f"Every printable word search pack we make, in one instant download — "
        f"{total} large-print puzzles across {len(PACKS)} themes: "
        + ", ".join(t["title"].replace("Large Print ", "").replace(" Word Search", "")
                    for t in themes) + ".\n\n"
        "WHY THE EVERYTHING PACK:\n"
        f"• {total} puzzles — our deepest catalog in a single PDF\n"
        "• Extra-large, easy-to-read print — kind to aging eyes\n"
        "• Full solutions for every puzzle\n"
        "• Instant download — no shipping, print at home tonight\n"
        "• Print unlimited copies forever (personal, family, classroom & care-home use)\n\n"
        "Best value in the shop: every theme, one download, one low price. The ultimate "
        "gift for puzzle lovers, seniors, teachers, and care-home activity coordinators.\n\n"
        "Delivered as a print-ready US Letter PDF. Tap to download and start printing today."
    )

    manifest = {
        "theme": BUNDLE_SLUG,
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "product": {
            "title": title,
            "price_usd": PRICE_USD,
            "pdf": os.path.relpath(pdf_path, HERE),
            "puzzles": total,
            "packs_included": PACKS,
            "pages": n_pages,
            "gumroad_status": "NOT_LISTED",
            "suggested_slug": "everything-pack",
            "listing_description": listing,
        },
        "copy_source": "handwritten",
    }
    mpath = os.path.join(outdir, "manifest.json")
    json.dump(manifest, open(mpath, "w"), indent=2)

    print(f"BUNDLE -> {pdf_path}  ({len(PACKS)} packs, {total} puzzles, {n_pages} pages, {size_mb:.1f} MB)")
    print(f"MANIFEST -> {mpath}")
    return manifest


if __name__ == "__main__":
    build()
