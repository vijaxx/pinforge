#!/usr/bin/env python3
"""Daily pin-posting run: builds a queue from every manifest, posts a few,
marks them done so nothing repeats. Caps posts per day and leans on the free
sampler early on new accounts -- Pinterest is not kind to bursty posting on a
young profile."""
import json, sys, time, datetime, glob, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
from post_pin import post  # noqa: E402

STATE = os.path.join(HERE, "post_state.json")
LOG = os.path.join(HERE, "post_log.jsonl")
ACCOUNT_CREATED = datetime.date(2026, 6, 10)
DAILY_CAP = 3

# theme -> Pinterest board (falls back to the general board).
# 2026-07-01: audited actual boards on evergreenpuzzlepress account — only 5 exist:
#   Large Print Word Search | Kids Activities | Christmas Printables |
#   Activities for Seniors  | Printable Puzzles for Seniors
# All other board names in the old dict were non-existent → caused dropdown 'no-row'
# → dropdown stayed open → Publish button was hidden → 'no-publish' failure.
# Fixed: only use board names that actually exist.
BOARD = {
    "kids":                            "Kids Activities",
    "christmas":                       "Christmas Printables",
    # All large-print/senior-friendly themes go to the senior boards
    "nature":                          "Printable Puzzles for Seniors",
    "animals":                         "Printable Puzzles for Seniors",
    "animals-and-wildlife-conservation": "Activities for Seniors",
    "birds":                           "Printable Puzzles for Seniors",
    "ocean-life":                      "Printable Puzzles for Seniors",
    "outdoor-activities":              "Activities for Seniors",
    "endangered-species-and-wildlife": "Activities for Seniors",
    "gardening":                       "Activities for Seniors",
    "sports":                          "Activities for Seniors",
    "food":                            "Printable Puzzles for Seniors",
    "travel":                          "Printable Puzzles for Seniors",
    "beach-vacation":                  "Printable Puzzles for Seniors",
    "summer-vacation":                 "Activities for Seniors",
    "retro-travel-and-landmarks":      "Printable Puzzles for Seniors",
    # Everything else → default
}
DEFAULT_BOARD = "Large Print Word Search"


def _today():
    return datetime.date.today().isoformat()


def load_state():
    if os.path.exists(STATE):
        s = json.load(open(STATE))
    else:
        s = {"date": _today(), "posted_today": 0, "total_posted": 0}
    if s.get("date") != _today():
        s = {"date": _today(), "posted_today": 0, "total_posted": s.get("total_posted", 0)}
    return s


def save_state(s):
    json.dump(s, open(STATE, "w"), indent=2)


def manifest_path(theme):
    return os.path.join(HERE, "out", theme, "manifest.json")


def build_queue():
    """Return dict of theme -> list of unposted pin records (with resolved fields)."""
    q = {}
    for mf in sorted(glob.glob(os.path.join(HERE, "out", "*", "manifest.json"))):
        theme = os.path.basename(os.path.dirname(mf))
        d = json.load(open(mf))
        prod = d.get("product", {})
        # 2026-06-30 FIX: list_gumroad.py records the live link as `gumroad_url`, but this
        # only read `url` — so every pack listed that way (the 3 newest) was silently skipped
        # and its pins never posted. Accept either key.
        url = prod.get("url") or prod.get("gumroad_url")
        if prod.get("gumroad_status") == "NOT_LISTED" or not url:
            # Surface the silent leak: a pack marked LISTED but missing its URL gets skipped
            # here (no link to drive traffic to) — back-fill gumroad_url from the Gumroad
            # dashboard so its pins post. Silent before 2026-07-07 (bible/food/gardening).
            if prod.get("gumroad_status") == "LISTED" and not url:
                print(f"WARN: {theme} is LISTED but has no gumroad_url — pins skipped until back-filled",
                      file=sys.stderr)
            continue  # don't drive traffic to a product that isn't live
        pins = []
        for i, p in enumerate(d.get("pins", [])):
            if p.get("posted"):
                continue
            img = os.path.join(HERE, p["image"])
            if not os.path.exists(img):
                continue
            pins.append({
                "theme": theme, "idx": i, "image": img,
                "title": p["title"].replace("\n", " ").strip(),
                "description": (p.get("description") or "").replace("\n", " ").strip(),
                "link": p.get("link") or url,
                "board": BOARD.get(theme, DEFAULT_BOARD),
            })
        if pins:
            q[theme] = pins
    return q


def pick_batch(q, n, total_posted):
    """Sampler-first, then rotate paid themes, ~1 in 4 = collection."""
    in_first_14 = (datetime.date.today() - ACCOUNT_CREATED).days < 14
    batch = []
    # 1) lead with a sampler pin while aging the account
    if in_first_14 and q.get("sampler"):
        batch.append(q["sampler"][0])
    # 2) fill the rest from paid themes, rotating, sprinkling the collection
    paid_themes = [t for t in q if t not in ("sampler", "collection")]
    paid_themes.sort(key=lambda t: q[t][0]["idx"])  # least-posted first
    ti = 0
    counter = total_posted + len(batch)
    used = {p["theme"] for p in batch}
    while len(batch) < n and (paid_themes or q.get("collection")):
        # every 4th post -> collection, if available
        if counter % 4 == 3 and q.get("collection") and "collection" not in used:
            batch.append(q["collection"][0]); used.add("collection"); counter += 1; continue
        if not paid_themes:
            if q.get("collection") and "collection" not in used:
                batch.append(q["collection"][0]); used.add("collection")
            break
        theme = paid_themes[ti % len(paid_themes)]
        # take the lowest unposted idx for this theme not already queued
        avail = [p for p in q[theme] if p not in batch]
        if avail:
            batch.append(avail[0]); counter += 1
        ti += 1
        if ti > len(paid_themes) * 3:
            break
    return batch[:n]


def mark_posted(rec, result):
    mf = manifest_path(rec["theme"])
    d = json.load(open(mf))
    p = d["pins"][rec["idx"]]
    p["posted"] = True
    p["posted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    json.dump(d, open(mf, "w"), indent=2, ensure_ascii=False)
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": p["posted_at"], "theme": rec["theme"], "idx": rec["idx"],
                            "title": rec["title"], "link": rec["link"], "board": rec["board"],
                            "publish": (result or {}).get("publish")}) + "\n")


def main():
    args = sys.argv[1:]
    dry = "--dry" in args

    # Human-like daily target: NOT always the cap. Real users vary how much they
    # post and skip some days entirely. This irregularity is the single biggest
    # signal that an account is human, not a scheduled bot.
    if "--n" in args:
        n = int(args[args.index("--n") + 1])
    elif random.random() < 0.15:
        print("Randomized natural day off — posting nothing today (looks human).")
        return
    else:
        n = random.choices([1, 2, 3], weights=[0.30, 0.45, 0.25])[0]

    s = load_state()
    remaining_today = max(0, DAILY_CAP - s["posted_today"])
    n = min(n, remaining_today)
    if n <= 0:
        print(f"Daily cap reached ({s['posted_today']}/{DAILY_CAP} for {s['date']}). Nothing to do.")
        return

    q = build_queue()
    total_unposted = sum(len(v) for v in q.values())
    batch = pick_batch(q, n, s["total_posted"])
    print(f"Queue: {total_unposted} unposted pins across {len(q)} themes. "
          f"Posting {len(batch)} (cap {DAILY_CAP}/day, {s['posted_today']} already today).")
    for r in batch:
        print(f"  - {r['theme']}#{r['idx']} -> board '{r['board']}' :: {r['title'][:60]}")

    if dry:
        print("DRY RUN — nothing posted.")
        return

    for i, r in enumerate(batch):
        print(f"\n>>> posting {r['theme']}#{r['idx']}")
        try:
            res = post(r["image"], r["title"], r["link"], r["board"], r["description"])
            if (res or {}).get("publish") == "published":
                mark_posted(r, res)
                s["posted_today"] += 1
                s["total_posted"] += 1
                save_state(s)
                print(f"    OK ({s['posted_today']}/{DAILY_CAP} today, {s['total_posted']} total)")
            else:
                print(f"    NOT published: {res}")
        except Exception as e:
            print(f"    ERROR: {e}")
        # Human spacing between pins: minutes, not seconds. Nobody creates several
        # pins 8s apart — that velocity is a classic bot tell. Skip after the last.
        if i < len(batch) - 1:
            gap = random.randint(120, 420)  # 2–7 minutes
            print(f"    (waiting ~{gap // 60}m {gap % 60}s before next pin)")
            time.sleep(gap)

    print(f"\nDone. {s['posted_today']}/{DAILY_CAP} posted today, {s['total_posted']} total.")


if __name__ == "__main__":
    main()
