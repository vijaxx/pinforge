#!/usr/bin/env python3
"""
pincopy.py — pin titles + descriptions via local Ollama (qwen2.5:3b). $0, offline-safe.

Pinterest is a SEARCH engine: titles ≤100 chars front-load keywords, descriptions
≤450 chars read naturally and end with a soft CTA. If Ollama is down, deterministic
templates keep the factory running.

    /usr/bin/python3 pincopy.py --themes ../kdp/themes/animals.json --out out/animals/copy.json
"""
import argparse, json, re, urllib.request

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"


def ollama(prompt, timeout=180):
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.8}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["response"]


def extract_json(text):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def fallback(theme_title, n):
    short = theme_title.replace("Large Print ", "").replace(" Word Search", "")
    base = [
        {"title": f"{theme_title} Printable — {n} Large Print Puzzles PDF",
         "description": f"{n} relaxing {short.lower()} word search puzzles in big, easy-to-read print. "
                        "Instant download PDF — print at home as many times as you like. Full solutions "
                        "included. Perfect for seniors, road trips, and screen-free evenings. "
                        "Tap to download and print tonight."},
        {"title": f"Large Print {short} Word Search — Instant Download Puzzle Pack",
         "description": f"A calm evening activity: {n} {short.lower()} word searches with large print "
                        "that's kind to the eyes. Printable PDF, US Letter, answers at the back. "
                        "Great gift idea for grandparents and puzzle lovers. Save this pin for later!"},
        {"title": f"Screen-Free Activity for Seniors — {short} Word Search Printables",
         "description": f"Looking for an easy screen-free activity? This printable pack has {n} "
                        f"{short.lower()} puzzles in extra-large print, with full solutions. Download "
                        "once, print forever. Ideal for care homes, classrooms, and quiet Sunday "
                        "afternoons."},
        {"title": f"{short} Word Search PDF — Print at Home Puzzle Pack ({n} Puzzles)",
         "description": f"Instant-download {short.lower()} word search pack: {n} large-print puzzles "
                        "on US Letter pages, solutions included. No shipping, no waiting — print "
                        "tonight and start solving. A thoughtful, inexpensive gift for puzzle fans."},
        {"title": f"Brain Games for Adults — {n} Printable {short} Word Searches",
         "description": f"Keep your mind sharp the relaxing way. {n} {short.lower()}-themed word "
                        "search puzzles, generously sized print, full answer keys. Printable PDF "
                        "delivered instantly. Pin this for your next quiet evening."},
    ]
    return base


def generate(theme_title, n, want=5):
    try:
        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path.home() / ".project-agents"))
        import collective as _cm
        _cmb = "\n\n" + _cm.brief("pins")
    except Exception:
        _cmb = ""
    prompt = (
        f'You write Pinterest SEO copy for a printable puzzle shop. Product: "{theme_title}", '
        f"a printable PDF pack of {n} large-print word search puzzles with full solutions, "
        "printed at home by the buyer. Audience: gift shoppers, seniors, caregivers, teachers.\n"
        f"Write {want} DIFFERENT pin variants as a JSON array. Each object: "
        '"title" (max 95 chars, front-load search keywords like printable, large print, word search, PDF) '
        'and "description" (45-70 words, natural tone, include keywords organically, end with a soft '
        "call to action). No emojis, no hashtags, no markdown. Output ONLY the JSON array."
        + _cmb
    )
    try:
        items = extract_json(ollama(prompt))
        good = [i for i in (items or [])
                if isinstance(i, dict) and i.get("title") and i.get("description")
                and 35 <= len(i["title"]) <= 110
                and len(i["description"].split()) >= 40]
        if good:
            out = (good + [v for v in fallback(theme_title, n) if v not in good])[:want]
            return out, f"ollama({len(good)})+template"
    except Exception as e:
        print(f"  ollama unavailable ({e}); using template copy")
    return fallback(theme_title, n)[:want], "template"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--themes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=5)
    a = ap.parse_args()
    data = json.load(open(a.themes))
    variants, src = generate(data.get("title", "Word Search"), len(data["puzzles"]), a.count)
    import os
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump({"source": src, "variants": variants}, open(a.out, "w"), indent=2)
    print(f"COPY -> {a.out}  ({len(variants)} variants via {src})")


if __name__ == "__main__":
    main()
