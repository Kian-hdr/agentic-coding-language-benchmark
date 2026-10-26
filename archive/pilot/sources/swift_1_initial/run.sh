#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -x "$here/program" ] || [ "$here/main.swift" -nt "$here/program" ]; then
  xcrun swiftc -module-cache-path "$here/.module_cache" -O "$here/main.swift" -o "$here/program"
fi
exec "$here/program" "$1"
