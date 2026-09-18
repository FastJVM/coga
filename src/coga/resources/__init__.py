"""Packaged prompt/protocol resources and the `coga init` template tree.

**This file is load-bearing — do not delete it as an empty package marker.**
It exists to keep `coga.resources` a *regular* package rather than an implicit
namespace package, because `importlib.resources.files()` returns a different
type for each:

- regular package → a plain `pathlib.Path` for the package directory;
- namespace package → an `importlib.resources.readers.MultiplexedPath`.

On Python 3.11 — the oldest interpreter Coga supports — `MultiplexedPath` is
`def joinpath(self, child)`: exactly *one* segment. It only grew the
`joinpath(*descendants)` signature in 3.12. Every multi-segment call site
(`paths.packaged_template_path`, `commands.update.packaged_template_root`,
`managed_skills.managed_skill_manifest_root`,
`dream_cleanup_orphan_markers`) therefore raised
`TypeError: MultiplexedPath.joinpath() takes 2 positional arguments but N were
given` on 3.11, crashing `coga init` before it could lay down a single template
(it died in `packaged_template_root`, on the two-segment `templates/coga`).
3.12 happened to work, which is why the break stayed invisible in local
development.

`MultiplexedPath` also has no `__fspath__`, so the `Path(files(...).joinpath(...))`
conversions those helpers do would fail on a directory resource regardless of
segment count.
"""

from __future__ import annotations
