# Package-owned definitions release notes

Shipped definitions (contexts, skills, workflows, bootstrap tickets and the
bundled recurring jobs with their scripts and runbooks) now have one owner:
the installed Coga package. Repos resolve them from the package unless they
keep a deliberate local override of the same ref.

- **Fresh repos.** `coga init` copies only scaffolds (`coga.toml`,
  `context.md`, `log.md`, ignore/attribute files, authoring starters and the
  onboarding task) and writes `coga/recurring/jobs.toml` selecting the nine
  bundled recurring jobs. Each job's repo state is a small state-only carrier
  created on its first run.
- **Existing repos.** Nothing changes on upgrade. Local definitions keep
  their activation, deleted or parked jobs stay gone, and a newly bundled job
  stays disabled until `jobs.toml` selects it. `false` disables a job even
  under `--force` and named launch.
- **Overrides fail loudly.** A local skill, bootstrap ticket or recurring job
  that exists but is unusable is an error, never a silent fallback to stock
  text. A lone `ticket.py` beside a state carrier is an incomplete fork.
- **trim-log adoption** (`python -m coga_edge.trim_log --install`) now records
  the selection and the `/log.md -merge` attribute instead of copying files.

Moving an existing repo's stock copies onto the package is optional and
manual: follow the
[migration and rollback procedure](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/package-definitions-migration.md).
Require this release or newer in every participating checkout before
migrating; older clients cannot read state carriers.
