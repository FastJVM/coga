"""Slack webhook response classification shared by live post and validate."""

from __future__ import annotations

import re
from typing import Literal

import requests

SlackResponseStatus = Literal["live", "revoked", "unreachable"]

_SLACK_WEBHOOK_PATH_RE = re.compile(
    r"(?:https?://hooks\.slack(?:-gov)?\.com)?/services/\S+",
    re.IGNORECASE,
)
_DNS_FAILURE_HINTS = (
    "nameresolutionerror",
    "name resolution",
    "failed to resolve",
    "name or service not known",
    "getaddrinfo failed",
    "nodename nor servname",
)


def redact_slack_webhook_credentials(text: str) -> str:
    """Remove full or relative Slack incoming-webhook credential paths."""
    return _SLACK_WEBHOOK_PATH_RE.sub("[redacted Slack webhook]", text)


def format_slack_request_error(exc: requests.RequestException) -> str:
    """Return useful request-failure context without rendering request data.

    Requests and urllib3 may include the full requested URL in an exception's
    string representation. Slack incoming-webhook credentials live in that URL,
    so this boundary uses exception types and message hints only to select a
    fixed, non-secret category. The original message never crosses into a Coga
    diagnostic surface.
    """
    class_name = type(exc).__name__
    try:
        hint = str(exc).casefold()
    except Exception:
        hint = ""

    if isinstance(exc, requests.exceptions.ProxyError):
        category = "proxy connection failure"
    elif isinstance(exc, requests.exceptions.SSLError):
        category = "TLS/SSL failure"
    elif isinstance(exc, requests.exceptions.Timeout):
        category = "request timed out"
    elif any(token in hint for token in _DNS_FAILURE_HINTS):
        category = "DNS/name-resolution failure"
    elif "proxy" in hint:
        category = "proxy connection failure"
    elif any(token in hint for token in ("tls", "ssl", "certificate")):
        category = "TLS/SSL failure"
    elif "timed out" in hint or "timeout" in hint:
        category = "request timed out"
    elif isinstance(exc, requests.exceptions.ConnectionError):
        category = "connection failure"
    else:
        category = "request failure"

    return f"{class_name}: {category}"


def classify_slack_response(status_code: int, text: str) -> tuple[SlackResponseStatus, str]:
    """Classify Slack webhook responses using the validator's existing contract."""
    body = redact_slack_webhook_credentials(text.strip())[:200]
    detail = f"HTTP {status_code}: {body!r}"
    if status_code == 404 or "no_service" in body:
        return "revoked", detail
    if 200 <= status_code < 500:
        return "live", detail
    return "unreachable", detail


__all__ = [
    "SlackResponseStatus",
    "classify_slack_response",
    "format_slack_request_error",
    "redact_slack_webhook_credentials",
]
