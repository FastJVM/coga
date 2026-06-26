# email-tool — repo context

The email-tool repo handles deliverability diagnostics and Stripe billing for
YC-backed customers. Python 3.11+. Tests via pytest. Postgres 14.

Entry points:
- `src/email_tool/cli.py` — CLI.
- `src/email_tool/webhooks/` — all Stripe handlers.
- `src/email_tool/deliverability/` — SPF/DKIM/DMARC checks.

Deploys: Fly.io. Staging: `email-tool-staging.fly.dev`. Prod: `email-tool.fly.dev`.
