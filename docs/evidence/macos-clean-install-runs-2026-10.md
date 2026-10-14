# macOS clean-install runs — 2026-09-30 and 2026-10-01

Dated run observations moved out of the
[macOS AWS runbook](../contexts/coga/testing/clean-install/macos-aws/SKILL.md)
and [`coga/install`](../contexts/coga/install/SKILL.md) on 2026-10-13, so the
runbook states procedure only. Point-in-time and machine-specific.

- **2026-09-30:** the AMI's CLT receipts did not stop `softwareupdate` from
  offering the Command Line Tools again.
- **2026-10-01:** the run reused dedicated host `h-0833c01ac15e645ac` through a
  temporary, untracked copy of `aws-mac.sh`, with separate owner approval; the
  new provision's standard `teardown` released it.
- **2026-10-01:** an earlier walk that resolved the PyPI `0.0.1` placeholder on
  the system Python 3.9 was set aside as not evidence for the 3.11 floor.
- **2026-10-01:** the walk reproduced the SSH error on a fresh macOS 27 host;
  the dialog path was not exercised.
