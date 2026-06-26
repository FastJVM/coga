---
name: coga/gmail
description: Reusable Gmail capability — search a mailbox, fetch a parsed message, and download attachment bytes via OAuth user credentials, so skills don't depend on a per-host binary or the Gmail MCP (which can't return attachment bytes). Other skills shell to this skill's gmail.py.
---

# Gmail capability

The Gmail analogue of `coga/google-calendar`: a shared, bootstrapped capability
any coga skill can use to read a mailbox and pull attachments, without a
per-machine binary or the Gmail MCP. The logic lives in `gmail.py`, a
self-contained script other skills shell to.

It exists because the Gmail MCP exposes attachment *filenames/IDs* but has **no
tool that returns attachment bytes** — so any skill that must download a
document (e.g. forwarding patent docs to counsel) needs this.

## Commands

```sh
python <coga>/skills/coga/gmail/gmail.py search \
    --query 'from:uspto.gov has:attachment newer_than:12m' --max 50
python .../gmail.py get --message-id <id>
python .../gmail.py download --message-id <id> --attachment-id <id> --out /path/file.pdf
python .../gmail.py authorize --client-secret /path/to/client_secret.json
```

- `search` → `{messages: [{id, threadId}], nextPageToken?}`
- `get` → normalized `{id, threadId, date, sender, subject, snippet, body_text,
  attachments: [{filename, mimeType, size, attachmentId}]}`
- `download` → writes bytes to `--out`, prints `{path, bytes}`
- `authorize` → prints the `[gmail]` block to paste into `coga.local.toml`

Exit codes are the contract: `0` ok · `1` config/auth/API error (stderr) · `3`
message/attachment not found.

## Auth — OAuth user credentials

Reads `[gmail]` from `coga.local.toml` (`client_id`, `client_secret`,
`refresh_token`, `user`; each `env:VAR`-referenceable). OAuth works on any
Google account — Workspace or personal — and needs no admin, unlike the
calendar service account; that is the right model for reading a human's
mailbox. Scope is `gmail.readonly` — this capability never sends or modifies
mail.

One-time setup: create an OAuth **Desktop app** client in Google Cloud Console,
enable the Gmail API, download the client-secret JSON, then run
`gmail.py authorize --client-secret <json>` (opens a browser; sign in as the
mailbox to read) and paste the printed `[gmail]` block into `coga.local.toml`.

## Dependencies

`google-api-python-client`, `google-auth`, `google-auth-oauthlib` (in
`requirements.txt`), installed into `.coga/.venv` by coga's per-skill install
pass at bootstrap / `coga init --update`.
