#!/usr/bin/env bash
# DRY-RUN DEMO — does not run the real Xero automation.
#
# This file exists to show the shape of a mode: script skill inside Relay:
# a SKILL.md with a bundled executable. At runtime, `relay launch` would
# invoke this script with secrets injected as env vars.
#
# To wire this up to the real automation at
# ~/Desktop/Xero_Reconciliation_Automation, replace the body below with:
#
#     set -euo pipefail
#     cd "${HOME}/Desktop/Xero_Reconciliation_Automation"
#     exec ./run.sh   # or: npm run reconcile
#
# Do NOT do that until you're ready to cut the existing launchd job over
# to relay. For now this is a demonstration — it prints what would happen
# and exits cleanly.

set -euo pipefail

echo "[relay demo] xero-reconcile: dry run"
echo "[relay demo] would exec: ~/Desktop/Xero_Reconciliation_Automation/run.sh"
echo "[relay demo] secrets in env: SLACK_WEBHOOK=${SLACK_WEBHOOK:-<unset>}"
echo "[relay demo] exiting 0 without touching anything"
exit 0
