# Autoclose worklist setup

A repo initialized before `retires.md` shipped needs `**/retires.md
merge=union` in `coga/.gitattributes` (fresh `coga init` writes it) and
refreshed local copies of the packaged `autoclose-merged` template and
`workflows/autoclose-merged/sweep.md`, whose prose composes into every period;
behavior comes from the upgraded package. The `coga/autoclose/sweep` skill
owns the backfill line shape.

A full local override or an outstanding period whose `ticket.py` predates the
edge job still calls `coga.autoclose` or `coga run autoclose`, both removed.
Follow [adopting wheel-owned edge code](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md)
("Recipe-backed recurring shims") to replace or hand-port it; a state-only
carrier needs nothing.
