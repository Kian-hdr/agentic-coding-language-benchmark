#!/bin/sh
set -eu
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$1" in
  /*) request=$1 ;;
  *) request=$PWD/$1 ;;
esac
export BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml
export DO_NOT_TRACK=1
exec "$BAML_HOME/bin/baml" --agent-skill-check off --directory "$dir" run main --output-format json -- --path "$request"
