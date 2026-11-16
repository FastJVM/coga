Peer-review prompt evidence, 2026-11-15

before-prompt.txt and before-report.json use package source/resources exported
from base 23e0a5b5f2a25d013e9a43209ab2301378de2d04.
after-prompt.txt and after-report.json use PR head
8c53bcecc8cbe7b5125171a80c1593c7ef9966dc.

Both calls used compose_prompt_report on this repository's configuration,
local context definitions and the identical live ticket saved in
capture-ticket.txt (peer-review step). Checkout notice was left at the API's
unsupplied default in both. The CLI prompt-report path was not invoked inside
an agent launch; these are its underlying composition reports. No ticket was
converted or renamed. The paired JSON files include all layer byte/token
counts and total byte/token counts; totals were asserted equal to the UTF-8
lengths of the saved prompts.

Before: 111707 bytes / approximately 27886 tokens.
After:  104676 bytes / approximately 26131 tokens.

The ticket prose itself quotes comment/frontmatter/filler examples as part of
the defect specification; those intentional prose examples remain. Structural
comments, resource metadata, duplicated titles and the standalone placeholder
are removed. Resolved blocker history remains. Open-blocker deduplication is
covered by controlled unit fixtures rather than invented live asks.
