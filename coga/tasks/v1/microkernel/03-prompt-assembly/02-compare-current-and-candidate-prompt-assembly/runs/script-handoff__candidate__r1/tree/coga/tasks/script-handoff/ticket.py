from __future__ import annotations
import os
from pathlib import Path

task = Path(os.environ["COGA_TASK_DIR"])
(task / "prepared.txt").write_text("prepared\n", encoding="utf-8")
path = Path(os.environ["COGA_TASK_TICKET"])
text = path.read_text(encoding="utf-8")
text = text.replace("No work performed yet.", "Script phase succeeded once; prepared.txt contains prepared. Agent work remains in this step.")
path.write_text(text, encoding="utf-8")
