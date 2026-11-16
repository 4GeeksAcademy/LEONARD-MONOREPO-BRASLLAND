#!/bin/sh
set -eu

export AUTH_API_URL="${AUTH_API_URL:-http://backend:8012}"

npm --prefix /workspace/uis/backoffice run build -- --watch=forever &
backoffice_pid=$!
npm --prefix /workspace/uis/website run dev -- --hostname 0.0.0.0 --port 3000 &
website_pid=$!
npm --prefix /workspace/uis/talent-pipeline-tracker run dev -- --hostname 0.0.0.0 --port 3001 &
tracker_pid=$!

cleanup() {
  trap - EXIT INT TERM
  kill "$backoffice_pid" "$website_pid" "$tracker_pid" 2>/dev/null || true
  wait "$backoffice_pid" "$website_pid" "$tracker_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

while kill -0 "$backoffice_pid" 2>/dev/null \
  && kill -0 "$website_pid" 2>/dev/null \
  && kill -0 "$tracker_pid" 2>/dev/null; do
  sleep 2
done

echo "A UI process stopped; shutting down the UI container." >&2
exit 1