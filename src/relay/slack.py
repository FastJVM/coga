"""Compatibility shim for the old `relay.slack` import path.

New code should import from `relay.notification`.
"""

from __future__ import annotations

from relay.notification import *  # noqa: F403
from relay.notification import __all__ as __all__
from relay.notification.slack import mention as _mention
from relay.notification.slack import requests
