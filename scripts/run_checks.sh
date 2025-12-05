#!/usr/bin/env bash
set -euo pipefail

# Basic syntax check for AFCS desktop and mobile entrypoints.
python -m compileall afcs mobile main.py
