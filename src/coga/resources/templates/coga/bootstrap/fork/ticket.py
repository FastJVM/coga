"""`coga fork` / `coga fork-copy` — find packaged behavior and fork it locally.

The script half of the stateless `bootstrap/fork` command ticket; `ticket.md`
beside it owns the contract. `inspect` runs under read-only dispatch and must
write nothing; `copy` runs under ordinary launch. Selection is always asked of
the shared resolvers; this script only computes override destinations from the
same path helpers and never imports a job implementation.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import shlex
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import coga
from coga.aliases import BUILTIN_COMMANDS, DEFAULT_ALIASES
from coga.atomicio import atomic_write_bytes
from coga.config import Config, ConfigError, load_config
from coga.paths import (
    IGNORABLE_OVERRIDE_ENTRIES,
    RESOURCE_NAMES,
    LocalOverrideError,
    RepoResourceUnreadable,
    bootstrap_context_dir,
    bootstrap_path,
    bootstrap_skill_dir,
    bootstrap_workflow_path,
    local_bootstrap_path,
    packaged_template_path,
    resolve_context_path,
    resolve_resource_path,
    resolve_skill_path,
    resolve_workflow_path,
    resource_override_path,
    skill_dir,
    workflow_path,
)
from coga.recurring import (
    ORIGIN_LOCAL,
    SELECTION_ENABLED,
    packaged_recurring_dir,
    resolve_template_source,
)
from coga.recurring_state import (
    CARRIER,
    CARRIER_PREFIX,
    INCOMPLETE,
    RUNTIME_STATE_FILES,
    active_parent_dir,
    inspect_parent_dir,
    parked_parent_dir,
)
from coga.taskfile import TaskFileError, read_blackboard, with_blackboard
from coga.tasks import (
    BootstrapOverrideError,
    TaskNotFoundError,
    read_ticket,
    resolve_bootstrap,
    resolve_task,
)
from coga.ticket import TicketError
from coga.workflow import Workflow, WorkflowError


KINDS = ("workflow", "skill", "context", "bootstrap", "recurring", "resource")
DEFINITION_FILE = {
    "workflow": None, "resource": None,
    "skill": "SKILL.md", "context": "SKILL.md",
    "bootstrap": "ticket.md", "recurring": "ticket.md",
}
KERNEL = "kernel primitive (not an editable ticket)"
STOCK = "stock"
IDENTICAL = "fork (identical to installed package)"
MODIFIED = "fork (modified)"
LOCAL_ONLY = "local only"
# `coga launch` options that consume the next token.
_LAUNCH_VALUE_OPTIONS = {"--agent", "--idle-timeout", "--max-session"}


class TargetError(Exception):
    """The target is unknown or ambiguous; `checked` lists what was tried."""

    def __init__(self, message: str, checked: list[str]) -> None:
        super().__init__(message)
        self.checked = checked


@dataclass
class Record:
    kind: str
    ref: str
    state: str
    origin: str | None = None
    selected: str | None = None
    packaged: str | None = None
    override: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    script: dict[str, object] | None = None
    return_to_stock: list[str] = field(default_factory=list)

    @property
    def typed(self) -> str:
        return f"{self.kind}:{self.ref}"

    @property
    def broken(self) -> bool:
        return self.state.startswith("broken:")


# --- ticket.py and edge-module classification (ast only) ---------------------


def _is_main_guard(node: ast.stmt) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name) and test.left.id == "__name__"
        and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _is_docstring(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
        and isinstance(node.value.value, str)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_bytes(), filename=str(path))


def _is_shim_guard(node: ast.stmt) -> bool:
    """Only a plain main() or raise SystemExit(main()) delegates completely."""
    if not _is_main_guard(node) or node.orelse or len(node.body) != 1:
        return False
    statement = node.body[0]
    call = statement.value if isinstance(statement, ast.Expr) else None
    if isinstance(statement, ast.Raise) and statement.cause is None:
        outer = statement.exc
        if (isinstance(outer, ast.Call) and isinstance(outer.func, ast.Name)
                and outer.func.id == "SystemExit" and len(outer.args) == 1
                and not outer.keywords):
            call = outer.args[0]
    return (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            and call.func.id == "main" and not call.args and not call.keywords)


def classify_script(path: Path) -> dict[str, object]:
    """Classify a `ticket.py` without importing or running it."""
    try:
        tree = _parse(path)
    except (OSError, SyntaxError, ValueError) as exc:
        return {"path": str(path), "kind": "unparseable", "reason": str(exc)}
    edge_module = None
    shim = True
    for node in tree.body:
        if _is_docstring(node) or _is_shim_guard(node):
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        if (
            isinstance(node, ast.ImportFrom) and node.level == 0
            and (node.module or "").startswith("coga_edge.")
            and [(a.name, a.asname) for a in node.names] == [("main", None)]
            and edge_module is None
        ):
            edge_module = node.module
            continue
        shim = False
    if shim and edge_module is not None and any(_is_main_guard(n) for n in tree.body):
        return {"path": str(path), "kind": "edge shim", "module": edge_module}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "run_recipe":
                literal = next(
                    (a.value for a in node.args
                     if isinstance(a, ast.Constant) and isinstance(a.value, str)),
                    None,
                )
                if literal is not None:
                    return {"path": str(path), "kind": "recipe adapter", "recipe": literal}
    return {"path": str(path), "kind": "full script", "implementation": str(path)}


def edge_module_path(module: str) -> Path | None:
    """Locate an installed `coga_edge` submodule without importing it."""
    top, _, rest = module.partition(".")
    try:
        spec = importlib.util.find_spec(top)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    for location in spec.submodule_search_locations:
        candidate = Path(location, *rest.split(".")).with_suffix(".py")
        if candidate.is_file():
            return candidate
    return None


def inspect_edge_module(path: Path) -> dict[str, object]:
    """Shared-core dependencies and whether a single-file fork is complete."""
    try:
        tree = _parse(path)
    except (OSError, SyntaxError, ValueError) as exc:
        return {"path": str(path), "forkable": False, "causes": [f"unparseable: {exc}"],
                "core_dependencies": [], "other_dependencies": []}
    core: set[str] = set()
    other: set[str] = set()
    causes: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.ImportFrom):
            if node.level:
                causes.append(f"relative import (line {node.lineno})")
                continue
            names = [node.module or ""]
        elif isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        for name in names:
            top = name.split(".")[0]
            if top == "coga_edge":
                causes.append(f"imports {name} (line {node.lineno})")
            elif top == "coga":
                core.add(name)
            elif top not in sys.stdlib_module_names and top != "__future__":
                other.add(name)
    if not any(_is_main_guard(n) for n in tree.body):
        causes.append("no `if __name__ == \"__main__\":` guard")
    return {
        "path": str(path), "forkable": not causes, "causes": causes,
        "core_dependencies": sorted(core), "other_dependencies": sorted(other),
    }


def describe_script(path: Path) -> dict[str, object]:
    info = classify_script(path)
    if info["kind"] == "edge shim":
        module = str(info["module"])
        located = edge_module_path(module)
        if located is None:
            info["implementation"] = None
            info["forkable"] = False
            info["causes"] = [f"module {module} is not installed"]
        else:
            edge = inspect_edge_module(located)
            info["implementation"] = str(located)
            info.update({k: edge[k] for k in
                         ("forkable", "causes", "core_dependencies", "other_dependencies")})
    elif info["kind"] == "recipe adapter":
        info["implementation"] = f"kernel recipe {info['recipe']}"
        info["forkable"] = False
        info["causes"] = [f"kernel recipe {info['recipe']} (not forkable here)"]
    elif info["kind"] == "full script":
        info["forkable"] = True
    else:
        info["forkable"] = False
        info["causes"] = [str(info.get("reason"))]
    return info


# --- artifacts -----------------------------------------------------------------


def _skip(path: Path, root: Path, definition: str | None) -> bool:
    rel = path.relative_to(root)
    if any(part in IGNORABLE_OVERRIDE_ENTRIES for part in rel.parts):
        return True
    if definition is None:
        return False
    # A child directory holding its own definition is a nested ref.
    for parent in list(rel.parents)[:-1]:
        if (root / parent / definition).is_file():
            return True
    return False


def artifact_files(root: Path, definition: str | None) -> dict[str, bytes]:
    """{posix relpath: bytes} of one artifact (a file, or its directory)."""
    if definition is None:
        return {root.name: root.read_bytes()} if root.is_file() else {}
    if not root.is_dir():
        return {}
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not _skip(path, root, definition):
            out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


def planned_copy(kind: str, packaged: Path) -> tuple[dict[str, bytes], str | None]:
    """What `fork-copy` writes from the package, and the implementation note.

    The note is None when an edge shim was expanded to its real module.
    """
    files = artifact_files(packaged, DEFINITION_FILE[kind])
    note = None
    if "ticket.py" in files and kind in {"bootstrap", "recurring"}:
        info = describe_script(packaged / "ticket.py")
        if info["kind"] == "edge shim" and info.get("forkable"):
            files["ticket.py"] = Path(str(info["implementation"])).read_bytes()
            note = f"ticket.py is the implementation, copied from {info['implementation']}"
        elif info["kind"] != "full script":
            causes = "; ".join(str(c) for c in info.get("causes") or [])
            note = f"implementation not forked: {causes or info['kind']}"
    return files, note


def _above_fence(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="replace")
    try:
        return with_blackboard(text, "").encode("utf-8")
    except TaskFileError:
        return data


def fork_state(kind: str, local: Path, packaged: Path | None) -> str:
    if packaged is None or not packaged.exists():
        return LOCAL_ONLY
    expected, _ = planned_copy(kind, packaged)
    actual = artifact_files(local, DEFINITION_FILE[kind])
    if kind == "recurring":
        for name in RUNTIME_STATE_FILES:
            actual.pop(name, None)
        # The blackboard is state, not definition.
        for files in (expected, actual):
            if "ticket.md" in files:
                files["ticket.md"] = _above_fence(files["ticket.md"])
    return IDENTICAL if expected == actual else MODIFIED


def return_to_stock(kind: str, override: Path) -> list[str]:
    if kind in {"workflow", "resource"}:
        return [f"delete {override}"]
    if kind in {"skill", "context", "bootstrap"}:
        return [f"delete the directory {override} (keep any nested definition "
                "directories it holds; they are separate refs)"]
    header = ", ".join(f"`{line}`" if line else "an empty line"
                       for line in CARRIER_PREFIX.split("\n"))
    return [
        f"in {override / 'ticket.md'}, replace everything up to and including the "
        f"blackboard fence with the exact carrier header lines {header} "
        "(coga/recurring/templates), keeping the blackboard region after the "
        "fence byte-for-byte",
        f"keep runtime state ({', '.join(sorted(RUNTIME_STATE_FILES))}); delete every "
        f"other file in {override}",
        "frozen periods keep their own script until they finish",
    ]


# --- definition records --------------------------------------------------------


def _ref_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def _ticket_references(path: Path, record: Record) -> list[str]:
    try:
        from coga.ticket import Ticket
        fm = Ticket.read(path).frontmatter
    except (OSError, UnicodeError, TicketError) as exc:
        record.state = f"broken: {exc}"
        return []
    refs = []
    workflow = fm.get("workflow")
    if isinstance(workflow, str):
        refs.append(f"workflow:{workflow}")
    refs += [f"skill:{s}" for s in _ref_list(fm.get("skills"))]
    refs += [f"context:{c}" for c in _ref_list(fm.get("contexts"))]
    return refs


def _workflow_details(path: Path, record: Record) -> None:
    try:
        workflow = Workflow.load(path)
    except WorkflowError as exc:
        if record.origin == "local":
            record.state = f"broken: {exc}"
        else:
            record.details["error"] = str(exc)
        return
    record.details["steps"] = [
        {"name": s.name, "skills": list(s.skills), "checkout": s.checkout,
         "assignee": s.assignee, "requires": s.requires}
        for s in workflow.steps
    ]
    for step in workflow.steps:
        record.references += [f"skill:{s}" for s in step.skills
                              if f"skill:{s}" not in record.references]


def definition_record(cfg: Config, kind: str, ref: str) -> Record | None:
    """Report one definition, or None when nothing (local or package) exists."""
    record = Record(kind=kind, ref=ref, state=STOCK)
    if kind == "workflow":
        override, packaged = workflow_path(cfg, ref), bootstrap_workflow_path(cfg, ref)
        try:
            selected = resolve_workflow_path(cfg, ref)
        except WorkflowError as exc:
            selected, record.state = override, f"broken: {exc}"
        if not selected.exists() and not selected.is_symlink():
            return None
    elif kind == "skill":
        override, packaged = skill_dir(cfg, ref), bootstrap_skill_dir(cfg, ref)
        try:
            found = resolve_skill_path(cfg, ref)
        except LocalOverrideError as exc:
            found, record.state = override / "SKILL.md", f"broken: {exc}"
        if found is None:
            return None
        selected = found.parent
    elif kind == "context":
        override, packaged = cfg.contexts_root / ref, bootstrap_context_dir(cfg, ref)
        try:
            found = resolve_context_path(cfg, ref)
        except ConfigError as exc:
            found, record.state = override / "SKILL.md", f"broken: {exc}"
        if found is None:
            return None
        selected = found.parent
    elif kind == "bootstrap":
        override, packaged = local_bootstrap_path(cfg, ref), bootstrap_path(cfg, ref)
        try:
            selected = resolve_bootstrap(cfg, ref).path
        except BootstrapOverrideError as exc:
            selected, record.state = override, f"broken: {exc}"
        except TaskNotFoundError:
            return None
    elif kind == "recurring":
        override, packaged = active_parent_dir(cfg, ref), packaged_recurring_dir() / ref
        source = resolve_template_source(cfg, ref)
        parent = inspect_parent_dir(source.state_dir)
        if source.definition_dir is None and source.error is None and parent.kind == "absent":
            return None
        selected = source.definition_dir or override
        record.origin = source.origin
        record.details["selection"] = source.selection
        if source.reason:
            record.details["selection reason"] = source.reason
        record.details["state carrier"] = str(source.state_dir / "ticket.md")
        record.details["state kind"] = parent.kind
        if source.error is not None:
            record.state = f"broken: {source.error}"
    elif kind == "resource":
        if ref not in RESOURCE_NAMES:
            return None
        override = resource_override_path(cfg, ref)
        packaged = packaged_template_path().parent.parent / ref
        try:
            local = resolve_resource_path(cfg, ref)
        except RepoResourceUnreadable as exc:
            local, record.state = override, f"broken: {exc}"
        selected = local or packaged
    else:  # pragma: no cover - guarded by callers
        raise ValueError(kind)

    if not packaged.exists():
        packaged = None
    record.override = str(override)
    record.packaged = str(packaged) if packaged else None
    record.selected = str(selected)
    if record.origin is None:
        record.origin = "local" if Path(selected) == override else "package"
    if record.origin == ORIGIN_LOCAL and not record.broken:
        # For recurring, the selected definition may be a parked `_<name>/`.
        record.state = fork_state(kind, Path(selected), packaged)
    if record.origin == ORIGIN_LOCAL and record.state != STOCK:
        record.return_to_stock = return_to_stock(kind, Path(selected))

    if kind == "workflow" and not record.broken:
        _workflow_details(Path(selected), record)
    if kind in {"bootstrap", "recurring"} and not record.broken:
        record.references += _ticket_references(Path(selected) / "ticket.md", record)
        script = Path(selected) / "ticket.py"
        if script.is_file():
            record.script = describe_script(script)
    return record


def kernel_record(kind: str, name: str) -> Record:
    package = Path(coga.__file__).parent
    if kind == "recipe":
        from coga.runner import RECIPES

        module = RECIPES[name].__module__
        path = package.joinpath(*module.split(".")[1:]).with_suffix(".py")
    else:
        module = f"coga.commands.{name}"
        path = package / "commands" / f"{name}.py"
    return Record(kind=kind, ref=name, state=KERNEL, origin="package",
                  selected=str(path), details={"module": module})


def task_record(cfg: Config, slug: str) -> Record:
    ref = resolve_task(cfg, slug)
    record = Record(kind="task", ref=ref.id_slug, state="task (not forkable)",
                    selected=str(ref.ticket_path))
    try:
        fm = read_ticket(ref).frontmatter
    except (OSError, UnicodeError, TicketError) as exc:
        record.state = f"broken: {exc}"
        return record
    frozen = fm.get("workflow")
    if isinstance(frozen, dict):
        record.details["frozen workflow"] = frozen.get("name")
        record.details["frozen steps"] = [
            {k: s.get(k) for k in ("name", "skills", "checkout", "assignee", "requires")}
            for s in frozen.get("steps") or [] if isinstance(s, dict)
        ]
        for step in record.details["frozen steps"]:
            record.references += [f"skill:{s}" for s in _ref_list(step["skills"])]
        name = frozen.get("name")
        if isinstance(name, str):
            record.details["live workflow file"] = (
                f"{resolve_workflow_path(cfg, name)} "
                "(not used by this ticket's frozen snapshot)"
            )
    elif isinstance(frozen, str):
        record.details["draft workflow"] = frozen
        record.references.append(f"workflow:{frozen}")
    record.references += [f"skill:{s}" for s in _ref_list(fm.get("skills"))]
    record.references += [f"context:{c}" for c in _ref_list(fm.get("contexts"))]
    record.references = list(dict.fromkeys(record.references))
    if ref.task_dir is not None and (ref.task_dir / "ticket.py").is_file():
        record.script = describe_script(ref.task_dir / "ticket.py")
    return record


# --- target resolution ---------------------------------------------------------


def _parse_typed(text: str) -> tuple[str, str] | None:
    if text.startswith("bootstrap/"):
        return "bootstrap", text[len("bootstrap/"):]
    kind, sep, ref = text.partition(":")
    if sep and kind in KINDS + ("task",) and ref:
        return kind, ref
    return None


def _follow_alias(cfg: Config, expansion: str) -> tuple[str, list[Record]]:
    tokens = shlex.split(expansion)
    head, rest = tokens[0], tokens[1:]
    if head == "launch":
        target = None
        skip = False
        for token in rest:
            if skip:
                skip = False
            elif token == "--":
                break
            elif token in _LAUNCH_VALUE_OPTIONS:
                skip = True
            elif not token.startswith("-"):
                target = token
                break
        if target is None:
            return "launch with no target", [kernel_record("command", "launch")]
        if target.startswith("bootstrap/"):
            return f"bootstrap ticket {target}", _expand(cfg, "bootstrap", target[10:])
        return f"task {target}", _expand(cfg, "task", target)
    if head == "recurring" and rest[:1] == ["launch"] and len(rest) > 1:
        return f"recurring job {rest[1]}", _expand(cfg, "recurring", rest[1])
    if head == "run" and rest:
        from coga.runner import RECIPES

        if rest[0] in RECIPES:
            return f"kernel recipe {rest[0]}", [kernel_record("recipe", rest[0])]
    return f"kernel primitive {head}", [kernel_record("command", head)]


def _expand(cfg: Config, kind: str, ref: str) -> list[Record]:
    """A record plus every definition it references, transitively."""
    if kind == "task":
        try:
            first = task_record(cfg, ref)
        except TaskNotFoundError as exc:
            raise TargetError(str(exc), [f"task ref {ref!r}: {exc}"]) from exc
    else:
        found = definition_record(cfg, kind, ref)
        if found is None:
            raise TargetError(
                f"no {kind} {ref!r} found", [f"{kind} {ref!r}: {_where(cfg, kind, ref)}"],
            )
        first = found
    out, seen, queue = [first], {first.typed}, list(first.references)
    while queue:
        typed = queue.pop(0)
        if typed in seen:
            continue
        seen.add(typed)
        k, _, r = typed.partition(":")
        record = definition_record(cfg, k, r)
        if record is None:
            record = Record(kind=k, ref=r, state=f"broken: unresolved ({_where(cfg, k, r)})")
        out.append(record)
        queue += record.references
    return out


def _where(cfg: Config, kind: str, ref: str) -> str:
    paths = {
        "workflow": lambda: (workflow_path(cfg, ref), bootstrap_workflow_path(cfg, ref)),
        "skill": lambda: (skill_dir(cfg, ref), bootstrap_skill_dir(cfg, ref)),
        "context": lambda: (cfg.contexts_root / ref, bootstrap_context_dir(cfg, ref)),
        "bootstrap": lambda: (local_bootstrap_path(cfg, ref), bootstrap_path(cfg, ref)),
        "recurring": lambda: (active_parent_dir(cfg, ref), packaged_recurring_dir() / ref),
        "resource": lambda: (resource_override_path(cfg, ref),
                             packaged_template_path().parent.parent / ref),
    }[kind]()
    return "checked " + ", ".join(str(p) for p in paths)


@dataclass
class Resolution:
    target: str
    via: list[str]
    records: list[Record]


def resolve(cfg: Config, text: str) -> Resolution:
    typed = _parse_typed(text)
    if typed is not None:
        return Resolution(text, [], _expand(cfg, *typed))
    aliases = {**DEFAULT_ALIASES, **cfg.aliases}
    if text in aliases:
        source = "coga.toml [aliases]" if text in cfg.aliases else "default alias"
        expansion = aliases[text]
        followed, records = _follow_alias(cfg, expansion)
        via = [f"alias {text} = {expansion!r} ({source}) -> {followed}"]
        return Resolution(text, via, records)
    if text in BUILTIN_COMMANDS:
        return Resolution(text, [f"built-in command {text}"], [kernel_record("command", text)])
    checked = [f"alias: none of {len(aliases)} effective aliases",
               f"built-in command: not one of {len(BUILTIN_COMMANDS)}"]
    try:
        return Resolution(text, [], _expand(cfg, "task", text))
    except TargetError as exc:
        checked += exc.checked
    matches = []
    for kind in KINDS:
        try:
            if kind == "bootstrap" and "/" in text:
                raise TargetError("", [])
            matches.append((kind, _expand(cfg, kind, text)))
        except TargetError as exc:
            checked += exc.checked
    if len(matches) == 1:
        return Resolution(text, [f"{matches[0][0]} {text}"], matches[0][1])
    if matches:
        kinds = ", ".join(f"{k}:{text}" for k, _ in matches)
        raise TargetError(f"ambiguous target {text!r}: matches {kinds}", checked)
    raise TargetError(f"unknown target {text!r}", checked)


# --- rendering -----------------------------------------------------------------


def _detail_lines(key: str, value: object) -> list[str]:
    if key in {"steps", "frozen steps"} and isinstance(value, list):
        lines = [f"    {key}:"]
        for step in value:
            parts = [f"skills: {', '.join(_ref_list(step.get('skills'))) or '-'}"]
            parts += [f"{k}: {step[k]}" for k in ("checkout", "assignee", "requires")
                      if step.get(k)]
            lines.append(f"      {step.get('name')} — {'; '.join(parts)}")
        return lines
    return [f"    {key}: {value}"]


def render_text(resolution: Resolution) -> str:
    lines = [f"coga fork {resolution.target}"]
    lines += [f"  {v}" for v in resolution.via]
    for record in resolution.records:
        lines.append("")
        lines.append(f"  {record.kind}: {record.ref}")
        lines.append(f"    state: {record.state}")
        for key, value in (("origin", record.origin), ("selected", record.selected),
                           ("packaged", record.packaged), ("local override", record.override)):
            if value is not None or key == "packaged" and record.override:
                lines.append(f"    {key}: {value if value is not None else 'none'}")
        for key, value in record.details.items():
            lines += _detail_lines(key, value)
        if record.script:
            script = record.script
            lines.append(f"    ticket.py: {script['kind']} ({script['path']})")
            if script.get("implementation"):
                lines.append(f"      implementation: {script['implementation']}")
            if script.get("core_dependencies"):
                lines.append("      shared-core dependencies: "
                             + ", ".join(script["core_dependencies"]))
            if script.get("other_dependencies"):
                lines.append("      other dependencies: "
                             + ", ".join(script["other_dependencies"]))
            if script.get("forkable") and script["kind"] == "edge shim":
                lines.append("      forkable: coga fork-copy writes this module as ticket.py")
            if not script.get("forkable"):
                lines.append("      not completely forkable: "
                             + "; ".join(str(c) for c in script.get("causes") or []))
        if record.references:
            lines.append(f"    references: {', '.join(record.references)}")
        if record.return_to_stock:
            lines.append("    return to stock:")
            lines += [f"      - {step}" for step in record.return_to_stock]
        elif record.state == STOCK and record.packaged:
            lines.append(f"    customize: coga fork-copy {record.typed}")
    return "\n".join(lines) + "\n"


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _record_json(record: Record) -> dict[str, object]:
    data = asdict(record)
    data["typed_ref"] = record.typed
    data["broken"] = record.broken
    return data


# --- copy ----------------------------------------------------------------------


@dataclass
class CopyResult:
    record: Record
    destination: Path
    written: list[str]
    note: str | None
    converted_carrier: bool


class CopyRefused(Exception):
    pass


def copy_definition(cfg: Config, record: Record) -> CopyResult:
    if record.kind not in KINDS:
        raise CopyRefused(f"{record.typed} is a {record.state}; only packaged "
                          "definitions can be forked")
    if record.packaged is None:
        raise CopyRefused(f"{record.typed} has no packaged definition to copy")
    if record.origin == "local" or record.broken:
        raise CopyRefused(f"{record.typed} is already a local override at {record.override}"
                          + (f" ({record.state})" if record.broken else ""))
    packaged, destination = Path(record.packaged), Path(str(record.override))
    files, note = planned_copy(record.kind, packaged)
    carrier = None
    if record.kind == "recurring":
        parked = parked_parent_dir(cfg, record.ref)
        if parked.exists() or parked.is_symlink():
            raise CopyRefused(f"recurring/{record.ref} is parked at {parked}; "
                              "rename it back or remove it before forking")
        parent = inspect_parent_dir(destination)
        if parent.kind == INCOMPLETE:
            raise CopyRefused(str(parent.problem))
        if parent.kind == CARRIER:
            carrier = read_blackboard(parent.ticket_path)
            files["ticket.md"] = with_blackboard(
                files["ticket.md"].decode("utf-8"), carrier,
            ).encode("utf-8")
    definition = DEFINITION_FILE[record.kind]
    targets = {rel: (destination / rel if definition else destination) for rel in files}
    conflicts = []
    for rel, path in targets.items():
        if carrier is not None and rel == "ticket.md":
            continue
        for candidate in [path, *path.parents]:
            if candidate == cfg.repo_root or candidate in cfg.repo_root.parents:
                break
            if candidate.is_symlink() or (candidate.exists() and
                                          (candidate == path or not candidate.is_dir())):
                conflicts.append(str(candidate))
                break
    if destination.is_symlink():
        conflicts.append(str(destination))
    if conflicts:
        raise CopyRefused("destination entries already exist:\n"
                          + "\n".join(f"  {c}" for c in sorted(set(conflicts))))
    def_name = definition or destination.name
    order = sorted(targets, key=lambda rel: (rel == def_name, rel))
    for rel in order:
        path = targets[rel]
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(path, files[rel])
        if os.name == "posix":
            source = packaged / rel if definition else packaged
            # Keep executable attachments usable without copying read-only
            # installation permissions into the editable repository fork.
            path.chmod(path.stat().st_mode | (source.stat().st_mode & 0o111))
    return CopyResult(record, destination, [str(targets[r]) for r in order],
                      note, carrier is not None)


def render_copy(cfg: Config, result: CopyResult, after: list[Record]) -> str:
    record = after[0]
    lines = [f"Forked {result.record.typed} to {result.destination}"]
    if result.converted_carrier:
        lines.append("  converted the state-only carrier; its blackboard and runtime "
                     "state are kept")
    lines.append("  wrote:")
    lines += [f"    {path}" for path in result.written]
    if result.note:
        lines.append(f"  {result.note}")
    edit = {
        "workflow": "the workflow file", "resource": "the resource file",
        "skill": "SKILL.md and its attachments", "context": "SKILL.md",
        "bootstrap": "ticket.md (contract) and ticket.py (script), if present",
        "recurring": "ticket.md above the blackboard fence, ticket.py and runbooks",
    }[record.kind]
    lines.append(f"  edit: {edit} under {result.destination}")
    if record.kind == "recurring":
        selection = record.details.get("selection")
        lines.append(f"  selection: recurring/{record.ref} is now {selection}")
        if selection == SELECTION_ENABLED:
            lines.append(f"  to keep it off, add `{record.ref} = false` under [jobs] in "
                         "recurring/jobs.toml")
    stock = [r for r in after[1:] if r.state == STOCK and r.packaged and r.kind in KINDS]
    if stock:
        lines.append("  referenced definitions still stock:")
        lines += [f"    coga fork-copy {r.typed}" for r in stock]
    if record.return_to_stock:
        lines.append("  return to stock:")
        lines += [f"    - {step}" for step in record.return_to_stock]
    return "\n".join(lines) + "\n"


# --- entry ---------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coga fork",
        description="Find where packaged behavior lives (inspect) or copy one "
        "packaged definition to its local override (copy).",
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode, help_text in (
        ("inspect", "report definitions, implementation and override paths (read-only)"),
        ("copy", "copy one packaged definition to its local override location"),
    ):
        command = sub.add_parser(mode, help=help_text, prog=f"coga fork {mode}")
        command.add_argument("target", help="typed ref (workflow:<ref>, skill:<ref>, "
                             "context:<ref>, bootstrap/<name>, recurring:<name>, "
                             "resource:<name>, task:<slug>) or an untyped word")
        command.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        cfg = load_config(require_user=False)
    except ConfigError as exc:
        print(f"coga fork: {exc}", file=sys.stderr)
        return 2
    try:
        resolution = resolve(cfg, args.target)
    except TargetError as exc:
        print(f"coga fork: {exc}", file=sys.stderr)
        for line in exc.checked:
            print(f"  checked {line}", file=sys.stderr)
        return 1
    if args.mode == "inspect":
        broken = [r for r in resolution.records if r.broken]
        if args.json:
            sys.stdout.write(render_json({
                "target": resolution.target, "via": resolution.via,
                "broken": bool(broken),
                "records": [_record_json(r) for r in resolution.records],
            }))
        else:
            sys.stdout.write(render_text(resolution))
        for record in broken:
            print(f"coga fork: {record.typed} is {record.state}", file=sys.stderr)
        return 1 if broken else 0
    primary = resolution.records[0]
    try:
        result = copy_definition(cfg, primary)
    except CopyRefused as exc:
        print(f"coga fork-copy: refused: {exc}", file=sys.stderr)
        return 1
    after = _expand(cfg, primary.kind, primary.ref)
    if args.json:
        sys.stdout.write(render_json({
            "target": resolution.target, "via": resolution.via,
            "destination": str(result.destination), "written": result.written,
            "implementation_note": result.note,
            "converted_carrier": result.converted_carrier,
            "records": [_record_json(r) for r in after],
        }))
    else:
        sys.stdout.write(render_copy(cfg, result, after))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
