#!/usr/bin/env bash
# Run the trial service locally: http://127.0.0.1:8000  (needs python3, LibreOffice, poppler-utils; see README.md)
set -euo pipefail
cd "$(dirname "$0")"
exec python3 -m uvicorn app:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}" --workers 1
