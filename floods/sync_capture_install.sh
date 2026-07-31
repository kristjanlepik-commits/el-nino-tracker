#!/bin/bash
# Refresh the pinned capture install from the repo.
#
# The unattended job runs from ~/tls-floods-capture/bin, not from the
# working tree, for two reasons found on 2026-07-29:
#
#   1. ~/Documents is TCC-protected. A launch agent cannot read a script
#      there without Full Disk Access, which is far too broad a grant
#      for this. The first plist failed with exit 126, "Operation not
#      permitted", having never once run.
#   2. Four chats edit this tree continuously. An unattended job should
#      not execute whatever happens to be on disk mid-edit, which is the
#      same reasoning as platform's dirty-generator guard.
#
# Run this after changing capture_viirs_global.py or the wrapper.
# Deliberate rather than automatic: the point is that the running copy
# only changes when someone decides it should.

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$HOME/tls-floods-capture/bin"
mkdir -p "$BIN"

cp "$REPO/floods/capture_viirs_global.py" "$BIN/"

# Rewrite the wrapper's paths to the pinned location.
sed -e "s#^REPO=.*#REPO=\"$BIN\"#" \
    -e "s#\$REPO/floods/capture_viirs_global.py#\$REPO/capture_viirs_global.py#" \
    -e "s#^PY=.*#PY=\"$BIN/venv/bin/python\"#" \
    "$REPO/floods/run_daily_capture.sh" > "$BIN/run_daily_capture.sh"
chmod +x "$BIN/run_daily_capture.sh"

if [ ! -x "$BIN/venv/bin/python" ]; then
  echo "creating venv (numpy, netCDF4)"
  /usr/bin/python3 -m venv "$BIN/venv"
  "$BIN/venv/bin/pip" install -q --disable-pip-version-check numpy netCDF4
fi

"$BIN/venv/bin/python" -c "import numpy, netCDF4" || { echo "venv broken"; exit 1; }
bash -n "$BIN/run_daily_capture.sh"
echo "synced to $BIN"
grep -E '^REPO=|^PY=' "$BIN/run_daily_capture.sh"
