## Dev
branch: test-conformance-in-implement
worktree: ../relay-test-conformance
pr: https://github.com/FastJVM/relay/pull/331

## Decision

Did NOT build a standalone unit-test-writing skill. Discussed with nick and
agreed a generic "write good tests" skill is boilerplate an Opus-class agent
already follows unprompted — and `relay/project-stage` says no premature
generality. The only non-obvious value is *conformance to the existing suite*
(agents write clean-from-scratch tests instead of matching a quirky neighbor).

That's process knowledge → belongs in a skill, not a context. It's small
enough to fold directly into `code/implement`'s existing "Test" step rather
than a new skill no workflow currently wires in.

Change: `code/implement` step 4 now requires reading a sibling test first and
mirroring it, reusing the repo's harness (no new framework/assertion/mock
deps), and keeping coverage deterministic + low-scaffolding.

`code/*` skills are project-local only — no packaged-template copy to sync.

Sibling tickets `add-dev-testing-setup-skill` and `add-dev-test-run-skill`
remain as drafts; this ticket's conclusion (don't over-build generic test
skills) may apply to them too.
