#!/bin/sh
# Build, check that every built file is in the bundle, then
# deploy. A file left out by the upload rules is not an
# error to Cloudflare, only a missing page or prompt later.
set -eu
cd "$(dirname "$0")"

./build.sh

listing=$(uv run pywrangler deploy --dry-run 2>&1)

missing=0

for file in $(cd src && find . -type f ! -name '*.py' | sed 's|^\./||'); do
    if ! printf '%s\n' "$listing" | grep -qF "│ $file "; then
        echo "Not in the bundle: $file"
        missing=1
    fi
done

if [ "$missing" -ne 0 ]; then
    echo "Refusing to deploy: add the files to \"rules\" in wrangler.jsonc."
    exit 1
fi

uv run pywrangler deploy
