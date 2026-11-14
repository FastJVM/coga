#!/bin/sh
# Disposable: run unattended sessions back to back (counterbalanced order, pairs adjacent).
set -u
T=$(cd "$(dirname "$0")" && pwd)
for spec in "code baseline 1" "code candidate 1" "design candidate 1" "design baseline 1" \
            "docs baseline 1" "docs candidate 1" "code candidate 2" "code baseline 2" \
            "design baseline 2" "design candidate 2" "docs candidate 2" "docs baseline 2"; do
  set -- $spec
  [ -d "$T/runs/$1__$2__r$3" ] && { echo "skip $spec"; continue; }
  echo "$(date -u +%FT%TZ) start $spec"
  "$T/ctl.sh" start "$1" "$2" "$3"
  until [ "$("$T/ctl.sh" done)" = yes ]; do sleep 20; done
  sleep 2; "$T/ctl.sh" stop
  python3 -c "import json;r=json.load(open('$T/runs/$1__$2__r$3/record.json'));print('$(date -u +%FT%TZ) end $spec', r.get('result'), r.get('wall_seconds'), r.get('production_equals_frozen_baseline'), r.get('delivered',{}).get('equals_frozen_modulo_marker'), r.get('live_repo_changed'), r.get('venv_changed'))"
done
echo ALL-DONE
