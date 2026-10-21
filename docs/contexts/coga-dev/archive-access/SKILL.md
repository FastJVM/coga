---
name: coga-dev/archive-access
description: The human-request requirement for reading or searching this repository’s dated archives.
---

# Archive access in the Coga repository

## Archive access

Agents must exclude `docs/archive/**`, including evidence and design pages,
from searches and reading unless the human explicitly requests archive use
for the current task. A link, citation, reusable instruction, or general
research request is not permission to open archived material. If the task
needs it, ask before reading.

Scope searches to live directories, or exclude the archive explicitly when
searching from the repository root: `rg --glob '!docs/archive/**' ...` and
`rg --files --glob '!docs/archive/**'`. This applies to other search and
file-reading tools too. Authorized archive material remains historical
evidence, not current instructions. This is an agent instruction, not a
filesystem access restriction.
