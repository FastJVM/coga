"""The Python-version guard in `relay/__init__.py`.

Relay targets 3.11+ and imports the stdlib `tomllib`. The guard turns the
cryptic `ModuleNotFoundError: No module named 'tomllib'` an older interpreter
would raise deep in an import chain into one actionable message, raised the
moment the package is imported.
"""

from __future__ import annotations

import pytest

from relay import _require_supported_python


@pytest.mark.parametrize("version", [(3, 9, 0), (3, 10, 9), (3, 0), (2, 7, 18)])
def test_guard_rejects_old_python(version):
    with pytest.raises(RuntimeError, match=r"Relay requires Python 3\.11 or newer"):
        _require_supported_python(version)


def test_guard_message_names_the_actual_version():
    with pytest.raises(RuntimeError, match=r"this interpreter is Python 3\.9"):
        _require_supported_python((3, 9, 7))


@pytest.mark.parametrize("version", [(3, 11, 0), (3, 12, 5), (3, 13, 1), (4, 0, 0)])
def test_guard_allows_supported_python(version):
    # Must not raise.
    _require_supported_python(version)
