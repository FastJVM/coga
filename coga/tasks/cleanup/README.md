# cleanup/

Product and first-run work found during the original marketing audit. The
fresh marketing plan decides which completed fixes or remaining prerequisites
its selected reader path needs; indexing this queue does not make every task
a publication gate. Each product ticket retains its own scope.

The owner opened this directory on 2026-09-03 while finishing step 2 of
`marketing/phase-0-audit`. That audit ran the README quickstart end to end on
a fresh repo and found the first-run path broken in several independent ways;
these tickets are those findings, plus the release that makes a first run
possible at all. The dated [step-1 findings](../../../docs/archive/launch-programs/phase-0-audit/step-1-findings.md)
hold the original evidence; check each ticket for its current state.

The queue is drained and retired: every ticket finished `done` and has been
removed, so this README is the group's only remaining file. Find a retired
ticket's body with the `git log --diff-filter=D` recipe in
`coga/tickets/discovery`.

## Ordering

One hard dependency was recorded in the ticket bodies:
`fix-coga-init-crash-on-python-3-11-by-adding-the-r` had to land before the
release ticket, now `v1/43-publish-coga-1-0-as-the-final-v1-step`, cuts
the release. That fix is `done`, so nothing here still gates the release.

## Not here

- `v1/32-finish-the-readme-launch-checks-left-open-by-readm` owns the remaining
  README checks, including the existing demo's accuracy. It succeeds retired
  `marketing/readme-top`, which absorbed
  `cleanup/check-the-demo-video-against-current-cli-names`;
  a new video is not a V1 launch prerequisite.
- Community setup is outside the approved V1 campaign. The superseded
  `marketing/discord` ticket was removed; repository hygiene does not create
  a community requirement.
