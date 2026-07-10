#!/usr/bin/env python3
"""
pack.py — print-at-home puzzle pack (DIGITAL edition) for Gumroad.

Reuses the KDP word-search engine (../kdp/wordsearch.py) but produces a digital
product: personal-use license page, print-at-home framing, and a back page that
cross-sells the Amazon paperback line — every download markets the KDP books.

RUN WITH /usr/bin/python3 (it has reportlab + PIL):

    /usr/bin/python3 pack.py --themes ../kdp/themes/animals.json --out out/animals/pack.pdf
"""
import argparse, json, os, random, sys

KDP_DIR = os.environ.get("KDP_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kdp")
if not os.path.isdir(KDP_DIR):  # live dir moved; fall back to the canonical KDP engine location
    KDP_DIR = os.path.expanduser("~/Desktop/clauwork/kdp")
sys.path.insert(0, KDP_DIR)
import wordsearch as ws  # noqa: E402  (the KDP engine — puzzles, grids, solutions)

from reportlab.pdfgen import canvas  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402

PAGE_W, PAGE_H = letter
MARGIN = 54
GUMROAD_NOTE = "evergreenpuzzlepress.gumroad.com"


def digital_cover(c, title, subtitle, author, n_puzzles):
    c.setFillColorRGB(0.96, 0.95, 0.91)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    c.setFillColorRGB(0.16, 0.32, 0.25)
    c.rect(0, PAGE_H - 200, PAGE_W, 200, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("SansB", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 60, "PRINTABLE PUZZLE PACK")
    c.setFont("SansB", 28)
    for i, line in enumerate(ws._wrap(title.upper(), 24)):
        c.drawCentredString(PAGE_W / 2, PAGE_H - 110 - i * 34, line)
    c.setFillColorRGB(0.16, 0.32, 0.25)
    c.setFont("SansB", 16)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 280, f"{n_puzzles} LARGE-PRINT PUZZLES")
    c.setFont("Sans", 13)
    for i, line in enumerate(ws._wrap(subtitle, 56)):
        c.drawCentredString(PAGE_W / 2, PAGE_H - 320 - i * 20, line)
    c.setFont("Sans", 12)
    perks = [
        "Print at home on US Letter paper",
        "Big, easy-to-read letters — kind to the eyes",
        "Full solutions included at the back",
        "Print as many copies as you like, forever",
    ]
    y = PAGE_H - 430
    for p in perks:
        c.setFillColorRGB(0.16, 0.32, 0.25)
        c.circle(PAGE_W / 2 - 150, y + 4, 3, stroke=0, fill=1)
        c.setFillColorRGB(0.15, 0.15, 0.15)
        c.drawString(PAGE_W / 2 - 138, y, p)
        y -= 26
    c.setFont("SansB", 13)
    c.drawCentredString(PAGE_W / 2, 140, author)
    c.setFont("Sans", 10)
    c.setFillColorRGB(0.45, 0.45, 0.45)
    c.drawCentredString(PAGE_W / 2, 120, GUMROAD_NOTE)
    c.showPage()


def license_page(c, author):
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("SansB", 20)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 140, "YOUR LICENSE (THE SHORT VERSION)")
    c.setFont("Sans", 12)
    lines = [
        "This pack is for PERSONAL USE.",
        "",
        "You may: print unlimited copies for yourself, your family,",
        "your classroom, or your care-home activity group.",
        "",
        "You may not: resell, redistribute, or upload this file anywhere.",
        "",
        f"Copyright © 2026 {author}. All rights reserved.",
        "",
        "Tip: print at 100% scale ('Actual Size') on US Letter paper.",
        "Grayscale is fine — the puzzles are pure black and white.",
    ]
    for i, ln in enumerate(lines):
        c.drawCentredString(PAGE_W / 2, PAGE_H - 190 - i * 20, ln)
    c.showPage()


def cross_sell_page(c, author, also_from):
    """The flywheel page: every digital download advertises the paperback line."""
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("SansB", 24)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 160, "PREFER A REAL BOOK?")
    c.setFont("Sans", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 195,
                        f"Every pack from {author} is also a beautiful large-print paperback.")
    c.drawCentredString(PAGE_W / 2, PAGE_H - 213,
                        "Search these titles on Amazon:")
    y = PAGE_H - 270
    for entry in also_from:
        c.setFont("SansB", 14)
        c.drawCentredString(PAGE_W / 2, y, entry.get("title", ""))
        sub = entry.get("subtitle", "")
        if sub:
            c.setFont("Sans", 11)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawCentredString(PAGE_W / 2, y - 17, sub)
            c.setFillColorRGB(0.1, 0.1, 0.1)
        y -= 60
    c.setFont("Sans", 12)
    c.drawCentredString(PAGE_W / 2, 150, "More printable packs:")
    c.setFont("SansB", 12)
    c.drawCentredString(PAGE_W / 2, 132, GUMROAD_NOTE)
    c.showPage()


def build(themes_path, out_path, seed=11):
    random.seed(seed)
    data = json.load(open(themes_path))
    title = data.get("title", "Word Search") + " — Printable Pack"
    subtitle = data.get("subtitle", "")
    author = data.get("author", "Evergreen Puzzle Press")
    n_puzzles = len(data["puzzles"])

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    ws.register_fonts()
    c = canvas.Canvas(out_path, pagesize=letter)
    c.setTitle(title)
    c.setAuthor(author)

    digital_cover(c, data.get("title", "Word Search"), subtitle, author, n_puzzles)
    license_page(c, author)

    solutions, page_no = [], 1
    for i, p in enumerate(data["puzzles"], start=1):
        words = ws.clean_words(p["words"])
        grid, placements, placed = ws.generate_puzzle(words)
        ws.puzzle_page(c, i, p["name"], grid, placed, page_no, title)
        solutions.append((i, p["name"], grid, placements))
        page_no += 1

    ws.solutions_pages(c, solutions, page_no, title)
    cross_sell_page(c, author, data.get("also_from", []))
    c.save()

    size_kb = os.path.getsize(out_path) / 1024
    print(f"PACK -> {out_path}  ({n_puzzles} puzzles, {size_kb:.0f} KB)")
    return {"title": title, "author": author, "puzzles": n_puzzles, "pdf": out_path}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--themes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    build(a.themes, a.out, a.seed)


if __name__ == "__main__":
    main()
