#!/usr/bin/env python3
"""Post a single Pinterest pin via the attached PinForge Chrome (port 9224).

Reverse-engineered pin-builder (https://in.pinterest.com/pin-builder/):
  - file input  : input[type=file]                       (image upload)
  - title       : textarea[placeholder="Add your title"]
  - description : textarea[placeholder="Tell everyone what your Pin is about"]
  - link        : textarea[placeholder="Add a destination link"]
  - board       : selector button (default shows current board) -> flyout w/ filter
  - publish     : button "Publish"

Text is set via the React native value-setter (see _set_textarea) because direct
.value assignment is ignored by React's controlled inputs. The image is attached
via DOM.setFileInputFiles (real file input).

ORDER MATTERS: both the image upload and the board selection remount the draft
form (new field ids) and wipe any text already entered. So we upload -> wait for
the real blob: preview + settle -> select board -> THEN fill the fields with
verify-and-retry (_fill_verified). A publish gate refuses to publish if title or
link came back empty, so a UI change can never push a blank pin live again.

CLI:  post_pin.py <image> <title> <link> <board> [description]
"""
import sys, time, json, random
from cdp import Tab

PIN_BUILDER = "https://in.pinterest.com/pin-builder/"


def _hp(a=0.8, b=2.4):
    """Human pause — a short randomized think/type delay so field-fills aren't instant."""
    time.sleep(random.uniform(a, b))


def _root(t):
    return t.send("DOM.getDocument", depth=0)["root"]["nodeId"]


def _node(t, selector):
    nid = t.send("DOM.querySelector", nodeId=_root(t), selector=selector).get("nodeId")
    if not nid:
        raise RuntimeError(f"selector not found: {selector}")
    return nid


def _node_wait(t, selector, timeout=20, interval=0.5):
    """Like _node, but POLL until the selector exists (or timeout).

    navigate() only sleeps a fixed few seconds; on the first pin of a cold run
    the pin-builder hasn't rendered input[type=file] yet, so a one-shot _node()
    threw 'selector not found' and burned that pin — every cold batch lost its
    first slot. Polling makes the cold-start pin as reliable as a warm one."""
    deadline = time.time() + timeout
    while True:
        nid = t.send("DOM.querySelector", nodeId=_root(t), selector=selector).get("nodeId")
        if nid:
            return nid
        if time.time() >= deadline:
            raise RuntimeError(f"selector not found after {timeout}s: {selector}")
        time.sleep(interval)


def _click_xy(t, x, y):
    for ev in ("mousePressed", "mouseReleased"):
        t.send("Input.dispatchMouseEvent", type=ev, x=x, y=y, button="left", clickCount=1)
        time.sleep(0.05)


def _set_textarea(t, selector, text):
    """React-controlled gestalt textarea: set value via the prototype native setter
    and fire a bubbling 'input' so React's value tracker registers the change.
    (Confirmed working where .focus()/click/insertText do not.)"""
    res = t.eval(f"""(function(){{
        var el=document.querySelector({json.dumps(selector)});
        if(!el) return 'no-el';
        var set=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
        set.call(el, {json.dumps(text)});
        el.dispatchEvent(new Event('input',{{bubbles:true}}));
        el.dispatchEvent(new Event('change',{{bubbles:true}}));
        return el.value;
    }})()""")
    if res == "no-el":
        raise RuntimeError(f"selector not found: {selector}")
    time.sleep(0.2)
    return res


def _fill_verified(t, selector, text, tries=6, settle=0.8):
    """Fill a React textarea and VERIFY the value stuck, retrying if not.

    The pin-builder remounts the draft form (new field ids) shortly after the
    image upload completes, which silently wipes any value set into the previous
    instance — this was the blank-pin bug. Setting then reading back, and
    re-filling if the value is empty, makes the fill robust to that remount."""
    for i in range(tries):
        got = _set_textarea(t, selector, text)
        time.sleep(settle)
        back = t.eval(f"(document.querySelector({json.dumps(selector)})||{{}}).value")
        if (back or "").strip() == text.strip() and text.strip():
            return back
    return t.eval(f"(document.querySelector({json.dumps(selector)})||{{}}).value")


def _fill_description(t, text):
    """Fill the description — best-effort, never fatal. Pinterest renders this field
    as EITHER a plain textarea or a Draft.js contenteditable depending on form
    state, so try the textarea native-setter first, then fall back to a paste into
    the contenteditable. Title+link+image are the required fields; this is a bonus."""
    if not text:
        return ""
    ta = 'textarea[placeholder="Tell everyone what your Pin is about"]'
    if t.eval(f"!!document.querySelector({json.dumps(ta)})"):
        try:
            return _fill_verified(t, ta, text, tries=3)
        except Exception:
            pass
    ce = '[contenteditable="true"][aria-label*="Pin is about"]'
    if t.eval(f"!!document.querySelector({json.dumps(ce)})"):
        # focus + select all existing content so insertText REPLACES it, then type
        # via CDP (real key input, which Draft.js accepts where synthetic paste fails)
        t.eval(f"""(function(){{
            var d=document.querySelector({json.dumps(ce)}); if(!d) return false;
            d.focus();
            var r=document.createRange(); r.selectNodeContents(d);
            var s=window.getSelection(); s.removeAllRanges(); s.addRange(r);
            return true;
        }})()""")
        time.sleep(0.3)
        t.send("Input.insertText", text=text)
        time.sleep(0.5)
        return t.eval(f"(document.querySelector({json.dumps(ce)})||{{}}).textContent")
    return "no-desc-field"


def _set_draftjs(t, selector, text):
    """Best-effort fill of the Draft.js description via a synthetic paste event.
    Non-fatal: returns the resulting textContent (may be '') so the caller can
    decide. Title+link+image+board are the SEO-critical fields; description is
    a bonus we add when Draft.js cooperates."""
    return t.eval(f"""(function(){{
        var d=document.querySelector({json.dumps(selector)});
        if(!d) return 'no-el';
        try{{
          var range=document.createRange(); range.selectNodeContents(d); range.collapse(false);
          var sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
          var dt=new DataTransfer(); dt.setData('text/plain', {json.dumps(text)});
          d.dispatchEvent(new ClipboardEvent('paste', {{clipboardData:dt, bubbles:true, cancelable:true}}));
        }}catch(e){{ return 'err:'+e; }}
        return d.textContent;
    }})()"""    )


BOARD_SELECT_BTN = '[data-test-id="board-dropdown-select-button"]'


def _current_board(t):
    return (t.eval(f"(document.querySelector({json.dumps(BOARD_SELECT_BTN)})||{{}}).textContent") or "").strip()


def _select_board(t, board_name):
    """Pick the destination board WITHOUT destroying the draft.

    The old heuristic clicked arbitrary buttons near "Publish" to open a flyout,
    which remounted the form and wiped the uploaded image AND the text — that was
    the carousel/blank-pin failure. Pinterest defaults the dropdown to the
    last-used board, so if it already matches we touch nothing. Otherwise we open
    the real dropdown (board-dropdown-select-button), filter, and click the row."""
    cur = _current_board(t)
    if cur == board_name.strip():
        return "already-selected"
    opened = t.eval(f"""(function(){{
        var b=document.querySelector({json.dumps(BOARD_SELECT_BTN)});
        if(!b) return 'no-btn'; b.click(); return 'opened';
    }})()""")
    if opened != "opened":
        return opened
    time.sleep(1.5)  # extra wait for dropdown to fully render
    if t.eval("""(function(){var i=Array.from(document.querySelectorAll('input')).find(x=>/search|filter|board/i.test((x.getAttribute('aria-label')||'')+' '+(x.placeholder||''))); if(i){i.focus(); return true;} return false;})()"""):
        t.send("Input.insertText", text=board_name)
        time.sleep(1.5)  # wait for search results to load
    clicked = t.eval(f"""(function(){{
        var name={json.dumps(board_name)};
        var rows=Array.from(document.querySelectorAll('[role=option],[data-test-id*="board"] [role=button],[data-test-id*="board-row"],div'));
        var row=rows.find(r=>(r.textContent||'').trim()===name) || rows.find(r=>(r.textContent||'').trim().startsWith(name));
        if(!row) return 'no-row'; row.click(); return 'clicked';
    }})()""")
    time.sleep(1.0)
    result = "selected" if _current_board(t) == board_name.strip() else f"unconfirmed({clicked})"
    # 2026-07-01: if the dropdown is still open (no-row / unconfirmed), the Publish button
    # gets covered by the dropdown overlay → publish fails with 'no-publish'. Close the
    # dropdown first by pressing Escape, so the pin builder is visible again.
    if "unconfirmed" in result or clicked == "no-row":
        t.send("Input.dispatchKeyEvent", type="keyDown", key="Escape", windowsVirtualKeyCode=27)
        time.sleep(0.5)
        t.send("Input.dispatchKeyEvent", type="keyUp", key="Escape", windowsVirtualKeyCode=27)
        time.sleep(0.5)
    return result


def post(image, title, link, board, description, dry_run=False):
    t = Tab.attach("pinterest.com")
    t.send("Page.bringToFront")
    t.navigate(PIN_BUILDER, wait=4)
    t.send("Page.bringToFront")

    # 1) attach image to the real file input. Wait for it: on the first pin of a
    #    cold run the pin-builder hasn't rendered the input within navigate()'s
    #    fixed sleep, so a one-shot lookup threw 'selector not found' and burned
    #    the pin (this is the 'selector not found: input[type=file]' batch loss).
    fid = _node_wait(t, "input[type=file]", timeout=20)
    t.send("DOM.setFileInputFiles", files=[image], nodeId=fid)
    print(f"  image set: {image}")

    # 2) wait for the ACTUAL upload to render. The uploaded image shows as a
    #    blob: preview; we must NOT match pre-existing pinimg images (avatars,
    #    logos) — that false positive fired in ~1s and caused fields to be
    #    filled into the pre-remount form (then wiped). Require a blob: image,
    #    then let the draft form remount (new field ids) settle before filling.
    for _ in range(30):
        time.sleep(1)
        ready = t.eval("""(function(){
            return Array.from(document.querySelectorAll('img')).some(i=>/^blob:/.test(i.src||''));
        })()""")
        if ready:
            break
    time.sleep(2.5)
    print("  upload processed")

    # 3) select the board FIRST. Choosing/changing the board remounts the draft
    #    form (new field ids) and wipes any text already entered — this was the
    #    second half of the blank-pin bug. Doing it before the fill means the
    #    title/link land on the final, stable form.
    b = _select_board(t, board)
    print(f"  board '{board}': {b}")
    _hp(1.0, 2.5)

    # 4) fill fields (verified against the remount; description best-effort)
    # human-like pacing between fields — no instant robotic fill
    _hp(1.0, 3.0)
    tv = _fill_verified(t, 'textarea[placeholder="Add your title"]', title)
    _hp(1.5, 4.0)
    dv = _fill_description(t, description)
    _hp(1.2, 3.5)
    lv = _fill_verified(t, 'textarea[placeholder="Add a destination link"]', link)
    _hp(0.8, 2.0)
    print(f"  title={tv!r} link={lv!r} desc={dv!r}")

    # 5) verify what we're about to publish: fields + an actual image + that the
    #    draft is a normal (non-carousel) pin.
    state = t.eval("""JSON.stringify({
        title:(document.querySelector('textarea[placeholder="Add your title"]')||{}).value,
        link:(document.querySelector('textarea[placeholder="Add a destination link"]')||{}).value,
        desc:(document.querySelector('textarea[placeholder="Tell everyone what your Pin is about"]')||{}).value,
        images:Array.from(document.querySelectorAll('img')).filter(i=>/^blob:/.test(i.src||'')).length,
        carousel_err:(function(){var e=null;Array.from(document.querySelectorAll('div,span')).forEach(function(x){var tx=(x.textContent||'').trim();if(/Carousel Pin must have/.test(tx)&&tx.length<80&&!e)e=tx;});return e;})()
    })""")
    print(f"  STATE: {state}")
    try:
        st = json.loads(state)
    except Exception:
        st = {}
    title_ok = bool((st.get("title") or "").strip())
    link_ok = bool((st.get("link") or "").strip())
    image_ok = (st.get("images") or 0) >= 1
    no_carousel = not st.get("carousel_err")
    ready_ok = title_ok and link_ok and image_ok and no_carousel

    if dry_run:
        print("  DRY RUN — not publishing")
        return {"dry_run": True, "state": state, "ok": ready_ok}

    # PUBLISH GATE — only publish a normal pin with title, link, AND an image.
    # A blank / imageless / carousel-state draft either fails outright or has zero
    # SEO and no Gumroad traffic, so it's worse than not posting. run_batch only
    # records publish=='published', so aborting leaves the pin queued for next run.
    if not ready_ok:
        print(f"  ABORT: not publishing — title_ok={title_ok} link_ok={link_ok} "
              f"image_ok={image_ok} no_carousel={no_carousel}")
        return {"publish": "ABORTED_NOT_READY", "state": state, "ok": False,
                "title_ok": title_ok, "link_ok": link_ok,
                "image_ok": image_ok, "no_carousel": no_carousel}

    # 6) publish — click, then ACTUALLY VERIFY it succeeded. Do not trust the click:
    #    Pinterest can reject a publish (e.g. carousel/validation) while the button
    #    "click" itself succeeds. We poll for an explicit outcome.
    clicked = t.eval("""(function(){
        var b=Array.from(document.querySelectorAll('button,[role=button]')).find(x=>(x.textContent||'').trim()==='Publish' && x.offsetParent!==null);
        if(!b) return 'no-publish'; b.click(); return 'clicked';
    })()""")
    if clicked != "clicked":
        print(f"  publish: {clicked}")
        return {"publish": clicked, "ok": False, "state": state}

    # Outcome detection (validated against the live UI): a FAILED publish surfaces
    # an error/validation banner within a couple of seconds; a SUCCESSFUL publish
    # shows no banner (the builder does NOT reliably clear the draft, so "draft
    # cleared" is not a usable success signal). Therefore: error banner => FAILED;
    # no banner after the watch window => published. The strict pre-publish gate
    # (title+link+image+non-carousel) already blocks the known failure mode, so a
    # clean click with no error is a real publish.
    verdict, detail = "published", "no error banner after publish"
    for _ in range(10):
        time.sleep(1)
        err = t.eval("""(function(){var e=null;Array.from(document.querySelectorAll('div,span')).forEach(function(x){var tx=(x.textContent||'').trim();if(/(Carousel Pin must have|went wrong|couldn.t be|failed to|please try again)/i.test(tx)&&tx.length<120&&!e)e=tx;});return e;})()""")
        if err:
            verdict, detail = "FAILED", err
            break
    print(f"  publish verdict: {verdict} ({detail})")
    return {"publish": verdict, "ok": verdict == "published", "detail": detail, "state": state}


if __name__ == "__main__":
    a = sys.argv
    dry = "--dry" in a
    a = [x for x in a if x != "--dry"]
    image, title, link, board = a[1], a[2], a[3], a[4]
    desc = a[5] if len(a) > 5 else ""
    print(json.dumps(post(image, title, link, board, desc, dry_run=dry), indent=2, default=str))
