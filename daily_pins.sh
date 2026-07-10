#!/bin/zsh
# PinForge daily pin poster — launchd entrypoint.
# 1) ensure the dedicated PinForge Chrome (port 9224) is up & logged in
# 2) post the daily batch (run_batch.py enforces the <=3/day cadence + sampler weighting)
#
# Requires the PinForgeChrome profile to stay logged into Pinterest (cookies persist).
# Runs locally only (CDP drives the local browser) — cannot run in the cloud.

# Lives OFF the Desktop: ~/Desktop is TCC-protected, so launchd cannot read
# scripts/data there without Full Disk Access (it silently fails with exit 127,
# "can't open input file"). ~/clauwork is unprotected — same as ~/RedditReels.
DIR="$HOME/clauwork/pinforge"
LOG="$DIR/daily_pins.log"
PY=/usr/bin/python3

echo "===== $(date '+%Y-%m-%d %H:%M:%S') daily_pins start =====" >> "$LOG"

# Randomized start delay (0–40 min) so pins don't post at the same clock time
# every day. A fixed daily timestamp is an obvious scheduled-bot signal.
JITTER=$(( RANDOM % 2400 ))
echo "jitter: sleeping ${JITTER}s before posting" >> "$LOG"
sleep "$JITTER"

"$DIR/ensure_chrome_pinforge.sh" >> "$LOG" 2>&1
sleep 5
cd "$DIR" && "$PY" run_batch.py >> "$LOG" 2>&1
echo "===== $(date '+%Y-%m-%d %H:%M:%S') daily_pins done =====" >> "$LOG"
