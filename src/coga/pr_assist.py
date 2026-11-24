"""Audit identity for an agent assisting on an owner-held step."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from coga.config import Config
from coga.repl_supervisor import ASSIST_AGENT_ENV, EXPECTED_TASK_ENV
from coga.tasks import TaskRef


@dataclass(frozen=True)
class AssistSession:
    agent: str


def assist_session_from_env(cfg: Config, ref: TaskRef) -> AssistSession | None:
    agent = os.environ.get(ASSIST_AGENT_ENV, "").strip()
    expected_task = os.environ.get(EXPECTED_TASK_ENV, "").strip()
    if agent not in cfg.agents or not expected_task:
        return None
    if Path(expected_task).resolve() != ref.path.resolve():
        return None
    return AssistSession(agent=agent)
