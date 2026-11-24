#!/usr/bin/env bash
# Start the Historical Shadow Replay Harness locally. No API key required.
set -euo pipefail
cd "$(dirname "$0")"
STREAMLIT_PORT="${SHADOW_REPLAY_UI_PORT:-8510}"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
# Ensure the seeded ticket file exists before the UI loads.
.venv/bin/python -m replay generate >/dev/null
echo "Shadow Replay UI: http://127.0.0.1:${STREAMLIT_PORT}"
echo "CLI:              .venv/bin/python -m replay run --agent v2"
exec .venv/bin/streamlit run app.py --server.headless true --server.port "$STREAMLIT_PORT" --server.address 127.0.0.1
