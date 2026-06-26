"""Compatibility shim for the old `coga.slack` import path.

New code should import from `coga.notification`.
"""

from __future__ import annotations

from coga.notification import *  # noqa: F403
from coga.notification import __all__ as __all__
from coga.notification.slack import mention as _mention
from coga.notification.slack import requests
