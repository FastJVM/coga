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
python /resolved/coga/gmail/gmail.py search \
    --query 'from:uspto.gov has:attachment newer_than:12m' --max 50
python .../gmail.py get --message-id <id>
python .../gmail.py download --message-id <id> --attachment-id <id> --out /path/file.pdf
python .../gmail.py authorize --client-secret /path/to/client_secret.json
```

- `search` → `{messages: [{id, threadId}], nextPageToken?}`
- `get` → normalized `{id, threadId, date, sender, subject, snippet, body_text,
  attachments: [{filename, mimeType, size, attachmentId}]}`
- `download` → writes bytes to `--out`, prints `{path, bytes}`
- `authorize` → prints the four `GMAIL_*=<value>` lines to store as secrets

Exit codes are the contract: `0` ok · `1` config/auth/API error (stderr) · `3`
message/attachment not found.

`/resolved/coga/gmail/` stands for this skill's resolved directory: the repo's
local `coga/skills/coga/gmail/` override if one exists, else the installed
bundled skill (resolution as in `coga/checkouts/sandbox-clone`, "What a fresh
checkout lacks"). Bundled skills are not copied into the repo.

## Auth — OAuth user credentials

Reads `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, and
`GMAIL_USER` (the mailbox address) from the environment — never from Coga
config. The consuming ticket declares all four in its `secrets:` frontmatter,
and launch resolves them into the child environment
(`coga/secrets`):

```yaml
secrets:
  - GMAIL_CLIENT_ID: op://<automation-vault>/<item>/client_id
  - GMAIL_CLIENT_SECRET: op://<automation-vault>/<item>/client_secret
  - GMAIL_REFRESH_TOKEN: op://<automation-vault>/<item>/refresh_token
  - GMAIL_USER: op://<automation-vault>/<item>/user
```

`env:VAR` refs work for values the operator already exports; a manual run
outside launch exports the four variables itself. OAuth works on any
Google account — Workspace or personal — and needs no admin, unlike the
calendar service account; that is the right model for reading a human's
mailbox. Scope is `gmail.readonly` — this capability never sends or modifies
mail.

One-time setup: create an OAuth **Desktop app** client in Google Cloud Console,
enable the Gmail API, download the client-secret JSON, then run
`gmail.py authorize --client-secret <json>` (opens a browser; sign in as the
mailbox to read) and store the four printed values in the automation vault (or
your environment). Never commit them.

To migrate an existing `[gmail]` entry, reuse its four values under the
corresponding environment names above, then remove the retired table from
`coga.local.toml` so Coga can load the repo.

## Dependencies

`google-api-python-client`, `google-auth`, `google-auth-oauthlib` (in
`requirements.txt`). Coga installs nothing for a skill — run
`python -m pip install -r requirements.txt` from this skill's resolved dir,
using the same Python that runs `gmail.py`.
