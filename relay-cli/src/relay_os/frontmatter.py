"""YAML frontmatter parsing and writing for ticket.md and SKILL.md files.

Stub. Full implementation lands in ticket FJVM-1291.

Expected surface (tentative):

    def read(path: Path) -> tuple[dict, str]        # (frontmatter, body)
    def write(path: Path, frontmatter: dict, body: str) -> None
    def parse_step_field(s: str) -> tuple[int | None, str | None]
"""
