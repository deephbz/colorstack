#!/usr/bin/env bash
# Convenience entrypoint for the explicit Colorstack output-bundle switcher.
set -euo pipefail
exec python3 "$(cd -- "$(dirname -- "$0")" && pwd)/switch.py" "$@"
