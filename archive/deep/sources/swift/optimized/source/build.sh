#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec {ORIGINAL_XCODE_APP}/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc -O -whole-module-optimization -module-cache-path "$here/.build_cache" "$here/main.swift" -o "$here/program"
