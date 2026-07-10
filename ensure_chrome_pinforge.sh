#!/bin/zsh
# Idempotent: ensure the PinForge Chrome instance is running with
# --remote-debugging-port=9224. If already running, leave it; just make sure
# a Pinterest + a Gumroad tab exist. If not running, launch it.
#
# DEDICATED PORT 9224 (PinForge). 9222 = KDP (/tmp/kdpdbg), 9223 = RedditReels
# (FrameWiseChrome). PinForge owns 9224 with its own PinForgeChrome profile so
# Pinterest/Gumroad cookies persist and never collide with the other engines.
#
# Log in ONCE in this browser (Pinterest + Gumroad) — cookies persist in the
# profile dir across runs, exactly like the RedditReels setup.

PROFILE_DIR="$HOME/Library/Application Support/PinForgeChrome"
PORT=9224
# Aarav (auth agent): verify/recover the Pinterest login on every exit path. Non-fatal.
trap 'python3 "$HOME/.authagent/authd.py" ensure pinterest >/dev/null 2>&1 || true' EXIT
PINTEREST_URL="https://www.pinterest.com/pin-builder/"
GUMROAD_URL="https://app.gumroad.com/products"
LOGDIR="$HOME/clauwork/pinforge"

if curl -s --max-time 2 "http://127.0.0.1:${PORT}/json/version" > /dev/null 2>&1; then
    TABS_JSON=$(curl -s "http://127.0.0.1:${PORT}/json" 2>/dev/null)
    if ! echo "$TABS_JSON" | grep -q "pinterest.com"; then
        curl -s -X PUT "http://127.0.0.1:${PORT}/json/new?${PINTEREST_URL}" > /dev/null 2>&1
    fi
    if ! echo "$TABS_JSON" | grep -q "gumroad.com"; then
        curl -s -X PUT "http://127.0.0.1:${PORT}/json/new?${GUMROAD_URL}" > /dev/null 2>&1
    fi
    echo "Chrome already running on port ${PORT} (Pinterest + Gumroad tabs ensured)"
    exit 0
fi

mkdir -p "$PROFILE_DIR"

echo "Launching PinForge Chrome on port ${PORT}..."
nohup "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --user-data-dir="$PROFILE_DIR" \
    --remote-debugging-port=$PORT \
    "--remote-allow-origins=*" \
    --no-first-run \
    --no-default-browser-check \
    --window-size=1340,950 \
    "$PINTEREST_URL" \
    "$GUMROAD_URL" \
    > "$LOGDIR/chrome.log" 2>&1 &

for i in $(seq 1 15); do
    sleep 1
    if curl -s --max-time 1 "http://127.0.0.1:${PORT}/json/version" > /dev/null 2>&1; then
        echo "Chrome ready on port ${PORT} after ${i}s"
        sleep 3
        exit 0
    fi
done

echo "ERROR: Chrome failed to start on port ${PORT} within 15s"
exit 1
