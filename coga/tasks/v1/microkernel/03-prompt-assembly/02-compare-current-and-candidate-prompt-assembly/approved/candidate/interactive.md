Use the exact target path in the header; do not reconstruct it. Follow the
Checkout (runtime) notice: do not repeat prepared setup or return a checkout
the launcher owns. If no preparation or branch setup was supplied, read
`coga/checkouts` and follow its complete procedure before editing. If unexpected
or failed, read `coga/checkouts/launch-boundary` for recovery. Identify the
branch's ticket, check its current control status and PR merge status, and
inspect uncommitted edits separately. Explain what is finished and unknown.
Do not automatically stash, discard work or switch an occupied checkout.

Before publishing or handing off any edits, read and follow
`coga/checkouts/reconciliation`; fetch current main, preserve unique work and
resolve ordinary drift. Use the selected conduct for unclear intent or access.

Do not edit `coga.toml` or `coga.local.toml`. Do not launch an agent with nested
`coga launch`; use an available sub-session or edit files directly. Script-mode
launches that run a skill without another agent are allowed.
