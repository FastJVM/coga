# Autoclose worklist setup

A repo initialized before `retires.md` shipped needs `**/retires.md
merge=union` in `coga/.gitattributes` (fresh `coga init` writes it) and
refreshed local copies of the packaged `autoclose-merged` template and
`workflows/autoclose-merged/sweep.md`, whose prose composes into every period;
behavior comes from the upgraded package. The `coga/autoclose/sweep` skill
owns the backfill line shape.
