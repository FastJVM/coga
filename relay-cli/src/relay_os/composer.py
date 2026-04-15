"""Prompt composition for `relay launch`.

Stub. Full implementation lands in ticket FJVM-1293.

Assembles, in order: protocol → mode block → global rules → project
context → ticket contexts → inline ticket context → current step skill
→ blackboard. Writes the result to a temp file and returns the path.

Expected surface (tentative):

    def compose(cfg, ticket, project: str, mode: str) -> str
    def write_temp(prompt: str, task_id: str) -> Path
"""
