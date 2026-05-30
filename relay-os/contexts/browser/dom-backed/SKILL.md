---
name: browser/dom-backed
description: DOM-backed browser automation standard for real SaaS workflows. Attach to browser tasks that should use Playwright snapshots, accessibility-tree refs, and DOM selectors only.
---

# DOM-Backed Browser Automation

Use DOM-backed automation as the only browser-control method for tickets
that attach this context.

Multiple Playwright runners (CLI, MCP) are available. Pick one runner
per task. After the active test track, we choose one as the primary;
the other stays available for separate exploratory tasks but is never
used as an in-run fallback. Do not switch runners mid-task.

## Allowed control surfaces

- Playwright accessibility snapshot output and its fresh element refs, whether surfaced through MCP or CLI.
- Playwright locator behavior when exposed by the selected runner.
- DOM and accessibility-tree inspection through `eval` when it supports diagnosis or structured extraction.
- Screenshots, traces, console output, and network logs as evidence and debugging artifacts.

Screenshots are not a targeting mechanism. Do not use visual recognition, set-of-mark overlays, OCR, coordinate clicks, or mouse-position guessing for normal task execution.

## Known DOM gaps

Some browser UI renders outside the accessibility tree and is not reachable by Playwright refs. Known examples:

- **Chrome's PDF viewer toolbar.** When a link opens a PDF inline (rather than triggering a native download), the toolbar — including the download button — is browser chrome, not DOM. A `snapshot` of the PDF tab returns an empty tree.
- **Native browser dialogs** (`alert`, `confirm`, `beforeunload`) — handled via the runner's dialog API, not refs.

When the final action is behind one of these gaps, DOM-backed alone cannot complete it. DOM-pure paths out:

- For inline PDFs: read `location.href` of the new tab (via `eval`), then HTTP-fetch the URL. Click is DOM-driven; save is HTTP. The boundary is clean and logged.
- For dialogs: use the runner's dialog handler explicitly.

Set-of-mark (SOM) is the candidate fallback for native-chrome UI because the button is visually present. SOM is not used as an in-run fallback; if a task needs SOM, that's a separate ticket with its own context.

## Standard loop

1. Open the target page in the selected Playwright runner, using a named session/profile when the runner supports it.
2. Take a fresh snapshot.
3. Identify the actionable DOM-backed ref or locator. Trust the action label the DOM exposes (e.g. `link "View"` is not `link "Download"`). If the label disagrees with the plan, the plan is wrong.
4. If the automation cannot continue using DOM-backed evidence, stop and fail loudly.
5. Perform the action by ref or locator.
6. Re-snapshot after navigation, row removal, modal open/close, tab switch, or any substantial DOM change.
7. Record the artifact paths and the exact decision rule in the task blackboard.

## Failure Process

If the DOM-backed method cannot finish the automation, fail loudly.
Do not predict or enumerate failure cases up front, and do not switch
to another automation method inside a DOM-only run.

When failing, write a short blocker entry to `blackboard.md` with:

- current URL
- latest snapshot path
- screenshot or trace path if useful
- intended action
- the exact ref or locator the automation expected to act on (so the
  human reviewing the blocker can verify the fix targets the same
  element after a re-snapshot, since refs are per-snapshot and a new
  snapshot will assign new ones)
- one-sentence reason the automation could not continue
- the smallest next step needed to proceed

## Restart Process

When the human resolves a blocker and restarts the automation:

- Take a fresh snapshot before any ref-based action. Refs from the
  pre-failure snapshot are stale and must not be reused.
- Re-identify the intended element from the new snapshot using the
  ref/locator description recorded in the blocker entry.
- If the element no longer matches the description, fail loudly again
  rather than acting on a guess.

## Artifacts

Minimum per task:

- Screenshot before the first action.
- Screenshot after the last action (or after the failure point).
- One-line failure reason in the blocker entry, if the run failed.

When a ref-based action fires, also save the snapshot text that
drove the decision (e.g. `artifacts/snap-NN.txt`) alongside the
screenshot. The snapshot is what tells a reviewer *why* the agent
picked that ref — screenshots only show the visual outcome and are
the wrong tool for diagnosing a wrong-element click.

Tickets may require additional captures (initial state, post-mutation
state, final state); follow the ticket's acceptance criteria when it
asks for more than the minimum.

## Per-Site Learning

Each real-site task should leave behind reusable observations:

- stable entry URLs and account or entity identifiers
- login and profile-persistence behavior
- DOM signatures for safe actions
- DOM signatures for manual or human-review states
- failure modes and how they should surface
- whether the selected runner was easier or harder than MCP/CLI alternatives for setup, debugging, portability, and future robustness

Promote durable findings into this context or a site-specific skill only after the task has been exercised against the real workflow. Keep runner comparisons (CLI vs MCP) in task blackboards until there is enough evidence to pick a primary; once a primary is chosen, record the decision here and stop re-comparing in every task.
