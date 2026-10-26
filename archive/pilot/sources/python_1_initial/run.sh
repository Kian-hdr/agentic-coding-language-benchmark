#!/bin/sh
exec {ORIGINAL_HOMEBREW}/bin/python3.14 "$(dirname "$0")/main.py" "$1"
