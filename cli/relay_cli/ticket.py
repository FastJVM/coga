"""Parse and write ticket.md files. Frontmatter is YAML."""
import re
from pathlib import Path

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "error: Relay requires PyYAML. Install with: pip install pyyaml"
    ) from e


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


class Ticket:
    def __init__(self, path: Path):
        self.path = Path(path)
        text = self.path.read_text()
        m = FRONTMATTER_RE.match(text)
        if not m:
            raise SystemExit(f"error: {self.path}: no YAML frontmatter found")
        self.frontmatter = yaml.safe_load(m.group(1)) or {}
        self.body = m.group(2)

    def save(self):
        fm = yaml.safe_dump(
            self.frontmatter, sort_keys=False, default_flow_style=False
        ).rstrip()
        self.path.write_text(f"---\n{fm}\n---\n{self.body}")

    # --- Identity ---

    @property
    def dir(self) -> Path:
        return self.path.parent

    @property
    def slug(self) -> str:
        return self.dir.name

    @property
    def id(self) -> str:
        m = re.match(r"^(\d+)", self.slug)
        return m.group(1) if m else self.slug

    # --- Frontmatter accessors ---

    @property
    def title(self):
        return self.frontmatter.get("title", "")

    @property
    def status(self):
        return self.frontmatter.get("status", "")

    @property
    def mode(self):
        return self.frontmatter.get("mode", "interactive")

    @property
    def owner(self):
        return self.frontmatter.get("owner")

    @property
    def assignee(self):
        return self.frontmatter.get("assignee")

    @property
    def step(self):
        return self.frontmatter.get("step")

    @property
    def workflow(self):
        return self.frontmatter.get("workflow")

    @property
    def contexts(self):
        return self.frontmatter.get("contexts") or []


def parse_step_field(s):
    """'1 (implement)' -> (1, 'implement'). Returns (None, None) if invalid."""
    if not s:
        return None, None
    m = re.match(r"^\s*(\d+)\s*\((.+)\)\s*$", s)
    if not m:
        return None, None
    return int(m.group(1)), m.group(2)
