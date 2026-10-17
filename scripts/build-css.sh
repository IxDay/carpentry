#!/usr/bin/env bash
#
# Build assets/css/site.css from assets/css/_tailwind.css.
#
#   scripts/build-css.sh            once, minified
#   scripts/build-css.sh --watch    again on each change
#
# Runs the Tailwind CLI out of node_modules and does not fall back to `npx`,
# because npx downloads a package when the local one is absent and that hides
# the real fault: nobody ran `npm install`.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

INPUT="assets/css/_tailwind.css"
OUTPUT="assets/css/site.css"
CLI="node_modules/.bin/tailwindcss"

if [ ! -x "$CLI" ]; then
  echo "error: the Tailwind CLI is absent at $ROOT/$CLI" >&2
  echo "       run 'npm install' in $ROOT first." >&2
  exit 1
fi

if [ "${1:-}" = "--watch" ]; then
  exec "$CLI" --input "$INPUT" --output "$OUTPUT" --watch
fi

"$CLI" --input "$INPUT" --output "$OUTPUT" --minify

if [ ! -s "$OUTPUT" ]; then
  echo "error: the build wrote no CSS to $ROOT/$OUTPUT" >&2
  exit 1
fi

# The stylesheet is embedded at compile time, so a new one is a new binary.
# Touching the module that embeds it is what makes cargo notice.
touch src/assets.rs

echo "built $OUTPUT ($(wc -c < "$OUTPUT" | tr -d ' ') bytes)"
