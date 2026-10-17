#!/usr/bin/env bash
# Run the suite on other LibreOffice versions, in containers: the PDF engine does not behave the same from one version
# to the next (kashida, where a page ends), and the skill must not depend on the version installed here.
# Needs podman or docker.   usage: tests/lo_versions.sh [ubuntu tag…]   default: 22.04 (LibreOffice 7.3) and 24.04 (24.2)
set -euo pipefail
cd "$(dirname "$0")/.."
C=$(command -v podman || command -v docker)
for v in "${@:-22.04 24.04}"; do for v in $v; do
  printf 'FROM docker.io/library/ubuntu:%s\nRUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libreoffice-writer python3 python3-pip poppler-utils fontconfig fonts-dejavu-core fonts-liberation && (pip3 install --break-system-packages fonttools pdfplumber || pip3 install fonttools pdfplumber)\n' "$v" | "$C" build -q -t "saffaf-lo:$v" -f - . >/dev/null
  echo "== ubuntu $v"
  "$C" run --rm -v "$PWD":/repo:ro "saffaf-lo:$v" bash -c 'soffice --version | head -1; cd /repo && python3 tests/run_tests.py | grep -E "^(FAIL|INFO l)|passed"' || true
done; done
