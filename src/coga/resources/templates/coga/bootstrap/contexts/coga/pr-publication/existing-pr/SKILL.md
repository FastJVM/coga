---
name: coga/pr-publication/existing-pr
description: How `coga open-pr` refreshes an existing PR — the `coga:pr:v1` generated-region markers, adopting an unmarked PR, the conflicts that refuse, and the open-PR lookup.
---

# Updating an existing PR

Part of [coga/pr-publication](../SKILL.md).

New bodies wrap generated content in `coga:pr:v1` HTML comment markers with
SHA-256 digests of the generated title and content. These are change detectors,
not authentication. LF and CRLF line endings compare equally; other generated
content edits still conflict. Human notes outside the marked region retain
their exact bytes, including line endings, during updates.
On reuse, title/body are fetched: unchanged generated content is refreshed,
including the ticket snapshot and evidence, before a draft is readied or `pr:`
is recorded. An unchanged rerun does not edit. An existing PR targeting another
base refuses because the prepared comparison would not describe its diff.

An unmarked PR from before the markers is adopted when its title is still the
plain ticket title Coga used to publish: the generated region is placed first
and the entire old body is kept below it as human-owned notes, so nothing is
lost and later reruns refresh only the region. An unmarked PR whose title a
human changed, a modified generated title, or a modified/malformed generated
region refuses instead of silently keeping stale text or overwriting human
edits. Reconcile with the owner: preserve wanted human prose outside the
markers, move intended generated changes into `## PR`, and restore the last
generated title/region (for an unmarked PR, the ticket title) before
rerunning. There is no force-overwrite flag. Resolve detected
conflicts before pushing. Lookup uses `gh pr view <branch>`, whose bare-branch
finder excludes same-named fork heads. Only its explicit branch-not-found
response or a valid closed/merged PR proves no open PR exists. API/auth errors,
malformed or incomplete results, and cross-repository heads refuse before push.
Re-read after
push to catch intervening edits before updating. GitHub has no atomic
compare-and-set for these title/body edits, so
a simultaneous edit after that last read can still race; avoid co-editing
presentation during publication. `gh` edit errors refuse without advancing.
