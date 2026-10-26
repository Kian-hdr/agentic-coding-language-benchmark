#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$here"
xcrun swiftc -module-cache-path "$here/.module_cache" -O tests.swift -o tests_program
exec "$here/tests_program"
