"""Slack feed — posts to the shared webhook from relay.local.toml.
No-op if the webhook is not configured."""
import json
import sys
import urllib.error
import urllib.request

from .config import Config


def post(message: str, mention_user_id: str | None = None) -> bool:
    """Post a message to the shared feed. Prefixes `<@UID> — ` for mentions.
    Returns True on success, False on failure or no webhook configured."""
    try:
        cfg = Config()
    except SystemExit:
        return False
    url = cfg.secret("slack_webhook")
    if not url:
        return False
    text = message
    if mention_user_id:
        text = f"<@{mention_user_id}> — {message}"
    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except urllib.error.URLError as e:
        print(f"warning: slack post failed: {e}", file=sys.stderr)
        return False
