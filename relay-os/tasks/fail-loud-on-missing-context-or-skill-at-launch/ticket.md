---
title: Fail loud on missing context or skill at launch
status: draft
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: claude1
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement-and-pr
  - name: review
step: 1 (implement)
---

## Description

`relay launch` silently skips referenced contexts and skills that don't
exist. A ticket can list `contexts: [foo]` where `foo/context.md` is
missing and the launch will succeed with that layer simply absent from the
composed prompt. The agent then runs without the knowledge the human
expected it to have, producing confidently wrong output — exactly the
"silent wrong answer" failure mode the vision flags as unacceptable.

Look at `src/relay/compose.py` around the loops that load contexts and
skills (the audit pointed at lines ~57-60, ~127-130, ~148-151 — verify
current line numbers). Each one catches the missing-file case and
continues.

`docs/spec.md` lists missing-context / missing-skill in the error table as
fail-loud cases. The implementation should match: raise during `compose`,
let `launch` surface the error, and refuse to start the task.

## Context

- Audit entry: `docs/spec-audit.md` §A.4.
- Compose pipeline: `src/relay/compose.py`.
- Spec error contract: `docs/spec.md` (search for the error / failure
  table; missing context and missing skill should be listed there).
- Vision principle: `docs/vision.md` — silent fallbacks violate the
  legibility / short-correction-loop goals.

## Acceptance criteria

- [ ] Launch raises a clear error naming the missing context/skill and
      the ticket that referenced it.
- [ ] Error message tells the user the exact file path that should exist.
- [ ] `relay validate` already catches the same condition statically — if
      it doesn't, add a check there too.
- [ ] Test added to `tests/` covering both missing-context and
      missing-skill at launch.
