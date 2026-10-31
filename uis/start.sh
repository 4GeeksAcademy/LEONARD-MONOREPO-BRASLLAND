#!/bin/sh
set -eu

npm --prefix /workspace/uis/backoffice run build -- --watch &
backoffice_pid=$!
npm --prefix /workspace/uis/talent-pipeline-tracker run dev -- --hostname 0.0.0.0 --port 3000 &
next_pid=$!

trap 'kill "$backoffice_pid" "$next_pid" 2>/dev/null || true' INT TERM
wait "$next_pid"