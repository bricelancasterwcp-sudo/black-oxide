#!/usr/bin/env bash
# Minimal RunPod REST wrapper. usage: runpod_api.sh {pods|create|terminate <id>|spend}
set -euo pipefail
KEY="$(cat "$HOME/.config/runpod/api_key")"
API="https://rest.runpod.io/v1"
case "$1" in
  pods)      curl -sf -H "Authorization: Bearer $KEY" "$API/pods" ;;
  terminate) curl -sf -X DELETE -H "Authorization: Bearer $KEY" "$API/pods/$2" ;;
  create)    curl -sf -X POST -H "Authorization: Bearer $KEY" \
               -H "Content-Type: application/json" \
               -d @"$2" "$API/pods" ;;   # $2 = json spec file
  spend)     curl -sf -H "Authorization: Bearer $KEY" "$API/billing" ;;
  *) echo "usage: pods|create <spec.json>|terminate <id>|spend" >&2; exit 2 ;;
esac
