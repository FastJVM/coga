"""Slack webhook response classification shared by live post and validate."""

from __future__ import annotations

from typing import Literal

SlackResponseStatus = Literal["live", "revoked", "unreachable"]


def classify_slack_response(status_code: int, text: str) -> tuple[SlackResponseStatus, str]:
    """Classify Slack webhook responses using the validator's existing contract."""
    body = text.strip()[:200]
    detail = f"HTTP {status_code}: {body!r}"
    if status_code == 404 or "no_service" in body:
        return "revoked", detail
    if 200 <= status_code < 500:
        return "live", detail
    return "unreachable", detail


__all__ = ["SlackResponseStatus", "classify_slack_response"]
