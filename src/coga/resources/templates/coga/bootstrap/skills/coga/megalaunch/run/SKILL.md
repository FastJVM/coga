---
name: coga/megalaunch/run
description: Run the shared megalaunch engine and write a bounded run summary.
script: run.py
---

# Megalaunch Runner

This skill is the script body for the `recurring/megalaunch` task. It calls the
same `coga.megalaunch.run_megalaunch` engine used by the manual
`coga megalaunch` command, then replaces the task blackboard's
`## Megalaunch Run Summary` section with the latest compact summary.

The engine spawns each eligible step as a normal interactive launch (PTY
watcher, done-sentinel teardown, idle-timeout backstop), so it requires a
TTY. Run headless, the script fails loud with exit 2 rather than launching
agents nobody can watch.
