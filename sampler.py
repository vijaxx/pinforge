#!/usr/bin/env python3
"""
sampler.py — FREE 10-puzzle lead-magnet pack. The funnel entrance:
free pins get the saves/clicks on Pinterest -> $0 Gumroad product captures the
email -> the PDF's back pages carry CLICKABLE links to the 7 paid packs, the
$14.99 Complete Collection, and the Amazon paperbacks.

    /usr/bin/python3 sampler.py
"""
import json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kdp"))
import wordsearch as ws  # noqa: E402

from reportlab.pdfgen import canvas  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402

PAGE_W, PAGE_H = letter
AUTHOR = "Evergreen Puzzle Press"
STORE = "https://evergreenpuzzlepress.gumroad.com"
COLLECTION_URL = STORE + "/l/complete-collection"

# (theme slug, how many puzzles to sample)
PICKS = [("animals", 2), ("nature", 2), ("food", 1), ("bible", 1),
         ("kids", 2), ("usa", 1), ("christmas", 1)]

PACKS = [  # title, n, live URL — printed AND clickable in the back pages
    ("Large Print Animal Word Search (44 puzzles)", STORE + "/l/animal-word-search"),
    ("Large Print Bible Word Search (48 puzzles)", STORE + "/l/bible-word-search"),
    ("Large Print Christmas Word Search (48 puzzles)", STORE + "/l/christmas-word-search"),
    ("Large Print Food & Kitchen Word Search (44 puzzles)", STORE + "/l/food-word-search"),
    ("Word Search for Kids (48 puzzles)", STORE + "/l/kids-word-search"),
    ("Large Print Nature Word Search (48 puzzles)", STORE + "/l/nature-word-search"),
    ("Large Print USA Word Search (49 puzzles)", STORE + "/l/usa-word-search"),
]


def cover(c):
    c.setFillColorRGB(0.96, 0.95, 0.91)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    c.setFillColorRGB(0.16, 0.32, 0.25)
    c.rect(0, PAGE_H - 210, PAGE_W, 210, stroke=0, fill=1)
    c.setFillColorRGB(0.88, 0.64, 0.35)
    c.setFont("SansB", 15)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 62, "A FREE GIFT FROM EVERGREEN PUZZLE PRESS")
    c.setFillColorRGB(1, 1, 1)
    c.setFont("SansB", 30)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 112, "THE EVERGREEN")
    c.drawCentredString(PAGE_W / 2, PAGE_H - 150, "PUZZLE SAMPLER")
    c.setFillColorRGB(0.16, 0.32, 0.25)
    c.setFont("SansB", 17)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 280, "10 LARGE-PRINT WORD SEARCH PUZZLES")
    c.setFont("Sans", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 310, "Animals • Nature • Food • Faith • Kids • USA • Christmas")
    c.setFont("Sans", 12)
    perks = ["Big, easy-to-read letters — kind to the eyes",
             "Full solutions included",
             "Print as many copies as you like, forever",
             "100% free — share it with a friend"]
    y = PAGE_H - 400
    for p in perks:
        c.setFillColorRGB(0.16, 0.32, 0.25)
        c.circle(PAGE_W / 2 - 140, y + 4, 3, stroke=0, fill=1)
        c.setFillColorRGB(0.15, 0.15, 0.15)
        c.drawString(PAGE_W / 2 - 128, y, p)
        y -= 26
    c.setFont("SansB", 13)
    c.setFillColorRGB(0.16, 0.32, 0.25)
    c.drawCentredString(PAGE_W / 2, 130, AUTHOR)
    c.setFont("Sans", 11)
    c.setFillColorRGB(0.45, 0.45, 0.45)
    c.drawCentredString(PAGE_W / 2, 110, "evergreenpuzzlepress.gumroad.com")
    c.linkURL(STORE, (PAGE_W / 2 - 140, 100, PAGE_W / 2 + 140, 124), relative=0)
    c.showPage()


def upsell_pages(c):
    # --- the money page: Complete Collection pitch ---
    c.setFillColorRGB(0.16, 0.32, 0.25)
    c.rect(0, PAGE_H - 170, PAGE_W, 170, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("SansB", 24)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 90, "ENJOYED THESE 10 PUZZLES?")
    c.setFillColorRGB(0.88, 0.64, 0.35)
    c.setFont("SansB", 14)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 125, "THERE ARE 329 MORE WAITING FOR YOU")

    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("SansB", 18)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 230, "THE COMPLETE COLLECTION — ALL 7 PACKS")
    c.setFont("Sans", 13)
    lines = ["329 large-print puzzles across every theme in this sampler.",
             "Instant download. Print forever. Full solutions for everything.",
             "", "Buy the packs one at a time for $4.99 each — or get", "everything at once and save 57%:"]
    y = PAGE_H - 265
    for ln in lines:
        c.drawCentredString(PAGE_W / 2, y, ln)
        y -= 20
    # big button
    bw, bh = 330, 54
    bx, by = (PAGE_W - bw) / 2, y - bh - 10
    c.setFillColorRGB(0.88, 0.64, 0.35)
    c.roundRect(bx, by, bw, bh, 12, stroke=0, fill=1)
    c.setFillColorRGB(0.13, 0.10, 0.03)
    c.setFont("SansB", 16)
    c.drawCentredString(PAGE_W / 2, by + bh / 2 - 6, "GET ALL 7 PACKS — $14.99")
    c.setFont("Sans", 10)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(PAGE_W / 2, by - 16, COLLECTION_URL.replace("https://", ""))
    c.linkURL(COLLECTION_URL, (bx, by - 22, bx + bw, by + bh), relative=0)

    # individual packs, clickable
    y = by - 70
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("SansB", 13)
    c.drawCentredString(PAGE_W / 2, y, "OR PICK A SINGLE PACK ($4.99 each) — tap a title:")
    y -= 26
    c.setFont("Sans", 11.5)
    for title, url in PACKS:
        c.setFillColorRGB(0.16, 0.32, 0.25)
        c.drawCentredString(PAGE_W / 2, y, title)
        c.linkURL(url, (PAGE_W / 2 - 200, y - 4, PAGE_W / 2 + 200, y + 12), relative=0)
        y -= 21
    c.showPage()

    # --- Amazon paperbacks page ---
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("SansB", 20)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 150, "PREFER A REAL BOOK IN YOUR HANDS?")
    c.setFont("Sans", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 185,
                        "Every pack is also a beautifully printed large-print paperback.")
    c.drawCentredString(PAGE_W / 2, PAGE_H - 205, 'Search "Evergreen Puzzle Press" on Amazon to see them all.')
    c.setFont("Sans", 12)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawCentredString(PAGE_W / 2, 150, "This sampler is yours to keep and share. Personal use only — do not resell.")
    c.drawCentredString(PAGE_W / 2, 130, f"Copyright © 2026 {AUTHOR}. All rights reserved.")
    c.showPage()


def build():
    random.seed(99)
    out_path = os.path.join(HERE, "out", "sampler", "sampler.pdf")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    ws.register_fonts()
    c = canvas.Canvas(out_path, pagesize=letter)
    c.setTitle("The Evergreen Puzzle Sampler — 10 Free Large Print Word Search Puzzles")
    c.setAuthor(AUTHOR)

    cover(c)

    solutions, page_no, idx = [], 1, 0
    for slug, count in PICKS:
        data = json.load(open(os.path.join(HERE, "..", "kdp", "themes", f"{slug}.json")))
        for p in data["puzzles"][:count]:
            idx += 1
            words = ws.clean_words(p["words"])
            grid, placements, placed = ws.generate_puzzle(words)
            ws.puzzle_page(c, idx, p["name"], grid, placed, page_no,
                           "The Evergreen Puzzle Sampler")
            solutions.append((idx, p["name"], grid, placements))
            page_no += 1

    ws.solutions_pages(c, solutions, page_no, "The Evergreen Puzzle Sampler")
    upsell_pages(c)
    c.save()
    print(f"SAMPLER -> {out_path}  ({idx} puzzles, {os.path.getsize(out_path)//1024} KB)")


if __name__ == "__main__":
    build()
