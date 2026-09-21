# Attribution

This skill is imported verbatim from Anthropic's public skills repository.

- Upstream: https://github.com/anthropics/skills
- Upstream path: `skills/skill-creator/`
- Vendored here as: `coga/skills/anthropic/skill-creator/`
- Pinned commit: `f458cee31a7577a47ba0c9a101976fa599385174`
- License: Apache 2.0 (see `LICENSE.txt`)

To refresh, re-copy upstream `skills/skill-creator/` over
`coga/skills/anthropic/skill-creator/` from a newer upstream commit and update
the pinned SHA above. Preserve upstream's standards-valid leaf metadata
(`name: skill-creator`); Coga derives the namespaced ref
`anthropic/skill-creator` from the directory path rather than from `name:`.

This skill is deliberately unmanaged: it is not in
`src/coga/resources/managed-skills.toml`, carries no `.coga-source.json`, and
sits outside every updater path, so the weekly `coga/recurring/skill-update`
run leaves it alone and this file is its attribution home (decision recorded
by ticket `vendored-skills-carry-no-coga-source-json-so-coga`). Refresh is the
manual re-copy above. The managed routes now exist for other skills —
`coga skill install` (GitHub-backed via `gh skill`), `coga skill install-url`
(writes `.coga-source.json` with an `include` allowlist and
`local_adaptation_notes`; `coga/skills/clarity/` is a live instance) and
`coga skill update` — and `install-url` is the route to take if this skill
should ever become managed.
