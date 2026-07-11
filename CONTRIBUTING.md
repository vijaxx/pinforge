# Contributing

## Setup

```
git clone https://github.com/vijaxx/pinforge.git
git clone https://github.com/vijaxx/kdp-puzzle-engine.git   # sibling dep, see README
cd pinforge
pip install -r requirements-dev.txt
```

`pack.py`, `pins.py`, and `sampler.py` import the word-search engine from `../kdp-puzzle-engine` (`wordsearch.py`), so that repo needs to be cloned as a sibling directory to actually generate anything. The test suite doesn't need it.

## Running tests

```
python -m pytest tests/ -v
```

CI runs this plus `python -m compileall -q .` on every push and PR.

## Making a change

1. Branch off `main`.
2. Keep the change scoped — this is a small collection of focused scripts, not a framework; a PR should generally touch one script's behavior, not several unrelated ones.
3. Add or update a test in `tests/` if you're changing logic that isn't purely about talking to a live browser session (those aren't practically testable in CI).
4. Open a PR against `main`. The template has a short checklist.

Posting/upload code (`post_pin.py`, `list_gumroad.py`) talks to a real logged-in Chrome session and can't be exercised in CI — changes there are reviewed by reading the diff carefully rather than by a green check mark.
