#!/bin/sh
# Sync the completed local update. A rejected push leaves the local commit intact.
set -eu
cd "$(dirname "$0")/.."
if [ "$#" -ne 1 ] || [ -z "$1" ]; then
    echo 'Usage: sh tools/sync_github.sh "Describe the update"' >&2
    exit 2
fi
if [ "$(git branch --show-current)" != main ]; then
    echo 'Switch to main before syncing a project update.' >&2
    exit 1
fi
exec python3 tools/github_export.py --sync "$1"
