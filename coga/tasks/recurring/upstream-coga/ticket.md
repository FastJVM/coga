---
title: Upstream Coga findings
status: done
owner: nicktoper
agent: claude
contexts:
- coga/period-task
period_generation: 12fb7535-dfc6-4e98-9a90-16807e118acc
workflow:
  name: upstream-coga/run
  steps:
  - name: sweep
    skills: []
    assignee: agent
---

## Description

Pull Coga findings out of client repos and file them here.

When Dream runs in a client repo — one with Coga installed that is not the Coga
source repo — it keeps Coga-owned files out of its corpus, but a client-owned
file can still make a claim only Coga's implementation can settle. Dream marks
such a finding `owner: coga` and Phase 6 appends it to that checkout's
append-only `coga/upstream-coga.md` instead of proposing a local edit (see the
Dream template's Phase 6). Nothing in the client repo reaches into this one:
the direction is deliberately **this repo pulls**, so a client needs no
credentials for this repo and no knowledge of where it lives.

Once a week this task's `ticket.py` sweeps the checkouts named by machine-local
`[upstream] checkouts` in `coga.local.toml`. For each one it:

1. reads `<checkout>/coga/upstream-coga.md`, skipping a missing checkout or a
   missing file with a printed note, never an error;
2. skips every entry at or before that checkout's cursor (below), and stops
   for that checkout — reporting instead of re-filing the whole file — when
   the recorded cursor id is no longer present, which only truncation or a
   rewrite can cause;
3. files one plain draft ticket per remaining entry with `coga.create`,
   titled from the entry and carrying its `upstream-id`, `repo`, `date`,
   `class`, `target`, `evidence` lines and prose in the description — a
   draft, with no workflow, so a human triages before anything launches;
4. advances the cursor after each entry, then syncs the template and every
   filed ticket through git in one commit.

The `- upstream-id: <checkout-name>/<id>` line on each filed ticket is the
durable identity: the processor greps existing tasks for it before creating,
so a run interrupted between filing and the cursor write files nothing twice.

### Operating it

Only the machine holding the client checkouts can run this job. Name them in
`coga.local.toml` — never `coga.toml`, the paths are machine-specific:

```toml
[upstream]
checkouts = ["~/Code/multiply", "~/Code/magicator"]
```

Paths must be absolute (`~` expands); a relative one is rejected at config
load because it would resolve against whatever directory the command ran
from. A path that does not exist is accepted at config load and skipped at
run time. The directory name is the cursor key, so a name containing
whitespace is skipped with a note — rename it or point the entry at a symlink.
Two configured checkouts sharing a directory name are ambiguous: the sweep
files nothing for either and says so. Run it now with
`coga recurring launch upstream-coga`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
