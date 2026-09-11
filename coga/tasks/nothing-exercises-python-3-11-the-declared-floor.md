---
title: Nothing exercises Python 3.11, the declared floor
status: draft
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

`pyproject.toml` declares `requires-python = ">=3.11"`, but nothing runs the
suite on 3.11. `.github/workflows/` contains only `release.yml`, a PyPI publish
workflow with no pytest step, and `coga/contexts/coga/codebase/SKILL.md` tells
the reader to run `PYTHONPATH=$PWD/src python3.12 -m pytest` because the ambient
`python3` is often 3.9. That guidance is correct about 3.9 and silently makes
the declared floor untested.

The cost is already on record. `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r`
found that `coga init` — the first command a new user runs — crashed on every
3.11 interpreter with `TypeError: MultiplexedPath.joinpath() takes 2 positional
arguments but 3 were given`, because `src/coga/resources/` shipped no
`__init__.py` and `importlib.resources.files()` returns a `MultiplexedPath`
(single-segment `joinpath`, no `__fspath__` before 3.12) for a namespace
package. The ticket says outright that "3.12 happens to work, which is why the
break stayed invisible in local development and CI", and it affected five call
sites across `paths.py`, `update.py`, `managed_skills.py` and
`dream_cleanup_orphan_markers.py`. The same ticket notes that
`src/coga/commands/__init__.py` leaves the identical namespace-package footgun
latent.

## Context

Two things are wanted and they are separable:

1. A real 3.11 verification step, so the declared floor is exercised rather
   than assumed. There is no test CI workflow at all today, which is the larger
   half of this.
2. The rule written into `coga/contexts/coga/codebase/SKILL.md` (and its
   enforced packaged twin): never add a new `files("coga.<pkg>")` consumer
   without a package marker, and a green 3.12 run is not evidence for the
   declared floor.

If the floor is not going to be tested, the honest alternative is to raise
`requires-python` — but that is an owner decision, not an implementer's.

Environment note from this Dream run: `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`
currently fails on this machine for an unrelated reason (`hatchling` is not
importable by the ambient interpreter), which is worth knowing before anyone
reads a red suite as evidence here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
