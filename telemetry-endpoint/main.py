"""GCP relay for Coga's anonymous install telemetry.

A single Cloud Functions (gen2) HTTP handler. It accepts the three-field ping
the client sends, forwards a one-line message to internal Slack via an incoming
webhook held server-side, and returns `204`. There is no datastore — at ~100
users the Slack channel is the record.

No-PII controls (both load-bearing — see README.md):

- **Never reads the client IP.** The handler does not touch
  `X-Forwarded-For` / `request.remote_addr` / any IP header. The request access
  log's `remoteIp` is separately suppressed by a Cloud Logging exclusion filter
  applied in `deploy.sh`.
- **Forwards only the three known fields.** Any extra key in the POST body is
  ignored and never forwarded — belt-and-suspenders on the no-PII line, even if
  a future client (or an attacker) adds fields.

Robustness: the handler returns `204` on *every* path, including malformed
input or a Slack error, logging the problem server-side. The client ignores the
body, so a non-2xx would only cause confusing client-side "failure" noise for
no benefit; a duplicate ping is a harmless duplicate Slack line.
"""

from __future__ import annotations

import os
import re

import functions_framework
import requests

# The internal Slack incoming webhook. Provided to the function as an env var,
# wired from a Secret Manager secret by `deploy.sh` — never shipped in the
# client, never in this source.
_SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"

# Shape guards for the three accepted fields. `instance_id` must look like a
# uuid4; `last_run` must be a bare `YYYY-MM-DD` date. Anything else is dropped.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_SLACK_TIMEOUT_SECONDS = 5


def _clean_payload(data: object) -> dict | None:
    """Return the three validated fields, or None if the body is not a valid ping.

    Only `instance_id`, `tickets_total`, `last_run` are read; every other key in
    `data` is ignored and never forwarded.
    """
    if not isinstance(data, dict):
        return None
    instance_id = data.get("instance_id")
    tickets_total = data.get("tickets_total")
    last_run = data.get("last_run")
    if not (isinstance(instance_id, str) and _UUID_RE.match(instance_id)):
        return None
    # bool is an int subclass — exclude it explicitly so `true` is not a count.
    if isinstance(tickets_total, bool) or not isinstance(tickets_total, int):
        return None
    if tickets_total < 0:
        return None
    if not (isinstance(last_run, str) and _DATE_RE.match(last_run)):
        return None
    return {
        "instance_id": instance_id,
        "tickets_total": tickets_total,
        "last_run": last_run,
    }


def _post_to_slack(payload: dict) -> None:
    webhook = os.environ.get(_SLACK_WEBHOOK_ENV, "").strip()
    if not webhook:
        print("telemetry: no SLACK_WEBHOOK_URL configured — dropping ping")
        return
    text = (
        f"ping: instance={payload['instance_id']} "
        f"tickets={payload['tickets_total']} "
        f"last_run={payload['last_run']}"
    )
    resp = requests.post(webhook, json={"text": text}, timeout=_SLACK_TIMEOUT_SECONDS)
    if not 200 <= resp.status_code < 300:
        print(f"telemetry: Slack returned {resp.status_code}")


@functions_framework.http
def telemetry(request):
    """HTTP entry point. Always returns `204`; never reads the client IP."""
    try:
        payload = _clean_payload(request.get_json(silent=True))
        if payload is None:
            print("telemetry: ignoring malformed ping")
        else:
            _post_to_slack(payload)
    except Exception as exc:  # never surface a 5xx to anonymous clients
        print(f"telemetry: error handling ping: {exc}")
    return ("", 204)
