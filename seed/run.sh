#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
python seed/__init__.py "$@"
