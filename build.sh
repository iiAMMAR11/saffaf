#!/usr/bin/env bash
# Run the tests, then package the skill for release.
# The version is the first «## x.y.z» heading of CHANGELOG.md; the package is written under the stable names
# (saffaf.zip / saffaf.skill — the download link always points at saffaf.zip) and once more with the version
# in its name (saffaf-x.y.z.zip), so a downloaded file says which version it is.
set -euo pipefail
cd "$(dirname "$0")"
VERSION=$(grep -m1 -oE '^## [0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md | cut -d' ' -f2)
[ -n "$VERSION" ] || { echo "no version heading in CHANGELOG.md" >&2; exit 1; }
python3 tests/run_tests.py
mkdir -p dist
rm -f dist/saffaf.skill dist/saffaf.zip dist/saffaf-*.zip
(cd skill && zip -qr ../dist/saffaf.zip saffaf -x '*__pycache__*' '*.DS_Store')
cp dist/saffaf.zip dist/saffaf.skill
cp dist/saffaf.zip "dist/saffaf-$VERSION.zip"
echo "Packaged $VERSION: dist/saffaf.skill, dist/saffaf.zip and dist/saffaf-$VERSION.zip"
