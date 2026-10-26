#!/bin/sh
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec {ORIGINAL_HOMEBREW}/bin/python3.14 -O "$script_dir/build.py"
