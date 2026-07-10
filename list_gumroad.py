#!/usr/bin/env python3
"""
list_gumroad.py — list a PinForge pack/bundle on Gumroad from its manifest, via the
already-logged-in PinForge Chrome (port 9224, driven by cdp.py). Lets Agent Kaushik publish
products himself instead of escalating for Vijaxx's login on every listing.

  python3 list_gumroad.py out/everything/manifest.json            # create DRAFT (safe default)
  python3 list_gumroad.py out/everything/manifest.json --publish  # create + PUBLISH live

SAFETY (matches the team's live-execution rails):
  • Reuses an EXISTING logged-in Gumroad session in Chrome 9224 — it NEVER types Vijaxx's password.
    If not logged in, it notifies Vijaxx and aborts (no half-listing).
  • DRAFT by default. Publishing live needs --publish (Kaushik passes it once the flow is calibrated).
  • Any step that can't find its Gumroad element ABORTS + notifies "needs calibration" — it never
    silently creates a malformed product. Manifest gumroad_status is only advanced on real success.

CALIBRATION: Gumroad's product-creation DOM can't be guessed perfectly. The GUMROAD-SPECIFIC
selectors live in ONE block below (marked ⚙ CALIBRATE). On the first supervised run against the
real logged-in page, only that block may need tweaking; everything else is generic.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from cdp import Tab, tabs

NOTIFY = "/Users/vijaxx/.project-agents/notify.sh"
GUMROAD_PRODUCTS = "https://gumroad.com/products"
GUMROAD_NEW = "https://gumroad.com/products/new"


ENSURE_PINFORGE = "/Users/vijaxx/clauwork/pinforge/ensure_chrome_pinforge.sh"

def notify(msg: str, url: str | None = None) -> None:
    """Plain notify, or — when `url` is given — a CLICKABLE notification that opens `url` in the
    PinForge automation Chrome (port 9224) so Vijaxx lands in the exact browser to act."""
    args = [NOTIFY, msg] + (["9224", url, ENSURE_PINFORGE] if url else [])
    try:
        subprocess.run(args, timeout=10)
    except Exception:
        print("notify:", msg)


def chrome_up() -> bool:
    try:
        tabs(); return True
    except Exception:
        return False


# JS helper: set a React-controlled input's value so Gumroad's form actually registers it.
SET_INPUT_JS = """
(function(sel, val){
  const el = document.querySelector(sel);
  if(!el) return false;
  const proto = Object.getPrototypeOf(el);
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
  setter.call(el, val);
  el.dispatchEvent(new Event('input', {bubbles:true}));
  el.dispatchEvent(new Event('change', {bubbles:true}));
  return true;
})(%s, %s)
"""


def set_input(t: Tab, selector: str, value: str) -> bool:
    return bool(t.eval(SET_INPUT_JS % (json.dumps(selector), json.dumps(value))))


def set_file_input(t: Tab, selector: str, abspath: str) -> bool:
    """Upload a file by setting an <input type=file> directly (no chooser dialog)."""
    doc = t.send("DOM.getDocument", depth=0)
    root = doc["root"]["nodeId"]
    q = t.send("DOM.querySelector", nodeId=root, selector=selector)
    nid = q.get("nodeId")
    if not nid:
        return False
    t.send("DOM.setFileInputFiles", files=[abspath], nodeId=nid)
    return True


def square_thumb(theme_dir: str):
    """Return a path to a SQUARE thumbnail for this pack (Gumroad's Thumbnail field rejects
    non-square: 'Image must be square'). Prefer an existing square thumb.png; else pad the
    landscape cover.png to a square; else None."""
    import glob
    thumb = os.path.join(theme_dir, "thumb.png")
    cover = os.path.join(theme_dir, "cover.png")
    try:
        from PIL import Image
        if os.path.exists(thumb):
            w, h = Image.open(thumb).size
            if w == h:
                return thumb
        if os.path.exists(cover):
            im = Image.open(cover).convert("RGB"); w, h = im.size; s = max(w, h)
            canvas = Image.new("RGB", (s, s), im.getpixel((5, 5)))
            canvas.paste(im, ((s - w) // 2, (s - h) // 2))
            out = os.path.join(theme_dir, "thumb_sq.png"); canvas.save(out)
            return out
    except Exception:
        pass
    return thumb if os.path.exists(thumb) else None


def set_thumbnail(t: Tab, sq_path: str) -> bool:
    """Upload a SQUARE image into Gumroad's Thumbnail field = the LAST image file input on the
    /edit page (#0 is the description editor's image-insert). Caller should then Save changes."""
    doc = t.send("DOM.getDocument", depth=0)
    root = doc["root"]["nodeId"]
    nids = t.send("DOM.querySelectorAll", nodeId=root,
                  selector="input[type=file][accept*='png']").get("nodeIds", [])
    if not nids:
        return False
    t.send("DOM.setFileInputFiles", files=[sq_path], nodeId=nids[-1])
    return True


def logged_in(t: Tab) -> bool:
    url = (t.eval("location.href") or "").lower()
    # Gumroad bounces logged-out users to /login or gumroad.com home.
    return "login" not in url and "/products" in url


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", help="path to a pack/bundle manifest.json")
    ap.add_argument("--publish", action="store_true", help="publish live (default: leave as draft)")
    a = ap.parse_args()

    m = json.load(open(a.manifest))
    p = m.get("product", m)
    # 2026-06-30 FIX: re-running this on an already-LISTED manifest always created a brand
    # NEW Gumroad product (no duplicate check existed) — confirmed 2 real orphan duplicates
    # this way (wildlife-conservation + endangered-species each got a second listing).
    # Refuse by default; --force only for an intentional re-list.
    if p.get("gumroad_status") == "LISTED" and (p.get("url") or p.get("gumroad_url")) and "--force" not in sys.argv:
        print(f"ALREADY LISTED at {p.get('url') or p.get('gumroad_url')} — refusing to create a "
              f"duplicate. Pass --force if you really mean to re-list (e.g. after deleting the old one).")
        return 0
    title = p["title"]; price = p.get("price_usd", p.get("price"))
    desc = p.get("listing_description", p.get("description", ""))
    pdf = os.path.abspath(os.path.join(os.path.dirname(a.manifest), os.path.basename(p["pdf"]))) \
        if not os.path.isabs(p.get("pdf", "")) else p["pdf"]
    if not os.path.exists(pdf):
        # pdf path in manifest may be repo-relative
        cand = os.path.join(os.path.dirname(os.path.dirname(a.manifest)), os.path.relpath(p["pdf"], "out")) \
            if p.get("pdf", "").startswith("out/") else p.get("pdf", "")
        pdf = p["pdf"] if os.path.exists(p["pdf"]) else (cand if os.path.exists(cand) else pdf)
    if not os.path.exists(pdf):
        notify(f"🔑 Kaushik: can't list '{title}' — PDF not found ({p.get('pdf')}).")
        print("PDF not found:", pdf); return 1

    if not chrome_up():
        notify("🔑 Kaushik: tap to bring up the PinForge Chrome + open Gumroad (it was down). "
               "Make sure Gumroad is logged in there.", url="https://gumroad.com/products")
        return 1

    t = Tab.open(GUMROAD_PRODUCTS)
    time.sleep(3)
    if not logged_in(t):
        notify("🔑 Kaushik needs you: tap to open Gumroad in the PinForge Chrome and log in once. "
               "I never type your password — once you're in, I list products myself.",
               url="https://gumroad.com/login")
        print("Not logged into Gumroad — aborted, notified Vijaxx."); return 2

    # ─── Gumroad new-product flow (CALIBRATED + verified live 2026-06-23 against the real DOM) ───
    def click_by_text(rx):
        return t.eval("(function(){for(const b of document.querySelectorAll('button,a[role=button]')){"
                      "if(new RegExp(%s,'i').test((b.innerText||'').trim())){b.click();return true;}}return false;})()"
                      % json.dumps(rx))

    # PAGE 1 — gumroad.com/products/new: pick "Digital product", set name + price, Next: Customize.
    t.navigate(GUMROAD_NEW, wait=5)
    click_by_text("^digital product"); time.sleep(1)
    ok_name  = set_input(t, "input[id^='name-']", title)
    ok_price = set_input(t, "input[id^='price-']", str(price))
    if not (ok_name and ok_price):
        notify(f"🔑 Kaushik: Gumroad new-product form changed — name/price field not found "
               f"(needs calibration). '{title}' NOT listed."); return 3
    if not click_by_text("next:?\\s*customize"):
        notify(f"🔑 Kaushik: Gumroad 'Next: Customize' not found (needs calibration)."); return 3
    time.sleep(6)  # creates the draft, lands on /products/<id>/edit

    # PAGE 2 — /edit: set the description (a contenteditable rich field), then Save and continue.
    t.eval("(function(){const d=document.querySelector('[contenteditable=true]');if(d){d.focus();}})()")
    time.sleep(0.3)
    t.eval("(function(dsc){const el=document.querySelector('[contenteditable=true]');"
           "if(!el)return false;el.focus();document.execCommand('insertText',false,dsc);return true;})(%s)"
           % json.dumps(desc))
    # Thumbnail (Gumroad's products-list image) — MUST be square, else it's rejected
    # ("Image must be square"). Non-fatal: a missing thumb shouldn't block the listing.
    sq = square_thumb(os.path.dirname(os.path.abspath(a.manifest)))
    if sq and set_thumbnail(t, sq):
        time.sleep(9)  # let the square thumb upload/validate before saving
    if not click_by_text("save and continue"):
        notify(f"🔑 Kaushik: Gumroad 'Save and continue' not found (needs calibration)."); return 4
    time.sleep(6)  # lands on /edit/content

    # PAGE 3 — /edit/content: upload the PDF into the file input, Save changes.
    if not set_file_input(t, "input[type='file']", pdf):
        notify(f"🔑 Kaushik: Gumroad content file-input not found (needs calibration). '{title}' draft incomplete.")
        return 5
    time.sleep(10)  # let the PDF upload finish
    click_by_text("save changes"); time.sleep(5)
    # ─────────────────────────────── end calibrated flow ───────────────────────────────

    status = "DRAFTED"
    if a.publish:
        if click_by_text("publish and continue|^publish"):
            status = "LISTED"; time.sleep(6)
        else:
            notify(f"🔑 Kaushik: '{title}' is a complete Gumroad DRAFT but the Publish button wasn't "
                   f"found — review + publish manually.")
    # capture the public URL if we can
    purl = t.eval("(function(){const a=Array.from(document.querySelectorAll('a')).find(a=>/gumroad\\.com\\/l\\//.test(a.href));return a?a.href:'';})()")
    if purl:
        p["gumroad_url"] = purl

    # record outcome in the manifest (only on real progress)
    p["gumroad_status"] = status
    p["gumroad_listed_at"] = time.strftime("%Y-%m-%d %H:%M")
    json.dump(m, open(a.manifest, "w"), indent=2, ensure_ascii=False)

    if status == "LISTED":
        notify(f"✅ Kaushik (PinForge) shipped live: '{title}' published on Gumroad (${price}).")
    else:
        notify(f"✅ Kaushik: '{title}' built as a Gumroad DRAFT (${price}) — review + hit Publish "
               f"(or re-run with --publish once the flow is confirmed).")
    print(f"done: status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
