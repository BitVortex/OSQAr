#!/usr/bin/env python3
"""OSQAr command line interface.

Goals:
- Simple, dependency-free CLI (stdlib only)
- Scaffold a new OSQAr project from built-in example templates
- Wrap existing verification tooling (traceability + checksums)

This repository is a documentation boilerplate; the CLI is meant to speed up
common workflows for suppliers/integrators.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Dict

from tools.generate_checksums import cli as checksums_cli
from tools.code_trace_check import cli as code_trace_cli
from tools.traceability_check import cli as traceability_cli


TEMPLATES_BASIC: dict[str, Path] = {
    "c": Path("templates/basic/c"),
    "cpp": Path("templates/basic/cpp"),
    "python": Path("templates/basic/python"),
    "rust": Path("templates/basic/rust"),
}

TEMPLATE_BASIC_SHARED = Path("templates/basic/shared")

# Legacy templates: full example projects.
TEMPLATES_EXAMPLE: dict[str, Path] = {
    "c": Path("examples/c_hello_world"),
    "cpp": Path("examples/cpp_hello_world"),
    "python": Path("examples/python_hello_world"),
    "rust": Path("examples/rust_hello_world"),
}

# Used for CLI choices.
TEMPLATES: dict[str, Path] = dict(TEMPLATES_BASIC)


DEFAULT_BUILD_DIR = Path("_build/html")
DEFAULT_CHECKSUM_MANIFEST = Path("SHA256SUMS")
DEFAULT_TRACEABILITY_REPORT = Path("traceability_report.json")
DEFAULT_DOCTOR_REPORT = Path("doctor_report.json")
DEFAULT_PROJECT_METADATA = Path("osqar_project.json")
DEFAULT_WORKSPACE_CONFIG = Path("osqar_workspace.json")

_HOOK_DISABLE_ENV = "OSQAR_DISABLE_HOOKS"

_IGNORED_DIR_NAMES = {
    "_build",
    "build",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    ".git",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
    "dist",
}

_DEFAULT_TEST_REPORT_GLOBS = (
    "test_results.xml",
    "**/test_results.xml",
    "junit.xml",
    "**/junit.xml",
    "junit-*.xml",
    "**/junit-*.xml",
    "**/TEST-*.xml",
)


@dataclass(frozen=True)
class ShipmentProject:
    path: Path
    language: str


def _detect_language(project_dir: Path) -> str:
    # Heuristics only; do not require a specific template layout.
    if (project_dir / "Cargo.toml").is_file():
        return "rust"
    if (project_dir / "pyproject.toml").is_file() or (
        project_dir / "requirements.txt"
    ).is_file():
        return "python"
    for probe in (project_dir / "src", project_dir / "tests"):
        if probe.is_dir() and any(
            p.suffix == ".py" for p in probe.rglob("*") if p.is_file()
        ):
            return "python"
    if (project_dir / "CMakeLists.txt").is_file():
        # Try to disambiguate C vs C++ based on sources.
        src_root = project_dir / "src"
        if src_root.is_dir():
            has_cpp = any(
                p.suffix in {".cpp", ".cc", ".cxx"}
                for p in src_root.rglob("*")
                if p.is_file()
            )
            if has_cpp:
                return "cpp"
        return "c"
    return "unknown"


def _detect_shipment_language(shipment_dir: Path) -> str:
    """Best-effort language detection for a built shipment directory."""
    impl = (shipment_dir / "implementation").resolve()
    if impl.is_dir():
        return _detect_language(impl)
    return _detect_language(shipment_dir)


def _code_trace_test_dirs_for_shipment(
    shipment_dir: Path, *, language: str
) -> list[str]:
    """Pick test scan roots for code-trace.

    Most templates keep tests under `tests/`.
    Rust commonly embeds unit tests or test binaries under `src/`.
    """
    shipment_dir = shipment_dir.resolve()
    dirs: list[Path] = []

    tests_dir = shipment_dir / "tests"
    dirs.append(tests_dir)

    if language == "rust":
        # Rust test code often lives in `src/` (unit tests) or `src/bin/*`.
        dirs.append(shipment_dir / "implementation" / "src")

    return [str(d) for d in dirs]


def _is_shipment_project_dir(path: Path) -> bool:
    return (path / "conf.py").is_file() and (path / "index.rst").is_file()


def _iter_project_dirs(root: Path, *, recursive: bool) -> Iterable[Path]:
    root = root.resolve()

    if not root.is_dir():
        return

    if not recursive:
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name in _IGNORED_DIR_NAMES:
                continue
            yield child
        return

    # Recursive mode: find conf.py and treat its parent as a project root.
    for conf in sorted(root.rglob("conf.py")):
        project_dir = conf.parent
        # Skip common build/virtualenv roots early.
        if any(part in _IGNORED_DIR_NAMES for part in project_dir.parts):
            continue
        yield project_dir


def _default_shipment_dir(project_dir: Path) -> Path:
    return (project_dir / DEFAULT_BUILD_DIR).resolve()


def _run(cmd: list[str], *, cwd: Path, env: Optional[Dict[str, str]] = None) -> int:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        proc = subprocess.run(cmd, cwd=str(cwd), env=merged_env)
    except FileNotFoundError as exc:
        print(f"ERROR: command not found: {cmd[0]} ({exc})", file=sys.stderr)
        return 127
    return int(proc.returncode)


def _read_json_dict(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to parse JSON: {path} ({exc})", file=sys.stderr)
        return None
    return data if isinstance(data, dict) else None


def _read_project_config(
    project_dir: Path, *, explicit_path: Optional[str] = None
) -> dict:
    if explicit_path:
        cfg_path = Path(explicit_path).expanduser().resolve()
    else:
        cfg_path = (project_dir / DEFAULT_PROJECT_METADATA).resolve()
    return _read_json_dict(cfg_path) or {}


def _read_workspace_config(
    root_dir: Path, *, explicit_path: Optional[str] = None
) -> dict:
    if explicit_path:
        cfg_path = Path(explicit_path).expanduser().resolve()
    else:
        cfg_path = (root_dir / DEFAULT_WORKSPACE_CONFIG).resolve()
    return _read_json_dict(cfg_path) or {}


def _config_defaults_exclude(config: dict) -> list[str]:
    defaults = config.get("defaults") if isinstance(config, dict) else None
    if not isinstance(defaults, dict):
        return []
    ex = defaults.get("exclude")
    if isinstance(ex, list):
        return [str(x) for x in ex if isinstance(x, (str, int, float))]
    if isinstance(ex, str):
        return [ex]
    return []


def _hook_commands(config: dict, *, phase: str, event: str) -> list[str]:
    hooks = config.get("hooks") if isinstance(config, dict) else None
    if not isinstance(hooks, dict):
        return []

    bucket = hooks.get(phase)
    if not isinstance(bucket, dict):
        return []

    cmds = bucket.get(event)
    if cmds is None:
        return []
    if isinstance(cmds, str):
        return [cmds]
    if isinstance(cmds, list):
        return [str(c) for c in cmds if isinstance(c, (str, int, float))]
    return []


def _hooks_enabled(args: argparse.Namespace) -> bool:
    if os.environ.get(_HOOK_DISABLE_ENV):
        return False
    return not bool(getattr(args, "no_hooks", False))


def _run_command_string(command: str, *, cwd: Path, env: dict[str, str]) -> int:
    try:
        argv = shlex.split(str(command))
    except ValueError as exc:
        print(f"ERROR: invalid command string: {exc}", file=sys.stderr)
        return 2
    if not argv:
        print("ERROR: empty command", file=sys.stderr)
        return 2
    print(f"Running: {command}")
    return _run(argv, cwd=cwd, env=env)


def _git_source_date_epoch(project_dir: Path) -> Optional[str]:
    """Best-effort SOURCE_DATE_EPOCH from git history.

    Returns None if git is unavailable or the directory is not a git repo.
    """
    if shutil.which("git") is None:
        return None
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    epoch = (proc.stdout or "").strip()
    return epoch if epoch.isdigit() else None


def _reproducible_env(project_dir: Path, *, reproducible: bool) -> dict[str, str]:
    if not reproducible:
        return {}
    env: dict[str, str] = {
        "OSQAR_REPRODUCIBLE": "1",
    }
    if not os.environ.get("SOURCE_DATE_EPOCH"):
        epoch = _git_source_date_epoch(project_dir)
        if epoch:
            env["SOURCE_DATE_EPOCH"] = epoch
    return env


def _run_hooks(
    config: dict,
    *,
    args: argparse.Namespace,
    phase: str,
    event: str,
    cwd: Path,
    env: dict[str, str],
) -> int:
    if not _hooks_enabled(args):
        return 0
    cmds = _hook_commands(config, phase=phase, event=event)
    if not cmds:
        return 0
    print(f"Running {phase} hook(s) for {event}: {len(cmds)}")
    for cmd in cmds:
        rc = _run_command_string(cmd, cwd=cwd, env=env)
        if rc != 0:
            print(f"ERROR: hook failed (rc={rc}): {event}", file=sys.stderr)
            return int(rc)
    return 0


def _run_docs_build(project_dir: Path, output_dir: Path, *, config: dict) -> int:
    commands = config.get("commands") if isinstance(config, dict) else None
    cmd = commands.get("docs") if isinstance(commands, dict) else None
    if isinstance(cmd, str) and cmd.strip():
        env = {
            "OSQAR_PROJECT_DIR": str(project_dir.resolve()),
            "OSQAR_DOCS_OUTPUT": str(output_dir.resolve()),
        }
        return _run_command_string(str(cmd), cwd=project_dir, env=env)
    return _run_sphinx_build(project_dir, output_dir)


def _poetry_available() -> bool:
    return shutil.which("poetry") is not None


def _project_uses_poetry(project_dir: Path) -> bool:
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        content = pyproject.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    # Conservative: only opt into Poetry if it looks like a Poetry-managed project.
    return "[tool.poetry]" in content


def _run_sphinx_build(project_dir: Path, output_dir: Path) -> int:
    project_dir = project_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    # Prefer running Sphinx inside the *project's* Poetry environment.
    # This keeps dependencies locked per project (poetry.lock) and allows an installed
    # `osqar` to remain lightweight (no Sphinx required in the CLI environment).
    if _project_uses_poetry(project_dir) and _poetry_available():
        print("Using Poetry environment for docs build (poetry.lock)")
        cmd = [
            "poetry",
            "run",
            "python",
            "-m",
            "sphinx",
            "-b",
            "html",
            ".",
            str(output_dir),
        ]
        return _run(cmd, cwd=project_dir)

    # Fallback: run in the current interpreter environment.
    # Use `python -m sphinx` to avoid relying on a shell-resolved `sphinx-build`.
    cmd = [sys.executable, "-m", "sphinx", "-b", "html", ".", str(output_dir)]
    return _run(cmd, cwd=project_dir)


def _find_needs_json(shipment_dir: Path) -> Optional[Path]:
    candidate = shipment_dir / "needs.json"
    if candidate.is_file():
        return candidate
    # Fallback: allow nested layouts.
    for p in shipment_dir.rglob("needs.json"):
        if p.is_file():
            return p
    return None


def _safe_rmtree(path: Path, *, dry_run: bool) -> None:
    path = path.resolve()
    if not path.exists():
        return
    # Safety: refuse to delete suspiciously short paths.
    if path == Path("/") or len(path.parts) < 3:
        raise ValueError(f"Refusing to remove unsafe path: {path}")

    if dry_run:
        print(f"DRY-RUN: would remove {path}")
        return
    shutil.rmtree(path)


def _iter_test_report_files(project_dir: Path, globs: tuple[str, ...]) -> list[Path]:
    # Deterministic, conservative search under project_dir.
    project_dir = project_dir.resolve()
    matches: set[Path] = set()

    for pattern in globs:
        for p in project_dir.glob(pattern):
            if not p.is_file():
                continue
            # Ignore generated/build outputs.
            if any(part in _IGNORED_DIR_NAMES for part in p.parts):
                continue
            matches.add(p.resolve())

    return sorted(matches)


def _copy_test_reports(
    project_dir: Path, shipment_dir: Path, *, dry_run: bool, globs: tuple[str, ...]
) -> int:
    reports = _iter_test_report_files(project_dir, globs)
    if not reports:
        print("No test report XML files found.")
        return 0

    shipment_dir = shipment_dir.resolve()
    shipment_dir.mkdir(parents=True, exist_ok=True)

    if len(reports) == 1:
        src = reports[0]
        dest = shipment_dir / src.name
        if dry_run:
            print(f"DRY-RUN: would copy {src} -> {dest}")
        else:
            shutil.copy2(src, dest)
        print(f"Copied test report: {src} -> {dest}")
        return 0

    dest_root = shipment_dir / "test_reports"
    if not dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)

    for src in reports:
        # Preserve relative path under project_dir to avoid collisions.
        rel = src.relative_to(project_dir).as_posix().replace("..", "__")
        dest = dest_root / rel
        if dry_run:
            print(f"DRY-RUN: would copy {src} -> {dest}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    print(f"Copied {len(reports)} test reports into: {dest_root}")
    return 0


def _copy_bundle_sources_and_reports(
    project_dir: Path, shipment_dir: Path, *, dry_run: bool
) -> None:
    """Copy non-doc evidence into a shipment directory.

    Goal: make a shipment a reviewable evidence bundle (docs + traceability + implementation
    + tests + analysis reports), not just a Sphinx HTML output directory.

    This is intentionally conservative and template-agnostic.
    """

    project_dir = project_dir.resolve()
    shipment_dir = shipment_dir.resolve()
    shipment_dir.mkdir(parents=True, exist_ok=True)

    impl_dir = shipment_dir / "implementation"
    tests_dir = shipment_dir / "tests"
    reports_dir = shipment_dir / "reports"

    if not dry_run:
        impl_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)

    def copy_file(src: Path, dest: Path) -> None:
        if not src.is_file():
            return
        if dry_run:
            print(f"DRY-RUN: would copy {src} -> {dest}")
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    def copy_tree(src_dir: Path, dest_dir: Path) -> None:
        if not src_dir.is_dir():
            return
        if dry_run:
            print(f"DRY-RUN: would copy tree {src_dir} -> {dest_dir}")
            return
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)

    # Implementation sources
    copy_tree(project_dir / "src", impl_dir / "src")
    copy_tree(project_dir / "include", impl_dir / "include")

    # Tests
    copy_tree(project_dir / "tests", tests_dir)

    # Build descriptors (helpful for audit/reproduction)
    for fname in (
        "osqar_project.json",
        "CMakeLists.txt",
        "Cargo.toml",
        "Cargo.lock",
        "pyproject.toml",
        "requirements.txt",
        "BUILD.bazel",
        "MODULE.bazel",
        ".bazelrc",
        "build-and-test.sh",
        "bazel-build-and-test.sh",
    ):
        copy_file(project_dir / fname, impl_dir / fname)

    # Project metadata at the shipment root (used by verify/doctor).
    copy_file(project_dir / "osqar_project.json", shipment_dir / "osqar_project.json")

    # Analysis / verification reports (best-effort)
    for fname in (
        "test_results.xml",
        "coverage_report.txt",
        "coverage.xml",
        "complexity_report.txt",
    ):
        copy_file(project_dir / fname, reports_dir / fname)

    # Convenience copies at the shipment root (for quick browsing / common expectations)
    for fname in (
        "test_results.xml",
        "coverage_report.txt",
        "coverage.xml",
        "complexity_report.txt",
    ):
        copy_file(project_dir / fname, shipment_dir / fname)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _set_nested_value(obj: dict, dotted_key: str, value: str) -> None:
    parts = [p for p in dotted_key.split(".") if p]
    if not parts:
        raise ValueError("Empty key")

    cur: dict = obj
    for part in parts[:-1]:
        nxt = cur.get(part)
        if nxt is None:
            nxt = {}
            cur[part] = nxt
        if not isinstance(nxt, dict):
            raise ValueError(f"Cannot set nested key under non-dict: {part}")
        cur = nxt

    cur[parts[-1]] = value


def _parse_kv(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Expected KEY=VALUE, got: {item}")
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            raise ValueError(f"Empty key in: {item}")
        out[k] = v
    return out


def _read_project_metadata(shipment_dir: Path) -> Optional[dict]:
    path = (shipment_dir / DEFAULT_PROJECT_METADATA).resolve()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - keep stdlib-only and robust
        print(
            f"WARNING: failed to read project metadata: {path} ({exc})", file=sys.stderr
        )
        return None


def _read_needs_summary_from_shipment(shipment_dir: Path) -> Optional[dict[str, int]]:
    needs_json = _find_needs_json(shipment_dir)
    if needs_json is None:
        return None

    try:
        data = json.loads(needs_json.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(
            f"WARNING: failed to parse needs.json: {needs_json} ({exc})",
            file=sys.stderr,
        )
        return None

    needs_list: list[dict] = []

    if isinstance(data, dict):
        if isinstance(data.get("needs"), list):
            needs_list = [n for n in data["needs"] if isinstance(n, dict)]
        elif isinstance(data.get("versions"), dict):
            versions = data.get("versions")
            current_version = data.get("current_version", "")
            if current_version in versions and isinstance(
                versions[current_version], dict
            ):
                v = versions[current_version]
                needs = v.get("needs")
                if isinstance(needs, list):
                    needs_list = [n for n in needs if isinstance(n, dict)]
                elif isinstance(needs, dict):
                    out: list[dict] = []
                    for need_id, need_data in needs.items():
                        if not isinstance(need_data, dict):
                            continue
                        if "id" not in need_data:
                            need_data = {"id": str(need_id), **need_data}
                        out.append(need_data)
                    needs_list = out
    elif isinstance(data, list):
        needs_list = [n for n in data if isinstance(n, dict)]

    if not needs_list:
        return None

    ids = [str(n.get("id", "")) for n in needs_list]
    return {
        "needs_total": sum(1 for i in ids if i),
        "req_total": sum(1 for i in ids if i.startswith("REQ_")),
        "arch_total": sum(1 for i in ids if i.startswith("ARCH_")),
        "test_total": sum(1 for i in ids if i.startswith("TEST_")),
        "code_total": sum(1 for i in ids if i.startswith(("CODE_", "IMPL_"))),
    }


def _write_project_metadata(
    shipment_dir: Path, metadata: dict, *, overwrite: bool, dry_run: bool
) -> int:
    shipment_dir = shipment_dir.resolve()
    shipment_dir.mkdir(parents=True, exist_ok=True)
    path = shipment_dir / DEFAULT_PROJECT_METADATA
    if path.exists() and not overwrite:
        print(
            f"ERROR: metadata already exists (use --overwrite): {path}", file=sys.stderr
        )
        return 2

    payload = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    if dry_run:
        print(f"DRY-RUN: would write metadata: {path}")
        return 0
    path.write_text(payload, encoding="utf-8")
    print(f"Wrote metadata: {path}")
    return 0


def _print_open_hint(path: Path) -> None:
    path = path.resolve()
    if sys.platform == "darwin":
        print(f"TIP: open {path}")
    elif sys.platform.startswith("linux"):
        print(f"TIP: xdg-open {path}")
    elif os.name == "nt":
        print(f"TIP: start {path}")
    else:
        print(f"TIP: open the file in your editor: {path}")


def _copytree(src: Path, dst: Path, *, force: bool) -> None:
    if dst.exists():
        if not force:
            raise FileExistsError(f"Destination already exists: {dst}")
        shutil.rmtree(dst)

    ignore_names = {
        "_build",
        "build",
        "target",
        "__pycache__",
        ".pytest_cache",
        "_diagrams",
    }

    def _ignore(directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            if name in ignore_names:
                ignored.add(name)
            if name.endswith(".pyc"):
                ignored.add(name)
            if name == ".DS_Store":
                ignored.add(name)
        return ignored

    shutil.copytree(src, dst, ignore=_ignore)


def _copytree_merge(src: Path, dst: Path) -> None:
    ignore_names = {
        "_build",
        "build",
        "target",
        "__pycache__",
        ".pytest_cache",
        "_diagrams",
    }

    def _ignore(directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            if name in ignore_names:
                ignored.add(name)
            if name.endswith(".pyc"):
                ignored.add(name)
            if name == ".DS_Store":
                ignored.add(name)
        return ignored

    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)


def _repo_root() -> Path:
    # Resolve relative paths independent of current working directory.
    return Path(__file__).resolve().parents[1]


def _rewrite_conf_project(conf_path: Path, project_title: str) -> None:
    if not conf_path.is_file():
        return

    lines = conf_path.read_text(encoding="utf-8").splitlines(True)
    out: list[str] = []
    replaced = False
    for line in lines:
        if not replaced and line.strip().startswith("project ="):
            out.append(f"project = {project_title!r}\n")
            replaced = True
        else:
            out.append(line)

    conf_path.write_text("".join(out), encoding="utf-8")


def _rewrite_readme_title(readme_path: Path, name: str) -> None:
    if not readme_path.is_file():
        return

    text = readme_path.read_text(encoding="utf-8")
    # Minimal, safe update: if there is a Markdown H1, replace only that line.
    lines = text.splitlines(True)
    for i, line in enumerate(lines[:5]):
        if line.startswith("# "):
            lines[i] = f"# {name}\n"
            break
    readme_path.write_text("".join(lines), encoding="utf-8")


def cmd_new(args: argparse.Namespace) -> int:
    template_kind = getattr(args, "template", "basic")
    templates = TEMPLATES_BASIC if template_kind == "basic" else TEMPLATES_EXAMPLE

    template = templates.get(args.language)
    if template is None:
        print(f"ERROR: Unsupported language: {args.language}", file=sys.stderr)
        return 2

    repo_root = _repo_root()
    dest = (
        Path(args.destination).resolve()
        if args.destination
        else (repo_root / args.name).resolve()
    )

    if dest.exists():
        if not args.force:
            print(f"ERROR: Destination already exists: {dest}", file=sys.stderr)
            return 2
        shutil.rmtree(dest)

    if template_kind == "basic":
        shared_src = (repo_root / TEMPLATE_BASIC_SHARED).resolve()
        lang_src = (repo_root / template).resolve()

        if not shared_src.is_dir():
            print(
                f"ERROR: Shared template directory not found: {shared_src}",
                file=sys.stderr,
            )
            return 2
        if not lang_src.is_dir():
            print(f"ERROR: Template directory not found: {lang_src}", file=sys.stderr)
            return 2

        dest.mkdir(parents=True, exist_ok=True)
        _copytree_merge(shared_src, dest)
        _copytree_merge(lang_src, dest)

        src = lang_src
    else:
        src = (repo_root / template).resolve()
        if not src.is_dir():
            print(f"ERROR: Template directory not found: {src}", file=sys.stderr)
            return 2
        try:
            _copytree(src, dest, force=args.force)
        except FileExistsError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    # Light customization (best-effort)
    project_title = f"OSQAr: {args.name} ({args.language})"
    _rewrite_conf_project(dest / "conf.py", project_title)
    _rewrite_readme_title(dest / "README.md", args.name)

    print(f"Created OSQAr project at: {dest}")
    print(f"Template: {src} ({template_kind})")
    return 0


def cmd_traceability(args: argparse.Namespace) -> int:
    argv = [str(args.needs_json)]
    if args.json_report:
        argv += ["--json-report", str(args.json_report)]

    if args.enforce_req_has_test:
        argv += ["--enforce-req-has-test"]
    if args.enforce_arch_traces_req:
        argv += ["--enforce-arch-traces-req"]
    if args.enforce_test_traces_req:
        argv += ["--enforce-test-traces-req"]

    # The underlying tool defaults already match OSQAr expectations.
    return traceability_cli(argv)


def cmd_code_trace(args: argparse.Namespace) -> int:
    argv: list[str] = ["--root", str(args.root)]
    if getattr(args, "needs_json", None):
        argv += ["--needs-json", str(args.needs_json)]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]

    for d in getattr(args, "impl_dir", []) or []:
        argv += ["--impl-dir", str(d)]
    for d in getattr(args, "test_dir", []) or []:
        argv += ["--test-dir", str(d)]
    for ex in getattr(args, "exclude", []) or []:
        argv += ["--exclude", ex]
    for ext in getattr(args, "ext", []) or []:
        argv += ["--ext", ext]
    if getattr(args, "max_bytes", None) is not None:
        argv += ["--max-bytes", str(args.max_bytes)]

    if getattr(args, "enforce_req_in_impl", False):
        argv += ["--enforce-req-in-impl"]
    if getattr(args, "enforce_arch_in_impl", False):
        argv += ["--enforce-arch-in-impl"]
    if getattr(args, "enforce_test_in_tests", False):
        argv += ["--enforce-test-in-tests"]
    if getattr(args, "enforce_no_unknown_ids", False):
        argv += ["--enforce-no-unknown-ids"]

    # Underlying defaults match OSQAr expectations.
    return code_trace_cli(argv)


def cmd_checksums_generate(args: argparse.Namespace) -> int:
    argv = ["--root", str(args.root), "--output", str(args.output)]
    for ex in args.exclude:
        argv += ["--exclude", ex]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]
    return checksums_cli(argv)


def cmd_checksums_verify(args: argparse.Namespace) -> int:
    argv = ["--root", str(args.root), "--verify", str(args.manifest)]
    for ex in args.exclude:
        argv += ["--exclude", ex]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]
    return checksums_cli(argv)


def _logical_cwd() -> Path:
    # On macOS, `os.getcwd()` may return a physical path (symlinks/casing collapsed),
    # while shells preserve the logical path in $PWD.
    return Path(os.environ.get("PWD") or os.getcwd())


def _abspath_no_resolve(path: Path) -> Path:
    # Do not use `Path.resolve()` (follows symlinks). Also avoid `os.path.abspath()`
    # without a base, since it relies on getcwd() which may be physical on macOS.
    base = _logical_cwd()
    p = path
    if not p.is_absolute():
        p = base / p
    return Path(os.path.normpath(os.fspath(p)))


def _open_in_browser(path: Path) -> int:
    path = path.resolve()
    if not path.exists():
        print(f"ERROR: path not found: {path}", file=sys.stderr)
        return 2

    if sys.platform == "darwin":
        rc = _run(["open", str(path)], cwd=Path.cwd())
        if rc != 0:
            _print_open_hint(path)
        return rc

    if sys.platform.startswith("linux"):
        rc = _run(["xdg-open", str(path)], cwd=Path.cwd())
        if rc != 0:
            _print_open_hint(path)
        return rc

    if os.name == "nt":
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return 0
        except Exception as exc:  # noqa: BLE001 - best-effort UX
            print(f"ERROR: failed to open path: {path} ({exc})", file=sys.stderr)
            _print_open_hint(path)
            return 2

    _print_open_hint(path)
    return 0


def cmd_open_docs(args: argparse.Namespace) -> int:
    # Default: open docs for the current project.
    project = getattr(args, "project", ".")
    shipment = getattr(args, "shipment", None)
    raw_path = getattr(args, "path", None)

    target: Optional[Path] = None

    if raw_path:
        p = _abspath_no_resolve(Path(raw_path).expanduser())
        if p.is_dir():
            candidate = p / "index.html"
            if candidate.is_file():
                target = candidate
            else:
                print(
                    f"ERROR: index.html not found under directory: {p}",
                    file=sys.stderr,
                )
                return 2
        else:
            target = p
    elif shipment:
        ship_dir = _abspath_no_resolve(Path(shipment).expanduser())
        target = ship_dir / "index.html"
    else:
        project_dir = _abspath_no_resolve(Path(project).expanduser())
        ship_dir = _abspath_no_resolve(project_dir / DEFAULT_BUILD_DIR)
        target = ship_dir / "index.html"

    if target is None:
        print("ERROR: could not resolve target path", file=sys.stderr)
        return 2

    if args.print_only:
        print(target)
        return 0

    if not target.is_file():
        print(f"ERROR: documentation entrypoint not found: {target}", file=sys.stderr)
        if shipment or raw_path:
            return 2
        print("TIP: build docs first via: osqar build-docs", file=sys.stderr)
        return 2

    return _open_in_browser(target)


def _run_capture(cmd: list[str], *, cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return int(proc.returncode), (proc.stdout or "").strip()
    except FileNotFoundError as exc:
        return 127, f"command not found: {cmd[0]} ({exc})"


def _write_json_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _doctor_best_effort_shipment_dir(
    project_dir: Path, explicit: Optional[str]
) -> Optional[Path]:
    if explicit:
        return Path(explicit).expanduser().resolve()
    default = (project_dir / DEFAULT_BUILD_DIR).resolve()
    return default if default.is_dir() else None


def _doctor_run_checksums_verify(
    *,
    shipment_dir: Path,
    manifest: Path,
    exclude: list[str],
) -> tuple[int, Optional[dict]]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tf:
        tmp_path = Path(tf.name)
    try:
        argv = [
            "--root",
            str(shipment_dir),
            "--verify",
            str(manifest),
            "--json-report",
            str(tmp_path),
        ]
        for ex in exclude:
            argv += ["--exclude", ex]
        rc = int(checksums_cli(argv))
        try:
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        return rc, data if isinstance(data, dict) else None
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _doctor_run_traceability(
    *,
    needs_json: Path,
    enforce_req_has_test: bool,
    enforce_arch_traces_req: bool,
    enforce_test_traces_req: bool,
) -> tuple[int, Optional[dict]]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tf:
        tmp_path = Path(tf.name)
    try:
        argv = [str(needs_json), "--json-report", str(tmp_path)]
        if enforce_req_has_test:
            argv += ["--enforce-req-has-test"]
        if enforce_arch_traces_req:
            argv += ["--enforce-arch-traces-req"]
        if enforce_test_traces_req:
            argv += ["--enforce-test-traces-req"]

        rc = int(traceability_cli(argv))
        try:
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        return rc, data if isinstance(data, dict) else None
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def cmd_doctor(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).expanduser().resolve()
    skip_env_checks = bool(getattr(args, "skip_env_checks", False))
    warnings: list[str] = []
    errors: list[str] = []
    checks: list[dict[str, object]] = []

    def info(msg: str) -> None:
        print(f"INFO: {msg}")

    def good(msg: str) -> None:
        print(f"OK: {msg}")

    def warn(msg: str) -> None:
        print(f"WARN: {msg}")
        warnings.append(msg)

    def issue(msg: str) -> None:
        print(f"ISSUE: {msg}")
        warnings.append(msg)

    def bad(msg: str) -> None:
        print(f"ERROR: {msg}")
        errors.append(msg)

    info(f"python={sys.executable}")
    info(f"platform={sys.platform}")

    if not skip_env_checks:
        if not project_dir.is_dir():
            bad(f"project directory not found: {project_dir}")
            return 2

        if _is_shipment_project_dir(project_dir):
            good(f"project looks like a shipment project: {project_dir}")
        else:
            warn(f"project is missing conf.py/index.rst: {project_dir}")

        uses_poetry = _project_uses_poetry(project_dir)
        poetry = shutil.which("poetry")
        if uses_poetry:
            if poetry:
                good("poetry found")
            else:
                bad("poetry not found but project uses Poetry (pyproject.toml)")
        else:
            if poetry:
                good("poetry found (project does not require it)")
            else:
                info("poetry not found")

        # Sphinx availability (in the environment that build-docs will use).
        if uses_poetry and poetry:
            rc, out = _run_capture(
                [
                    "poetry",
                    "run",
                    "python",
                    "-c",
                    "import sphinx; print(sphinx.__version__)",
                ],
                cwd=project_dir,
            )
            if rc == 0:
                good(f"sphinx import OK (poetry env): {out}")
            else:
                bad(f"sphinx not available in poetry env (rc={rc}): {out}")
        else:
            rc, out = _run_capture(
                [sys.executable, "-c", "import sphinx; print(sphinx.__version__)"],
                cwd=project_dir,
            )
            if rc == 0:
                good(f"sphinx import OK (current env): {out}")
            else:
                warn(
                    "sphinx not importable in current env; build-docs may still work if you use Poetry"
                )

        # PlantUML diagnostics.
        plantuml_cmd = shutil.which("plantuml")
        plantuml_jar = os.environ.get("PLANTUML_JAR")
        if plantuml_cmd:
            good(f"plantuml command found: {plantuml_cmd}")
        elif plantuml_jar:
            jar_path = Path(plantuml_jar).expanduser()
            if jar_path.is_file():
                java = shutil.which("java")
                if java:
                    good(f"PLANTUML_JAR set and java found: {jar_path}")
                else:
                    warn(f"PLANTUML_JAR set but java not found: {jar_path}")
            else:
                warn(f"PLANTUML_JAR set but file not found: {jar_path}")
        else:
            warn(
                "no PlantUML command or PLANTUML_JAR detected; builds may fall back to the public PlantUML server (internet required)"
            )

    shipment_override = getattr(args, "shipment", None)
    if skip_env_checks and shipment_override:
        shipment_dir = Path(shipment_override).expanduser().resolve()
    else:
        shipment_dir = _doctor_best_effort_shipment_dir(project_dir, shipment_override)
    if shipment_dir is None:
        info(
            "no shipment directory detected (build via: osqar build-docs) or pass --shipment"
        )
    else:
        info(f"shipment={shipment_dir}")
        if not shipment_dir.is_dir():
            bad(f"shipment directory not found: {shipment_dir}")
            shipment_dir = None

    # Shipment artifact checks (best-effort, non-destructive)
    if (
        shipment_dir is not None
        and getattr(args, "skip_shipment_checks", False) is False
    ):
        index = shipment_dir / "index.html"
        if index.is_file():
            good("shipment has index.html")
            checks.append(
                {"name": "shipment.index_html", "status": "ok", "path": str(index)}
            )
        else:
            issue("shipment is missing index.html (docs may not have been built)")
            checks.append(
                {"name": "shipment.index_html", "status": "missing", "path": str(index)}
            )

        md_path = shipment_dir / DEFAULT_PROJECT_METADATA
        md = _read_project_metadata(shipment_dir)
        if md_path.is_file() and md:
            good("shipment has osqar_project.json")
            if not md.get("version"):
                warn("shipment metadata has no version")
            origin = md.get("origin")
            if not isinstance(origin, dict) or not origin:
                warn("shipment metadata has no origin")
            checks.append(
                {"name": "shipment.metadata", "status": "ok", "path": str(md_path)}
            )
        elif md_path.is_file() and not md:
            bad(f"failed to parse shipment metadata: {md_path}")
            checks.append(
                {"name": "shipment.metadata", "status": "error", "path": str(md_path)}
            )
        else:
            warn("shipment has no osqar_project.json metadata")
            checks.append(
                {"name": "shipment.metadata", "status": "missing", "path": str(md_path)}
            )

        needs_json = _find_needs_json(shipment_dir)
        if needs_json and needs_json.is_file():
            good("shipment has needs.json")
            checks.append(
                {"name": "shipment.needs_json", "status": "ok", "path": str(needs_json)}
            )
        else:
            warn("shipment has no needs.json (traceability cannot be evaluated)")
            checks.append(
                {
                    "name": "shipment.needs_json",
                    "status": "missing",
                    "path": str((shipment_dir / "needs.json")),
                }
            )

        tr_report = shipment_dir / DEFAULT_TRACEABILITY_REPORT
        if tr_report.is_file():
            good("shipment has traceability_report.json")
            checks.append(
                {
                    "name": "shipment.traceability_report",
                    "status": "ok",
                    "path": str(tr_report),
                }
            )
        else:
            warn(
                "shipment is missing traceability_report.json (supplier-side traceability evidence not present)"
            )
            checks.append(
                {
                    "name": "shipment.traceability_report",
                    "status": "missing",
                    "path": str(tr_report),
                }
            )

        has_any_junit = False
        try:
            for pat in _DEFAULT_TEST_REPORT_GLOBS:
                if any(shipment_dir.glob(pat)):
                    has_any_junit = True
                    break
        except Exception:
            has_any_junit = False
        if has_any_junit:
            good("shipment has raw JUnit XML test report(s)")
            checks.append({"name": "shipment.test_reports", "status": "ok"})
        else:
            warn(
                "shipment has no raw JUnit XML test reports (optional but recommended)"
            )
            checks.append({"name": "shipment.test_reports", "status": "missing"})

        manifest = shipment_dir / DEFAULT_CHECKSUM_MANIFEST
        if manifest.is_file():
            good("shipment has SHA256SUMS")
            checks.append(
                {
                    "name": "shipment.checksum_manifest",
                    "status": "ok",
                    "path": str(manifest),
                }
            )
        else:
            issue("shipment is missing SHA256SUMS (integrity cannot be verified)")
            checks.append(
                {
                    "name": "shipment.checksum_manifest",
                    "status": "missing",
                    "path": str(manifest),
                }
            )

        if manifest.is_file() and not getattr(args, "skip_checksums", False):
            rc, data = _doctor_run_checksums_verify(
                shipment_dir=shipment_dir,
                manifest=manifest,
                exclude=list(getattr(args, "exclude", []) or []),
            )
            if rc == 0:
                good("checksums verify OK")
                checks.append({"name": "checksums.verify", "status": "ok", "rc": rc})
            else:
                bad(f"checksums verify FAILED (rc={rc})")
                checks.append({"name": "checksums.verify", "status": "fail", "rc": rc})
            if data is not None:
                checks[-1]["report"] = data

        # Run traceability if requested OR if needs.json exists (full shipment status).
        wants_trace = bool(getattr(args, "traceability", False))
        if (not getattr(args, "skip_traceability", False)) and (
            wants_trace or (needs_json and needs_json.is_file())
        ):
            if needs_json is None or not needs_json.is_file():
                bad("traceability check requested but needs.json not found")
            else:
                # If needs.json contains no needs, traceability is not meaningful.
                try:
                    data = json.loads(needs_json.read_text(encoding="utf-8"))
                except Exception as exc:  # noqa: BLE001
                    bad(f"failed to parse needs.json: {needs_json} ({exc})")
                    data = None

                has_any_needs = False
                if isinstance(data, dict):
                    if isinstance(data.get("needs"), list) and data.get("needs"):
                        has_any_needs = True
                    elif isinstance(data.get("versions"), dict):
                        versions = data.get("versions")
                        current_version = data.get("current_version", "")
                        if (
                            current_version in versions
                            and isinstance(versions[current_version], dict)
                            and versions[current_version].get("needs")
                        ):
                            has_any_needs = True

                if not has_any_needs:
                    warn(
                        f"needs.json contains no needs; skipping traceability check: {needs_json}"
                    )
                    checks.append(
                        {
                            "name": "traceability",
                            "status": "skipped",
                            "reason": "no needs",
                            "path": str(needs_json),
                        }
                    )
                else:
                    trc, treport = _doctor_run_traceability(
                        needs_json=needs_json,
                        enforce_req_has_test=bool(
                            getattr(args, "enforce_req_has_test", False)
                        ),
                        enforce_arch_traces_req=bool(
                            getattr(args, "enforce_arch_traces_req", False)
                        ),
                        enforce_test_traces_req=bool(
                            getattr(args, "enforce_test_traces_req", False)
                        ),
                    )
                    if trc == 0:
                        good(f"traceability OK: {needs_json}")
                        checks.append(
                            {
                                "name": "traceability",
                                "status": "ok",
                                "rc": trc,
                                "path": str(needs_json),
                            }
                        )
                    else:
                        bad(f"traceability FAILED (rc={trc}): {needs_json}")
                        checks.append(
                            {
                                "name": "traceability",
                                "status": "fail",
                                "rc": trc,
                                "path": str(needs_json),
                            }
                        )
                    if treport is not None:
                        checks[-1]["report"] = treport

    report: dict[str, object] = {
        "schema": "osqar.doctor_report.v1",
        "generated_at": _utc_now_iso(),
        "project": str(project_dir),
        "shipment": str(shipment_dir) if shipment_dir is not None else None,
        "python": sys.executable,
        "platform": sys.platform,
        "warnings": warnings,
        "errors": errors,
        "checks": checks,
    }

    if getattr(args, "json_report", None):
        out = Path(args.json_report).expanduser().resolve()
        _write_json_report(out, report)
        print(f"Wrote doctor report: {out}")

    # CI-friendly: return 1 if any issues (warnings or errors).
    return 0 if (not warnings and not errors) else 1


def _shipment_verify_static_checks(
    shipment_dir: Path,
) -> tuple[list[dict[str, object]], list[str], list[str]]:
    checks: list[dict[str, object]] = []
    warnings: list[str] = []
    errors: list[str] = []

    def warn(msg: str) -> None:
        print(f"WARN: {msg}")
        warnings.append(msg)

    def bad(msg: str) -> None:
        print(f"ERROR: {msg}")
        errors.append(msg)

    index = shipment_dir / "index.html"
    if index.is_file():
        checks.append(
            {"name": "shipment.index_html", "status": "ok", "path": str(index)}
        )
    else:
        warn("shipment is missing index.html")
        checks.append(
            {"name": "shipment.index_html", "status": "missing", "path": str(index)}
        )

    md_path = shipment_dir / DEFAULT_PROJECT_METADATA
    md = _read_project_metadata(shipment_dir)
    if md_path.is_file() and md:
        checks.append(
            {"name": "shipment.metadata", "status": "ok", "path": str(md_path)}
        )
        if not md.get("version"):
            warn("shipment metadata has no version")
        origin = md.get("origin")
        if not isinstance(origin, dict) or not origin:
            warn("shipment metadata has no origin")
    elif md_path.is_file() and not md:
        bad(f"failed to parse shipment metadata: {md_path}")
        checks.append(
            {"name": "shipment.metadata", "status": "error", "path": str(md_path)}
        )
    else:
        bad("shipment has no osqar_project.json metadata")
        checks.append(
            {"name": "shipment.metadata", "status": "missing", "path": str(md_path)}
        )

    needs_json = _find_needs_json(shipment_dir)
    if needs_json and needs_json.is_file():
        checks.append(
            {"name": "shipment.needs_json", "status": "ok", "path": str(needs_json)}
        )
    else:
        warn("shipment has no needs.json")
        checks.append(
            {
                "name": "shipment.needs_json",
                "status": "missing",
                "path": str(shipment_dir / "needs.json"),
            }
        )

    tr_report = shipment_dir / DEFAULT_TRACEABILITY_REPORT
    if tr_report.is_file():
        checks.append(
            {
                "name": "shipment.traceability_report",
                "status": "ok",
                "path": str(tr_report),
            }
        )
    else:
        warn("shipment is missing traceability_report.json")
        checks.append(
            {
                "name": "shipment.traceability_report",
                "status": "missing",
                "path": str(tr_report),
            }
        )

    return checks, warnings, errors


def _relpath(from_dir: Path, to_path: Path) -> str:
    try:
        return os.path.relpath(os.fspath(to_path), start=os.fspath(from_dir))
    except Exception:
        return os.fspath(to_path)


def cmd_workspace_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    shipments = _iter_shipment_dirs(root, recursive=bool(args.recursive))
    if not shipments:
        print(f"No shipments found under: {root}")
        return 1

    items: list[dict[str, object]] = []
    for shipment_dir in shipments:
        shipment_dir = shipment_dir.resolve()
        md = _read_project_metadata(shipment_dir)
        needs = _read_needs_summary_from_shipment(shipment_dir)
        entry = {
            "shipment": str(shipment_dir),
            "metadata": md,
            "needs_summary": needs,
            "has_docs": bool((shipment_dir / "index.html").is_file()),
        }
        items.append(entry)

    fmt = getattr(args, "format", "table")
    if fmt == "paths":
        for it in items:
            print(it["shipment"])
        return 0

    if fmt == "json":
        payload = json.dumps(items, indent=2, sort_keys=True) + "\n"
        if getattr(args, "json_report", None):
            out = Path(args.json_report).resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload, encoding="utf-8")
            print(f"Wrote workspace list: {out}")
            return 0
        print(payload, end="")
        return 0

    for it in items:
        md = it.get("metadata") or {}
        name = md.get("name") if isinstance(md, dict) else None
        version = md.get("version") if isinstance(md, dict) else None
        needs = it.get("needs_summary") or {}
        n_total = needs.get("needs_total") if isinstance(needs, dict) else None
        suffix = []
        if name:
            suffix.append(f"name={name}")
        if version:
            suffix.append(f"version={version}")
        if n_total is not None:
            suffix.append(f"needs={n_total}")
        if it.get("has_docs"):
            suffix.append("docs=yes")
        else:
            suffix.append("docs=no")
        print(f"- {it['shipment']}  ({', '.join(suffix)})")

    return 0


def cmd_workspace_report(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ws_config = _read_workspace_config(
        root, explicit_path=getattr(args, "config", None)
    )
    shipments = _iter_shipment_dirs(root, recursive=bool(args.recursive))
    if not shipments:
        print(f"No shipments found under: {root}")
        return 1

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    effective_excludes = _config_defaults_exclude(ws_config) + list(
        getattr(args, "exclude", []) or []
    )

    env = {
        "OSQAR_WORKSPACE_ROOT": str(root),
        "OSQAR_WORKSPACE_OUTPUT": str(output_dir),
    }
    rc = _run_hooks(
        ws_config,
        args=args,
        phase="pre",
        event="workspace.report",
        cwd=Path.cwd(),
        env=env,
    )
    if rc != 0:
        return int(rc)

    if not getattr(args, "dry_run", False):
        (output_dir / "checksums").mkdir(parents=True, exist_ok=True)
        (output_dir / "traceability").mkdir(parents=True, exist_ok=True)
        (output_dir / "doctor").mkdir(parents=True, exist_ok=True)

    items: list[dict[str, object]] = []
    any_failures = False

    for shipment_dir in shipments:
        shipment_dir = shipment_dir.resolve()
        print(f"\n== Inspecting shipment: {shipment_dir}")

        # Use a stable, filesystem-friendly name for per-shipment reports.
        safe_name = shipment_dir.name
        try:
            safe_name = shipment_dir.relative_to(root).as_posix().replace("/", "__")
        except Exception:
            pass

        checksums_rc: Optional[int] = None
        checksums_report: Optional[str] = None
        if getattr(args, "checksums", False):
            manifest = shipment_dir / DEFAULT_CHECKSUM_MANIFEST
            if not manifest.is_file():
                checksums_rc = 2
            else:
                argv = ["--root", str(shipment_dir), "--verify", str(manifest)]
                for ex in effective_excludes:
                    argv += ["--exclude", ex]
                checksums_report_path = output_dir / "checksums" / f"{safe_name}.json"
                argv += ["--json-report", str(checksums_report_path)]
                checksums_rc = int(checksums_cli(argv))
                checksums_report = str(checksums_report_path)
            if checksums_rc != 0:
                any_failures = True
                if not args.continue_on_error:
                    # Still record entry below.
                    pass

        trace_rc: Optional[int] = None
        trace_report: Optional[str] = None
        if getattr(args, "traceability", False):
            needs_json = (
                Path(args.needs_json).resolve()
                if getattr(args, "needs_json", None)
                else _find_needs_json(shipment_dir)
            )
            if needs_json is None or not needs_json.is_file():
                trace_rc = 2
            else:
                argv = [str(needs_json)]
                trace_report_path = output_dir / "traceability" / f"{safe_name}.json"
                argv += ["--json-report", str(trace_report_path)]
                if getattr(args, "enforce_req_has_test", False):
                    argv += ["--enforce-req-has-test"]
                if getattr(args, "enforce_arch_traces_req", False):
                    argv += ["--enforce-arch-traces-req"]
                if getattr(args, "enforce_test_traces_req", False):
                    argv += ["--enforce-test-traces-req"]
                trace_rc = int(traceability_cli(argv))
                trace_report = str(trace_report_path)

            if trace_rc != 0:
                any_failures = True

        doctor_rc: Optional[int] = None
        doctor_report: Optional[str] = None
        if getattr(args, "doctor", False):
            doctor_report_path = output_dir / "doctor" / f"{safe_name}.json"
            # Avoid duplicate expensive checks if the caller already asked for them.
            skip_checksums = bool(getattr(args, "checksums", False))
            skip_traceability = not bool(getattr(args, "traceability", False))
            doctor_rc = int(
                cmd_doctor(
                    argparse.Namespace(
                        project=".",
                        shipment=str(shipment_dir),
                        json_report=str(doctor_report_path),
                        traceability=bool(getattr(args, "traceability", False)),
                        needs_json=getattr(args, "needs_json", None),
                        exclude=list(effective_excludes),
                        skip_checksums=skip_checksums,
                        skip_traceability=skip_traceability,
                        skip_shipment_checks=False,
                        skip_env_checks=True,
                        enforce_req_has_test=bool(
                            getattr(args, "enforce_req_has_test", False)
                        ),
                        enforce_arch_traces_req=bool(
                            getattr(args, "enforce_arch_traces_req", False)
                        ),
                        enforce_test_traces_req=bool(
                            getattr(args, "enforce_test_traces_req", False)
                        ),
                    )
                )
            )
            doctor_report = str(doctor_report_path)
            if doctor_rc != 0:
                any_failures = True

        index = shipment_dir / "index.html"
        docs_link = _relpath(output_dir, index) if index.is_file() else None

        items.append(
            {
                "shipment": str(shipment_dir),
                "checksums_rc": checksums_rc,
                "checksums_report": checksums_report,
                "traceability_rc": trace_rc,
                "traceability_report": trace_report,
                "doctor_rc": doctor_rc,
                "doctor_report": doctor_report,
                "metadata": _read_project_metadata(shipment_dir),
                "needs_summary": _read_needs_summary_from_shipment(shipment_dir),
                "docs_entrypoint": docs_link,
            }
        )

        if any_failures and not args.continue_on_error:
            # Stop after the first failure if requested.
            if (checksums_rc not in (None, 0)) or (trace_rc not in (None, 0)):
                break

    overview = {
        "title": "Subproject overview",
        "generated_at": _utc_now_iso(),
        "root": str(root),
        "recursive": bool(args.recursive),
        "checksums": bool(args.checksums),
        "traceability": bool(args.traceability),
        "doctor": bool(getattr(args, "doctor", False)),
        "projects": items,
        "failures": bool(any_failures),
    }

    overview_json_path = output_dir / "subproject_overview.json"

    overview_json_path.write_text(
        json.dumps(overview, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if getattr(args, "json_report", None):
        report_path = Path(args.json_report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(overview, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"\nWrote workspace report: {report_path}")

    print(f"\nWrote Subproject overview JSON: {overview_json_path}")

    # Render a theme-aligned HTML overview via a tiny generated Sphinx project.
    sphinx_src = output_dir / "_sphinx"
    html_out = output_dir / "_build/html"
    _write_workspace_overview_sphinx_source(
        source_dir=sphinx_src,
        html_out_dir=html_out,
        overview=overview,
    )

    print(f"Building workspace overview HTML: {sphinx_src} -> {html_out}")
    rc = _run_sphinx_build(sphinx_src, html_out)
    if rc != 0:
        return int(rc)

    # Cleanup intermediate generated Sphinx sources.
    try:
        shutil.rmtree(sphinx_src)
    except OSError:
        pass

    entry = html_out / "index.html"
    if not entry.is_file():
        print(f"ERROR: overview entrypoint not found: {entry}", file=sys.stderr)
        return 2

    if bool(getattr(args, "open", False)):
        open_rc = _open_in_browser(entry)
        if open_rc != 0:
            return int(open_rc)
    else:
        # CI/non-interactive usage: emit the path for easy consumption.
        print(entry)

    rc = _run_hooks(
        ws_config,
        args=args,
        phase="post",
        event="workspace.report",
        cwd=Path.cwd(),
        env=env,
    )
    if rc != 0:
        return int(rc)

    return 0 if not any_failures else 1


def _write_workspace_overview_sphinx_source(
    *,
    source_dir: Path,
    html_out_dir: Path,
    overview: dict,
) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    static_dir = source_dir / "_static"
    static_dir.mkdir(parents=True, exist_ok=True)

    # Keep the workspace overview styling consistent with the main OSQAr docs.
    # Copy the repo's static CSS into the generated Sphinx project so it works
    # regardless of the output directory location.
    repo_static = Path(__file__).resolve().parent.parent / "_static"
    for css_name in ("custom.css", "furo-fixes.css"):
        src = repo_static / css_name
        dst = static_dir / css_name
        try:
            if src.is_file():
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            # Best-effort only; the overview remains readable without these.
            pass

    conf_py = """# Auto-generated by `osqar workspace report`

from __future__ import annotations

import importlib.util
import os

project = "OSQAr Workspace Overview"

extensions = []

exclude_patterns = [
    "_build",
    ".venv",
    ".venv/**",
]

master_doc = "index"

# Mirror the main OSQAr docs theme behavior.
html_theme = os.environ.get("OSQAR_SPHINX_THEME", "furo")

if html_theme == "furo" and importlib.util.find_spec("furo") is None:
    html_theme = "alabaster"
elif html_theme == "press" and importlib.util.find_spec("sphinx_press_theme") is None:
    html_theme = "alabaster"

html_static_path = ["_static"]

if html_theme == "furo":
    html_css_files = ["furo-fixes.css"]
else:
    html_css_files = ["custom.css", "furo-fixes.css"]
"""
    (source_dir / "conf.py").write_text(conf_py, encoding="utf-8")

    def esc(s: str) -> str:
        return s.replace("`", "\\`")

    def key_for_project(item: dict) -> str:
        md = item.get("metadata")
        if isinstance(md, dict):
            for k in ("id", "project_id"):
                v = md.get(k)
                if v:
                    return str(v)
            if md.get("name"):
                return str(md.get("name"))
        return str(item.get("shipment") or "")

    lines: list[str] = []
    lines.append("Workspace overview\n")
    lines.append("==================\n\n")
    lines.append(
        "This page is generated by ``osqar workspace report`` and summarizes all discovered shipments.\n\n"
    )
    lines.append(f"Generated at: {esc(str(overview.get('generated_at') or '—'))}\n\n")
    lines.append(f"Root: {esc(str(overview.get('root') or '—'))}\n\n")
    lines.append(
        "Checks: "
        + ("checksums" if overview.get("checksums") else "checksums (skipped)")
        + ", "
        + ("traceability" if overview.get("traceability") else "traceability (skipped)")
        + "\n\n"
    )

    lines.append(".. list-table::\n")
    lines.append("   :header-rows: 1\n\n")
    lines.append("   * - Project\n")
    lines.append("     - Version\n")
    lines.append("     - Origin\n")
    lines.append("     - URLs\n")
    lines.append("     - Needs\n")
    lines.append("     - REQ\n")
    lines.append("     - ARCH\n")
    lines.append("     - TEST\n")
    lines.append("     - Checksums\n")
    lines.append("     - Traceability\n")

    projects = overview.get("projects")
    if not isinstance(projects, list):
        projects = []

    for it in projects:
        if not isinstance(it, dict):
            continue
        shipment = it.get("shipment")
        shipment_dir = Path(str(shipment)).resolve() if shipment else None
        project_label = key_for_project(it)

        link = ""
        if shipment_dir is not None:
            index = shipment_dir / "index.html"
            if index.is_file():
                rel = _relpath(html_out_dir, index)
                link = f"`{esc(project_label)} <{esc(rel)}>`_"

        project_cell = link or esc(project_label)

        md = it.get("metadata") or {}
        version = ""
        origin_val = ""
        urls_val = ""
        if isinstance(md, dict):
            version = str(md.get("version") or "")
            origin = md.get("origin")
            if isinstance(origin, dict):
                origin_val = str(
                    origin.get("url")
                    or origin.get("repo")
                    or origin.get("source")
                    or ""
                )
            urls = md.get("urls")
            if isinstance(urls, dict) and urls:
                parts: list[str] = []
                for k, v in sorted(urls.items()):
                    parts.append(f"{k}: {v}")
                urls_val = "; ".join(parts)

        needs = it.get("needs_summary") or {}
        n_total = needs.get("needs_total", "") if isinstance(needs, dict) else ""
        n_req = needs.get("req_total", "") if isinstance(needs, dict) else ""
        n_arch = needs.get("arch_total", "") if isinstance(needs, dict) else ""
        n_test = needs.get("test_total", "") if isinstance(needs, dict) else ""

        checksums_rc = it.get("checksums_rc")
        trace_rc = it.get("traceability_rc")

        def cell(v: object, *, empty: str = "") -> str:
            return esc(str(v)) if v not in (None, "") else empty

        def rc_cell(rc: object) -> str:
            if rc is None or rc == "":
                return "skipped"
            try:
                code = int(rc)
            except (TypeError, ValueError):
                return cell(rc, empty="skipped")
            return "OK" if code == 0 else f"FAIL ({code})"

        lines.append("\n   * - " + project_cell + "\n")
        lines.append("     - " + cell(version, empty="—") + "\n")
        lines.append("     - " + cell(origin_val, empty="—") + "\n")
        lines.append("     - " + cell(urls_val, empty="—") + "\n")
        lines.append("     - " + cell(n_total) + "\n")
        lines.append("     - " + cell(n_req) + "\n")
        lines.append("     - " + cell(n_arch) + "\n")
        lines.append("     - " + cell(n_test) + "\n")
        lines.append("     - " + rc_cell(checksums_rc) + "\n")
        lines.append("     - " + rc_cell(trace_rc) + "\n")

    # Put the full content onto the root page. Themes may render a toctree-only
    # root as visually empty.
    (source_dir / "index.rst").write_text("".join(lines), encoding="utf-8")


def cmd_workspace_diff(args: argparse.Namespace) -> int:
    old_path = Path(args.old).expanduser().resolve()
    new_path = Path(args.new).expanduser().resolve()
    if not old_path.is_file():
        print(f"ERROR: old report not found: {old_path}", file=sys.stderr)
        return 2
    if not new_path.is_file():
        print(f"ERROR: new report not found: {new_path}", file=sys.stderr)
        return 2

    def load_projects(path: Path) -> list[dict]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("projects"), list):
            return [p for p in data["projects"] if isinstance(p, dict)]
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
        return []

    def key_for(p: dict) -> str:
        md = p.get("metadata")
        if isinstance(md, dict):
            for k in ("id", "project_id"):
                if md.get(k):
                    return str(md.get(k))
            if md.get("name"):
                return str(md.get("name"))
        return str(p.get("shipment") or "")

    def summarize(p: dict) -> dict[str, object]:
        md = p.get("metadata") if isinstance(p.get("metadata"), dict) else {}
        needs = (
            p.get("needs_summary") if isinstance(p.get("needs_summary"), dict) else {}
        )
        return {
            "version": (md or {}).get("version"),
            "origin": ((md or {}).get("origin") or {}),
            "needs_total": (needs or {}).get("needs_total"),
            "req_total": (needs or {}).get("req_total"),
            "arch_total": (needs or {}).get("arch_total"),
            "test_total": (needs or {}).get("test_total"),
            "code_total": (needs or {}).get("code_total"),
            "checksums_rc": p.get("checksums_rc"),
            "traceability_rc": p.get("traceability_rc"),
            "shipment": p.get("shipment"),
        }

    old_projects = {key_for(p): summarize(p) for p in load_projects(old_path)}
    new_projects = {key_for(p): summarize(p) for p in load_projects(new_path)}

    added = sorted(set(new_projects) - set(old_projects))
    removed = sorted(set(old_projects) - set(new_projects))
    common = sorted(set(old_projects) & set(new_projects))

    changed: list[tuple[str, list[str]]] = []
    for k in common:
        o = old_projects[k]
        n = new_projects[k]
        diffs: list[str] = []
        for field in (
            "version",
            "needs_total",
            "req_total",
            "arch_total",
            "test_total",
            "code_total",
            "checksums_rc",
            "traceability_rc",
        ):
            if o.get(field) != n.get(field):
                diffs.append(f"{field}: {o.get(field)} -> {n.get(field)}")
        if diffs:
            changed.append((k, diffs))

    print(f"Added projects: {len(added)}")
    for k in added:
        print(f"+ {k}")

    print(f"Removed projects: {len(removed)}")
    for k in removed:
        print(f"- {k}")

    print(f"Changed projects: {len(changed)}")
    for k, diffs in changed:
        print(f"* {k}")
        for d in diffs:
            print(f"  - {d}")

    return 0


def cmd_shipment_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    projects: list[ShipmentProject] = []

    for candidate in _iter_project_dirs(root, recursive=args.recursive):
        if not _is_shipment_project_dir(candidate):
            continue
        projects.append(
            ShipmentProject(path=candidate, language=_detect_language(candidate))
        )

    if args.format == "paths":
        for p in projects:
            print(p.path)
        return 0

    if not projects:
        print("No shipment projects found.")
        return 1

    for p in projects:
        print(f"- {p.path}  (language={p.language})")
    return 0


def cmd_shipment_build_docs(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    if not _is_shipment_project_dir(project_dir):
        print(
            f"ERROR: not a shipment project directory (missing conf.py/index.rst): {project_dir}",
            file=sys.stderr,
        )
        return 2

    config = _read_project_config(
        project_dir, explicit_path=getattr(args, "config", None)
    )

    output_dir = (
        Path(args.output).resolve()
        if args.output
        else _default_shipment_dir(project_dir)
    )

    env = {
        "OSQAR_PROJECT_DIR": str(project_dir),
        "OSQAR_DOCS_OUTPUT": str(output_dir),
    }
    rc = _run_hooks(
        config,
        args=args,
        phase="pre",
        event="shipment.build-docs",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    print(f"Building docs: {project_dir} -> {output_dir}")
    rc = _run_docs_build(project_dir, output_dir, config=config)
    if rc != 0:
        return int(rc)

    rc = _run_hooks(
        config,
        args=args,
        phase="post",
        event="shipment.build-docs",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    if getattr(args, "open", False):
        entry = output_dir / "index.html"
        if entry.is_file():
            return _open_in_browser(entry)
        print(f"WARNING: docs entrypoint not found: {entry}", file=sys.stderr)
        _print_open_hint(entry)

    return 0


def cmd_shipment_run_tests(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    config = _read_project_config(
        project_dir, explicit_path=getattr(args, "config", None)
    )

    env = {
        "OSQAR_PROJECT_DIR": str(project_dir),
    }
    env.update(
        _reproducible_env(
            project_dir,
            reproducible=bool(getattr(args, "reproducible", False)),
        )
    )
    rc = _run_hooks(
        config,
        args=args,
        phase="pre",
        event="shipment.run-tests",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    command_str = getattr(args, "command", None)
    if not command_str:
        commands = config.get("commands") if isinstance(config, dict) else None
        if isinstance(commands, dict) and isinstance(commands.get("test"), str):
            command_str = commands.get("test")

    if command_str:
        rc = _run_command_string(str(command_str), cwd=project_dir, env=env)
    else:
        script = project_dir / (args.script or "build-and-test.sh")
        if not script.is_file():
            print(
                "ERROR: no test command configured and script not found. Provide --command, set commands.test in osqar_project.json, or provide --script.",
                file=sys.stderr,
            )
            return 2
        print(f"Running script: {script}")
        rc = _run(["bash", str(script.name)], cwd=project_dir, env=env)

    if rc != 0:
        return int(rc)

    rc = _run_hooks(
        config,
        args=args,
        phase="post",
        event="shipment.run-tests",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)
    return 0


def cmd_shipment_run_build(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project directory not found: {project_dir}", file=sys.stderr)
        return 2

    config = _read_project_config(
        project_dir, explicit_path=getattr(args, "config", None)
    )

    env = {
        "OSQAR_PROJECT_DIR": str(project_dir),
    }
    env.update(
        _reproducible_env(
            project_dir,
            reproducible=bool(getattr(args, "reproducible", False)),
        )
    )
    rc = _run_hooks(
        config,
        args=args,
        phase="pre",
        event="shipment.run-build",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    command_str = getattr(args, "command", None)
    if not command_str:
        commands = config.get("commands") if isinstance(config, dict) else None
        if isinstance(commands, dict) and isinstance(commands.get("build"), str):
            command_str = commands.get("build")

    if not command_str:
        print(
            "ERROR: no build command configured. Pass --command or set commands.build in osqar_project.json in the project root.",
            file=sys.stderr,
        )
        return 2

    try:
        cmd = shlex.split(str(command_str))
    except ValueError as exc:
        print(f"ERROR: invalid build command: {exc}", file=sys.stderr)
        return 2

    if not cmd:
        print("ERROR: empty build command", file=sys.stderr)
        return 2

    print(f"Running build command: {command_str}")
    rc = _run(cmd, cwd=project_dir, env=env)
    if rc != 0:
        return int(rc)

    rc = _run_hooks(
        config,
        args=args,
        phase="post",
        event="shipment.run-build",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)
    return 0


def cmd_shipment_clean(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    dry_run = bool(args.dry_run)

    # Conservative default: only remove the well-known generated dirs.
    to_remove = [
        project_dir / "_build",
        project_dir / "build",
        project_dir / "target",
        project_dir / "__pycache__",
        project_dir / ".pytest_cache",
        project_dir / "_diagrams",
    ]
    if args.aggressive:
        to_remove.append(project_dir / "diagrams")

    removed_any = False
    for p in to_remove:
        if not p.exists():
            continue
        removed_any = True
        try:
            _safe_rmtree(p, dry_run=dry_run)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    if not removed_any:
        print("Nothing to clean.")
        return 0

    if dry_run:
        print("DRY-RUN: clean complete.")
    else:
        print("Clean complete.")
    return 0


def cmd_shipment_traceability(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    needs_json = (
        Path(args.needs_json).resolve()
        if args.needs_json
        else _find_needs_json(shipment_dir)
    )
    if needs_json is None or not needs_json.is_file():
        print(
            f"ERROR: needs.json not found in shipment: {shipment_dir}", file=sys.stderr
        )
        return 2

    json_report = (
        Path(args.json_report).resolve()
        if args.json_report
        else (shipment_dir / DEFAULT_TRACEABILITY_REPORT)
    )

    argv = [str(needs_json), "--json-report", str(json_report)]
    if args.enforce_req_has_test:
        argv += ["--enforce-req-has-test"]
    if args.enforce_arch_traces_req:
        argv += ["--enforce-arch-traces-req"]
    if args.enforce_test_traces_req:
        argv += ["--enforce-test-traces-req"]

    return traceability_cli(argv)


def cmd_shipment_checksums(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    manifest = (
        Path(args.manifest).resolve()
        if args.manifest
        else (shipment_dir / DEFAULT_CHECKSUM_MANIFEST)
    )

    if args.mode == "generate":
        argv = ["--root", str(shipment_dir), "--output", str(manifest)]
        for ex in args.exclude:
            argv += ["--exclude", ex]
        if getattr(args, "json_report", None):
            argv += ["--json-report", str(args.json_report)]
        return checksums_cli(argv)

    argv = ["--root", str(shipment_dir), "--verify", str(manifest)]
    for ex in args.exclude:
        argv += ["--exclude", ex]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]
    return checksums_cli(argv)


def cmd_shipment_copy_test_reports(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    shipment_dir = (
        Path(args.shipment).resolve()
        if args.shipment
        else _default_shipment_dir(project_dir)
    )
    globs = tuple(args.glob) if args.glob else _DEFAULT_TEST_REPORT_GLOBS
    return _copy_test_reports(
        project_dir, shipment_dir, dry_run=bool(args.dry_run), globs=globs
    )


def cmd_shipment_package(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    if not shipment_dir.is_dir():
        print(f"ERROR: shipment directory not found: {shipment_dir}", file=sys.stderr)
        return 2

    out = (
        Path(args.output).resolve() if args.output else shipment_dir.with_suffix(".zip")
    )
    if out.suffix.lower() != ".zip":
        print(
            f"ERROR: only .zip archives are supported (got: {out})",
            file=sys.stderr,
        )
        return 2
    root_name = shipment_dir.name

    if args.dry_run:
        print(f"DRY-RUN: would create archive {out} from {shipment_dir}")
        return 0

    # Deterministic ZIP creation:
    # - stable file ordering
    # - timestamps from SOURCE_DATE_EPOCH if set (clamped to 1980-01-01)
    # - store mode to avoid cross-tool compression differences
    def _zip_timestamp() -> tuple[int, int, int, int, int, int]:
        # ZIP does not support timestamps before 1980.
        epoch_raw = os.environ.get("SOURCE_DATE_EPOCH")
        if epoch_raw:
            try:
                dt = datetime.fromtimestamp(int(epoch_raw), tz=timezone.utc)
            except (ValueError, OSError):
                dt = datetime.now(tz=timezone.utc)
        else:
            dt = datetime.now(tz=timezone.utc)
        if dt.year < 1980:
            dt = datetime(1980, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    zip_dt = _zip_timestamp()
    files = sorted(
        (p for p in shipment_dir.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(shipment_dir).as_posix(),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_STORED) as zf:
        for src in files:
            if src.is_symlink():
                print(f"WARNING: skipping symlink in archive: {src}")
                continue

            rel = src.relative_to(shipment_dir).as_posix()
            arcname = f"{root_name}/{rel}"

            zi = zipfile.ZipInfo(filename=arcname, date_time=zip_dt)
            zi.compress_type = zipfile.ZIP_STORED

            mode = int(src.stat().st_mode) & 0o777
            zi.external_attr = (stat.S_IFREG | mode) << 16

            with src.open("rb") as fsrc, zf.open(zi, "w") as fdst:
                shutil.copyfileobj(fsrc, fdst)

    print(f"Wrote archive: {out}")
    return 0


def cmd_framework_bundle(args: argparse.Namespace) -> int:
    version = str(args.version)
    docs_dir = Path(args.docs_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not docs_dir.is_dir():
        print(f"ERROR: docs dir not found: {docs_dir}", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[2]
    bundle_root = output_dir / f"osqar-framework-{version}"

    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    def _ignore_common(_directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            if name in {
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".DS_Store",
                ".venv",
            }:
                ignored.add(name)
            if name.endswith(".pyc"):
                ignored.add(name)
        return ignored

    def _copytree(src: Path, dst: Path) -> None:
        if not src.is_dir():
            raise FileNotFoundError(f"Directory not found: {src}")
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=_ignore_common)

    def _copyfile(src: Path, dst: Path) -> None:
        if not src.is_file():
            raise FileNotFoundError(f"File not found: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    _copytree(docs_dir, bundle_root / "docs")
    _copytree(repo_root / "tools", bundle_root / "tools")
    _copytree(repo_root / "templates", bundle_root / "templates")

    _copyfile(repo_root / "osqar", bundle_root / "osqar")
    if (repo_root / "osqar.cmd").is_file():
        _copyfile(repo_root / "osqar.cmd", bundle_root / "osqar.cmd")
    if (repo_root / "osqar.ps1").is_file():
        _copyfile(repo_root / "osqar.ps1", bundle_root / "osqar.ps1")

    for file_name in (
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        "NOTICE",
        "pyproject.toml",
        "poetry.lock",
    ):
        p = repo_root / file_name
        if p.is_file():
            _copyfile(p, bundle_root / file_name)

    (bundle_root / "BUNDLE_README.txt").write_text(
        "\n".join(
            [
                f"OSQAr framework bundle: {version}",
                "",
                "Contents:",
                "- docs/: built HTML framework documentation (open docs/index.html)",
                "- tools/: stdlib-only CLI implementation",
                "- templates/: project scaffolding templates used by the CLI",
                "- osqar / osqar.cmd / osqar.ps1: OSQAr CLI entrypoints",
                "",
                "Quickstart:",
                "- macOS/Linux: ./osqar --help",
                "- Windows (cmd): osqar.cmd --help",
                "- Windows (PowerShell): ./osqar.ps1 --help",
                "",
                "Notes:",
                "- Example workspaces are published as separate release assets.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Assembled framework bundle at: {bundle_root}")
    return 0


def cmd_shipment_metadata_write(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    if not shipment_dir.is_dir():
        print(f"ERROR: shipment directory not found: {shipment_dir}", file=sys.stderr)
        return 2

    metadata: dict[str, object] = {
        "schema": "osqar.shipment_project_metadata.v1",
        "written_at": _utc_now_iso(),
    }

    if args.name:
        metadata["name"] = args.name
    if args.project_id:
        metadata["id"] = args.project_id
    if args.version:
        metadata["version"] = args.version
    if args.description:
        metadata["description"] = args.description

    try:
        if args.url:
            urls = _parse_kv(args.url)
            metadata["urls"] = urls
        if args.origin:
            origin = _parse_kv(args.origin)
            metadata["origin"] = origin
        if args.set:
            for item in args.set:
                if "=" not in item:
                    raise ValueError(f"Expected KEY=VALUE, got: {item}")
                k, v = item.split("=", 1)
                _set_nested_value(metadata, k.strip(), v.strip())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return _write_project_metadata(
        shipment_dir,
        metadata,
        overwrite=bool(args.overwrite),
        dry_run=bool(args.dry_run),
    )


def _shipment_prepare_impl(args: argparse.Namespace, *, label: str) -> int:
    project_dir = Path(args.project).resolve()
    if not _is_shipment_project_dir(project_dir):
        print(
            f"ERROR: not a shipment project directory (missing conf.py/index.rst): {project_dir}",
            file=sys.stderr,
        )
        return 2

    config = _read_project_config(
        project_dir, explicit_path=getattr(args, "config", None)
    )

    shipment_dir = (
        Path(args.shipment).resolve()
        if getattr(args, "shipment", None)
        else _default_shipment_dir(project_dir)
    )

    env = {
        "OSQAR_PROJECT_DIR": str(project_dir),
        "OSQAR_SHIPMENT_DIR": str(shipment_dir),
    }
    env.update(
        _reproducible_env(
            project_dir,
            reproducible=bool(getattr(args, "reproducible", True)),
        )
    )
    rc = _run_hooks(
        config,
        args=args,
        phase="pre",
        event="shipment.prepare",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    if args.clean:
        rc = cmd_shipment_clean(
            argparse.Namespace(
                project=str(project_dir), dry_run=args.dry_run, aggressive=False
            )
        )
        if rc != 0:
            return int(rc)

    if not getattr(args, "skip_build", False):
        # Optional: if a build command is configured, run it before tests.
        build_command = getattr(args, "build_command", None)
        if not build_command:
            commands = config.get("commands") if isinstance(config, dict) else None
            if isinstance(commands, dict) and isinstance(commands.get("build"), str):
                build_command = commands.get("build")

        if build_command:
            rc = cmd_shipment_run_build(
                argparse.Namespace(
                    project=str(project_dir),
                    command=str(build_command),
                    config=getattr(args, "config", None),
                    no_hooks=bool(getattr(args, "no_hooks", False)),
                    reproducible=bool(getattr(args, "reproducible", True)),
                )
            )
            if rc != 0:
                return int(rc)

    if not args.skip_tests:
        # Best-effort: if no script exists, continue (some shipments are docs-only).
        script = project_dir / (args.script or "build-and-test.sh")
        rc = cmd_shipment_run_tests(
            argparse.Namespace(
                project=str(project_dir),
                script=str(script.name),
                command=getattr(args, "test_command", None),
                config=getattr(args, "config", None),
                no_hooks=bool(getattr(args, "no_hooks", False)),
                reproducible=bool(getattr(args, "reproducible", True)),
            )
        )
        if rc != 0:
            return int(rc)

    rc = _run_docs_build(project_dir, shipment_dir, config=config)
    if rc != 0:
        return int(rc)

    # Bundle content: include implementation, tests, and analysis reports alongside docs.
    _copy_bundle_sources_and_reports(
        project_dir, shipment_dir, dry_run=bool(args.dry_run)
    )

    # Copy raw test reports into the shipped directory (optional but recommended).
    _copy_test_reports(
        project_dir,
        shipment_dir,
        dry_run=bool(args.dry_run),
        globs=_DEFAULT_TEST_REPORT_GLOBS,
    )

    # Code traceability check (source-level ID tags) against needs.json.
    if not bool(getattr(args, "skip_code_trace", False)):
        language = _detect_language(project_dir)
        needs_json = shipment_dir / "needs.json"
        code_trace_report = shipment_dir / "code_trace_report.json"
        rc_ct = cmd_code_trace(
            argparse.Namespace(
                root=str(shipment_dir),
                needs_json=str(needs_json) if needs_json.is_file() else None,
                json_report=str(code_trace_report),
                impl_dir=[
                    str(shipment_dir / "implementation" / "src"),
                    str(shipment_dir / "implementation" / "include"),
                    str(shipment_dir / "implementation" / "lib"),
                ],
                test_dir=_code_trace_test_dirs_for_shipment(
                    shipment_dir, language=language
                ),
                exclude=list(getattr(args, "exclude", []) or [])
                + [
                    "**/_build/**",
                    "_build/**",
                    "**/.venv/**",
                    ".venv/**",
                ],
                ext=None,
                max_bytes=None,
                enforce_req_in_impl=True,
                enforce_arch_in_impl=True,
                enforce_test_in_tests=True,
                enforce_no_unknown_ids=bool(
                    getattr(args, "enforce_no_unknown_ids", False)
                ),
            )
        )
        if rc_ct != 0:
            if bool(getattr(args, "code_trace_warn_only", False)):
                print(
                    f"WARNING: code-trace reported issues (rc={rc_ct}) but continuing due to --code-trace-warn-only",
                    file=sys.stderr,
                )
            else:
                return int(rc_ct)

    # Traceability report into shipment root.
    rc = cmd_shipment_traceability(
        argparse.Namespace(
            shipment=str(shipment_dir),
            needs_json=None,
            json_report=str(shipment_dir / DEFAULT_TRACEABILITY_REPORT),
            enforce_req_has_test=args.enforce_req_has_test,
            enforce_arch_traces_req=args.enforce_arch_traces_req,
            enforce_test_traces_req=args.enforce_test_traces_req,
        )
    )
    if rc != 0:
        return int(rc)

    if getattr(args, "doctor", False):
        # Create a pre-shipping status report inside the shipment directory.
        # Run after traceability report exists, but before checksums generation.
        doctor_report = shipment_dir / "doctor_report.json"
        d_rc = cmd_doctor(
            argparse.Namespace(
                project=str(project_dir),
                shipment=str(shipment_dir),
                json_report=str(doctor_report),
                traceability=True,
                needs_json=None,
                exclude=list(getattr(args, "exclude", []) or []),
                skip_checksums=True,
                skip_traceability=False,
                skip_shipment_checks=False,
                skip_env_checks=False,
                enforce_req_has_test=bool(getattr(args, "enforce_req_has_test", False)),
                enforce_arch_traces_req=bool(
                    getattr(args, "enforce_arch_traces_req", False)
                ),
                enforce_test_traces_req=bool(
                    getattr(args, "enforce_test_traces_req", False)
                ),
            )
        )
        if d_rc != 0:
            print(
                f"ERROR: doctor found issues in the would-be shipment (rc={d_rc}); aborting before checksums generation",
                file=sys.stderr,
            )
            return int(d_rc)

    # Checksums: generate and immediately verify.
    rc = cmd_shipment_checksums(
        argparse.Namespace(
            shipment=str(shipment_dir),
            manifest=str(shipment_dir / DEFAULT_CHECKSUM_MANIFEST),
            mode="generate",
            exclude=args.exclude,
        )
    )
    if rc != 0:
        return int(rc)

    rc = cmd_shipment_checksums(
        argparse.Namespace(
            shipment=str(shipment_dir),
            manifest=str(shipment_dir / DEFAULT_CHECKSUM_MANIFEST),
            mode="verify",
            exclude=args.exclude,
        )
    )
    if rc != 0:
        return int(rc)

    if args.archive:
        rc = cmd_shipment_package(
            argparse.Namespace(
                shipment=str(shipment_dir),
                output=args.archive_output,
                dry_run=args.dry_run,
            )
        )
        if rc != 0:
            return int(rc)

    print(f"{label} ready: {shipment_dir}")
    rc = _run_hooks(
        config,
        args=args,
        phase="post",
        event="shipment.prepare",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)
    return 0


def cmd_shipment_prepare(args: argparse.Namespace) -> int:
    return _shipment_prepare_impl(args, label="Shipment")


def _shipment_verify_impl(args: argparse.Namespace, *, label: str) -> int:
    shipment_dir = Path(args.shipment).resolve()
    if not shipment_dir.is_dir():
        print(f"ERROR: shipment directory not found: {shipment_dir}", file=sys.stderr)
        return 2

    # Integrator-side config (optional): do NOT trust configuration shipped inside the bundle.
    ws_root = Path(getattr(args, "config_root", ".")).expanduser().resolve()
    ws_config = _read_workspace_config(
        ws_root, explicit_path=getattr(args, "config", None)
    )

    env = {
        "OSQAR_SHIPMENT_DIR": str(shipment_dir),
        "OSQAR_WORKSPACE_ROOT": str(ws_root),
    }
    rc = _run_hooks(
        ws_config,
        args=args,
        phase="pre",
        event="shipment.verify",
        cwd=shipment_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    manifest = (
        Path(args.manifest).resolve()
        if getattr(args, "manifest", None)
        else (shipment_dir / DEFAULT_CHECKSUM_MANIFEST)
    )
    if not manifest.is_file():
        print(f"ERROR: checksum manifest not found: {manifest}", file=sys.stderr)
        return 2

    checks, warns, errs = _shipment_verify_static_checks(shipment_dir)

    checksums_report_data: Optional[dict] = None
    checksums_report_path: Optional[str] = None
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tf:
        tmp_checksums = Path(tf.name)
    try:
        rc = cmd_shipment_checksums(
            argparse.Namespace(
                shipment=str(shipment_dir),
                manifest=str(manifest),
                mode="verify",
                exclude=args.exclude,
                json_report=str(tmp_checksums),
            )
        )
        if tmp_checksums.is_file():
            checksums_report_path = str(tmp_checksums)
            try:
                data = json.loads(tmp_checksums.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    checksums_report_data = data
            except Exception:
                pass
        if rc != 0:
            # Hard failure: integrity failed.
            errs.append("checksums verify failed")
    finally:
        try:
            tmp_checksums.unlink(missing_ok=True)
        except Exception:
            pass

    trace_rc: Optional[int] = None
    trace_report: Optional[str] = None
    tmp_trace_report: Optional[Path] = None
    if args.traceability:
        if getattr(args, "json_report", None):
            report = Path(args.json_report).resolve()
        else:
            # Default: do not write into the received shipment directory.
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".json", delete=False
            ) as tf:
                tmp_trace_report = Path(tf.name)
            report = tmp_trace_report
        trace_rc = cmd_shipment_traceability(
            argparse.Namespace(
                shipment=str(shipment_dir),
                needs_json=args.needs_json,
                json_report=str(report),
                enforce_req_has_test=args.enforce_req_has_test,
                enforce_arch_traces_req=args.enforce_arch_traces_req,
                enforce_test_traces_req=args.enforce_test_traces_req,
            )
        )
        trace_report = str(report)
        if trace_rc != 0:
            errs.append("traceability check failed")

        # If traceability was requested but needs.json is missing, treat as error.
        needs_json = (
            _find_needs_json(shipment_dir)
            if not args.needs_json
            else Path(args.needs_json)
        )
        if needs_json is None or not Path(needs_json).is_file():
            errs.append("traceability requested but needs.json not found")

        if tmp_trace_report is not None:
            try:
                tmp_trace_report.unlink(missing_ok=True)
            except Exception:
                pass

    code_trace_rc: Optional[int] = None
    code_trace_report: Optional[str] = None
    tmp_code_trace_report: Optional[Path] = None
    if not bool(getattr(args, "skip_code_trace", False)):
        language = _detect_shipment_language(shipment_dir)
        needs_json_path = (
            Path(args.needs_json).resolve()
            if getattr(args, "needs_json", None)
            else (shipment_dir / "needs.json")
        )
        # Default: do not write into the received shipment directory.
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tf:
            tmp_code_trace_report = Path(tf.name)
        report = tmp_code_trace_report
        code_trace_rc = cmd_code_trace(
            argparse.Namespace(
                root=str(shipment_dir),
                needs_json=str(needs_json_path) if needs_json_path.is_file() else None,
                json_report=str(report),
                impl_dir=[
                    str(shipment_dir / "implementation" / "src"),
                    str(shipment_dir / "implementation" / "include"),
                    str(shipment_dir / "implementation" / "lib"),
                ],
                test_dir=_code_trace_test_dirs_for_shipment(
                    shipment_dir, language=language
                ),
                exclude=list(getattr(args, "exclude", []) or [])
                + [
                    "**/_build/**",
                    "_build/**",
                    "**/.venv/**",
                    ".venv/**",
                ],
                ext=None,
                max_bytes=None,
                enforce_req_in_impl=True,
                enforce_arch_in_impl=True,
                enforce_test_in_tests=True,
                enforce_no_unknown_ids=bool(
                    getattr(args, "enforce_no_unknown_ids", False)
                ),
            )
        )
        code_trace_report = str(report)
        if code_trace_rc != 0:
            if bool(getattr(args, "code_trace_warn_only", False)):
                warns.append("code-trace check reported issues")
            else:
                errs.append("code-trace check failed")

        if tmp_code_trace_report is not None:
            try:
                tmp_code_trace_report.unlink(missing_ok=True)
            except Exception:
                pass

    strict = bool(getattr(args, "strict", False))
    rc_final = 0
    if errs:
        rc_final = 1
    elif strict and (warns or errs):
        rc_final = 1

    if getattr(args, "report_json", None):
        out = Path(args.report_json).expanduser().resolve()
        report: dict[str, object] = {
            "schema": "osqar.shipment_verify_report.v1",
            "generated_at": _utc_now_iso(),
            "shipment": str(shipment_dir),
            "manifest": str(manifest),
            "checksums_rc": int(rc),
            "checksums_report": checksums_report_data,
            "traceability": bool(args.traceability),
            "traceability_rc": int(trace_rc) if trace_rc is not None else None,
            "traceability_report": trace_report,
            "code_trace": not bool(getattr(args, "skip_code_trace", False)),
            "code_trace_rc": int(code_trace_rc) if code_trace_rc is not None else None,
            "code_trace_report": code_trace_report,
            "warnings": warns,
            "errors": errs,
            "checks": checks,
            "metadata": _read_project_metadata(shipment_dir),
            "needs_summary": _read_needs_summary_from_shipment(shipment_dir),
        }
        _write_json_report(out, report)
        print(f"Wrote shipment verify report: {out}")

    if rc_final == 0:
        # Optional integrator-side extra verification command(s)
        extra_cmds = list(getattr(args, "verify_command", []) or [])
        for cmd in extra_cmds:
            vrc = _run_command_string(str(cmd), cwd=shipment_dir, env=env)
            if vrc != 0:
                errs.append("custom verify command failed")
                rc_final = 1
                break

    if rc_final == 0:
        print(f"{label} passed.")
        rc2 = _run_hooks(
            ws_config,
            args=args,
            phase="post",
            event="shipment.verify",
            cwd=shipment_dir,
            env=env,
        )
        return 0 if rc2 == 0 else int(rc2)

    print(f"{label} FAILED.")
    _run_hooks(
        ws_config,
        args=args,
        phase="post",
        event="shipment.verify",
        cwd=shipment_dir,
        env=env,
    )
    return 1


def cmd_shipment_verify(args: argparse.Namespace) -> int:
    return _shipment_verify_impl(args, label="Shipment verification")


def _iter_shipment_dirs(root: Path, *, recursive: bool) -> list[Path]:
    root = root.resolve()
    if not root.exists():
        return []

    results: set[Path] = set()

    # Workspace operations typically target built shipment directories, which by
    # default live under `<project>/_build/html`. Do not exclude `_build`/`build`/`target`
    # here, otherwise the default layout becomes undiscoverable.
    ignored_scan_names = _IGNORED_DIR_NAMES - {"_build", "build", "target"}

    def consider(candidate: Path) -> None:
        if not candidate.is_dir():
            return
        if any(part in ignored_scan_names for part in candidate.parts):
            return
        manifest = candidate / DEFAULT_CHECKSUM_MANIFEST
        if manifest.is_file():
            results.add(candidate)

    if root.is_dir() and (root / DEFAULT_CHECKSUM_MANIFEST).is_file():
        return [root]

    if not recursive:
        if not root.is_dir():
            return []
        for child in sorted(root.iterdir()):
            consider(child)
        return sorted(results)

    if root.is_dir():
        for manifest in root.rglob(DEFAULT_CHECKSUM_MANIFEST.name):
            if not manifest.is_file():
                continue
            consider(manifest.parent)

    return sorted(results)


def _unique_name(preferred: str, used: set[str]) -> str:
    if preferred not in used:
        used.add(preferred)
        return preferred
    i = 2
    while True:
        candidate = f"{preferred}-{i}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        i += 1


def cmd_workspace_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ws_config = _read_workspace_config(
        root, explicit_path=getattr(args, "config", None)
    )
    shipments = _iter_shipment_dirs(root, recursive=bool(args.recursive))
    if not shipments:
        print(f"No shipments found under: {root}")
        return 1

    effective_excludes = _config_defaults_exclude(ws_config) + list(
        getattr(args, "exclude", []) or []
    )

    env = {
        "OSQAR_WORKSPACE_ROOT": str(root),
    }
    rc = _run_hooks(
        ws_config,
        args=args,
        phase="pre",
        event="workspace.verify",
        cwd=Path.cwd(),
        env=env,
    )
    if rc != 0:
        return int(rc)

    doctor_out_dir: Optional[Path] = None
    if getattr(args, "doctor", False) and getattr(args, "json_report", None):
        doctor_out_dir = Path(args.json_report).expanduser().resolve().parent / "doctor"
        doctor_out_dir.mkdir(parents=True, exist_ok=True)

    failures: list[dict[str, object]] = []
    successes: list[dict[str, object]] = []

    for shipment_dir in shipments:
        print(f"\n== Verifying shipment: {shipment_dir}")

        ship_env = {
            **env,
            "OSQAR_SHIPMENT_DIR": str(shipment_dir),
        }
        rc = _run_hooks(
            ws_config,
            args=args,
            phase="pre",
            event="workspace.verify.shipment",
            cwd=Path(shipment_dir),
            env=ship_env,
        )
        if rc != 0:
            failures.append(
                {"shipment": str(shipment_dir), "rc": int(rc), "hook": "pre"}
            )
            if not args.continue_on_error:
                break
            continue

        rc = cmd_shipment_verify(
            argparse.Namespace(
                shipment=str(shipment_dir),
                manifest=None,
                exclude=effective_excludes,
                traceability=bool(args.traceability),
                needs_json=args.needs_json,
                json_report=None,
                report_json=None,
                strict=False,
                config=getattr(args, "config", None),
                config_root=str(root),
                verify_command=list(getattr(args, "verify_command", []) or []),
                no_hooks=bool(getattr(args, "no_hooks", False)),
                enforce_req_has_test=bool(args.enforce_req_has_test),
                enforce_arch_traces_req=bool(args.enforce_arch_traces_req),
                enforce_test_traces_req=bool(args.enforce_test_traces_req),
            )
        )

        doctor_rc: Optional[int] = None
        doctor_report: Optional[str] = None
        if getattr(args, "doctor", False):
            out = None
            if doctor_out_dir is not None:
                out = doctor_out_dir / f"{shipment_dir.name}.json"
            doctor_rc = int(
                cmd_doctor(
                    argparse.Namespace(
                        project=".",
                        shipment=str(shipment_dir),
                        json_report=str(out) if out is not None else None,
                        traceability=bool(getattr(args, "traceability", False)),
                        needs_json=getattr(args, "needs_json", None),
                        exclude=list(effective_excludes),
                        skip_checksums=True,
                        skip_traceability=not bool(
                            getattr(args, "traceability", False)
                        ),
                        skip_shipment_checks=False,
                        skip_env_checks=True,
                        enforce_req_has_test=bool(
                            getattr(args, "enforce_req_has_test", False)
                        ),
                        enforce_arch_traces_req=bool(
                            getattr(args, "enforce_arch_traces_req", False)
                        ),
                        enforce_test_traces_req=bool(
                            getattr(args, "enforce_test_traces_req", False)
                        ),
                    )
                )
            )
            doctor_report = str(out) if out is not None else None

        entry = {
            "shipment": str(shipment_dir),
            "rc": int(rc),
            "metadata": _read_project_metadata(shipment_dir),
            "doctor_rc": int(doctor_rc) if doctor_rc is not None else None,
            "doctor_report": doctor_report,
        }
        if rc == 0:
            successes.append(entry)
            _run_hooks(
                ws_config,
                args=args,
                phase="post",
                event="workspace.verify.shipment",
                cwd=Path(shipment_dir),
                env=ship_env,
            )
            continue

        failures.append(entry)
        _run_hooks(
            ws_config,
            args=args,
            phase="post",
            event="workspace.verify.shipment",
            cwd=Path(shipment_dir),
            env=ship_env,
        )
        if not args.continue_on_error:
            break

    if args.json_report:
        report_path = Path(args.json_report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "root": str(root),
            "recursive": bool(args.recursive),
            "traceability": bool(args.traceability),
            "successes": successes,
            "failures": failures,
        }
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"\nWrote workspace report: {report_path}")

    if failures:
        print(
            f"\nWorkspace verify FAILED: {len(failures)} / {len(successes) + len(failures)}"
        )
        _run_hooks(
            ws_config,
            args=args,
            phase="post",
            event="workspace.verify",
            cwd=Path.cwd(),
            env=env,
        )
        return 1

    print(f"\nWorkspace verify OK: {len(successes)}")
    rc = _run_hooks(
        ws_config,
        args=args,
        phase="post",
        event="workspace.verify",
        cwd=Path.cwd(),
        env=env,
    )
    if rc != 0:
        return int(rc)
    return 0


def cmd_workspace_intake(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else None
    output_dir = Path(args.output).resolve()

    ws_root = root if root is not None else Path.cwd()
    ws_config = _read_workspace_config(
        ws_root, explicit_path=getattr(args, "config", None)
    )

    shipments: list[Path]
    if args.shipments:
        shipments = [Path(s).resolve() for s in args.shipments]
    elif root is not None:
        shipments = _iter_shipment_dirs(root, recursive=bool(args.recursive))
    else:
        print("ERROR: provide either shipment paths or --root", file=sys.stderr)
        return 2

    if not shipments:
        print("No shipments to intake.")
        return 1

    effective_excludes = _config_defaults_exclude(ws_config) + list(
        getattr(args, "exclude", []) or []
    )

    env = {
        "OSQAR_WORKSPACE_ROOT": str(ws_root),
        "OSQAR_WORKSPACE_OUTPUT": str(output_dir),
    }
    rc = _run_hooks(
        ws_config,
        args=args,
        phase="pre",
        event="workspace.intake",
        cwd=Path.cwd(),
        env=env,
    )
    if rc != 0:
        return int(rc)

    if output_dir.exists():
        if not args.force:
            print(
                f"ERROR: output already exists (use --force to overwrite): {output_dir}",
                file=sys.stderr,
            )
            return 2
        try:
            _safe_rmtree(output_dir, dry_run=bool(args.dry_run))
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    shipments_root = output_dir / "shipments"
    reports_root = output_dir / "reports"
    intake_report_path = output_dir / "intake_report.json"
    overview_json_path = output_dir / "subproject_overview.json"

    if not args.dry_run:
        shipments_root.mkdir(parents=True, exist_ok=True)
        reports_root.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    items: list[dict[str, object]] = []
    any_failures = False

    for shipment_dir in shipments:
        shipment_dir = shipment_dir.resolve()
        name = _unique_name(shipment_dir.name, used_names)
        print(f"\n== Intake shipment: {shipment_dir} -> {name}")

        manifest = shipment_dir / DEFAULT_CHECKSUM_MANIFEST
        verify_rc = cmd_shipment_checksums(
            argparse.Namespace(
                shipment=str(shipment_dir),
                manifest=str(manifest),
                mode="verify",
                exclude=effective_excludes,
            )
        )

        dest = shipments_root / name
        if verify_rc == 0:
            if args.dry_run:
                print(f"DRY-RUN: would copy {shipment_dir} -> {dest}")
            else:
                shutil.copytree(shipment_dir, dest)

            trace_rc: Optional[int] = None
            trace_report: Optional[str] = None
            if args.traceability:
                trace_out = reports_root / name / "traceability_report.integrator.json"
                if args.dry_run:
                    print(f"DRY-RUN: would run traceability -> {trace_out}")
                    trace_rc = 0
                    trace_report = str(trace_out)
                else:
                    trace_out.parent.mkdir(parents=True, exist_ok=True)
                    trace_rc = cmd_shipment_traceability(
                        argparse.Namespace(
                            shipment=str(dest),
                            needs_json=args.needs_json,
                            json_report=str(trace_out),
                            enforce_req_has_test=bool(args.enforce_req_has_test),
                            enforce_arch_traces_req=bool(args.enforce_arch_traces_req),
                            enforce_test_traces_req=bool(args.enforce_test_traces_req),
                        )
                    )
                    trace_report = str(trace_out)

                if trace_rc != 0:
                    any_failures = True
                    if not args.continue_on_error:
                        items.append(
                            {
                                "name": name,
                                "source": str(shipment_dir),
                                "dest": str(dest),
                                "checksums_rc": int(verify_rc),
                                "traceability_rc": int(trace_rc),
                                "traceability_report": trace_report,
                            }
                        )
                        break

            items.append(
                {
                    "name": name,
                    "source": str(shipment_dir),
                    "dest": str(dest),
                    "checksums_rc": int(verify_rc),
                    "traceability_rc": int(trace_rc) if trace_rc is not None else None,
                    "traceability_report": trace_report,
                    "doctor_rc": None,
                    "doctor_report": None,
                    "metadata": _read_project_metadata(dest),
                    "needs_summary": _read_needs_summary_from_shipment(dest),
                    "docs_entrypoint": (
                        f"shipments/{name}/index.html"
                        if (dest / "index.html").is_file()
                        else None
                    ),
                }
            )

            if getattr(args, "doctor", False):
                doc_out = reports_root / name / "doctor_report.integrator.json"
                if args.dry_run:
                    print(f"DRY-RUN: would run doctor -> {doc_out}")
                    items[-1]["doctor_rc"] = 0
                    items[-1]["doctor_report"] = str(doc_out)
                else:
                    doc_out.parent.mkdir(parents=True, exist_ok=True)
                    drc = cmd_doctor(
                        argparse.Namespace(
                            project=".",
                            shipment=str(dest),
                            json_report=str(doc_out),
                            traceability=bool(getattr(args, "traceability", False)),
                            needs_json=getattr(args, "needs_json", None),
                            exclude=list(effective_excludes),
                            skip_checksums=True,
                            skip_traceability=not bool(
                                getattr(args, "traceability", False)
                            ),
                            skip_shipment_checks=False,
                            skip_env_checks=True,
                            enforce_req_has_test=bool(
                                getattr(args, "enforce_req_has_test", False)
                            ),
                            enforce_arch_traces_req=bool(
                                getattr(args, "enforce_arch_traces_req", False)
                            ),
                            enforce_test_traces_req=bool(
                                getattr(args, "enforce_test_traces_req", False)
                            ),
                        )
                    )
                    items[-1]["doctor_rc"] = int(drc)
                    items[-1]["doctor_report"] = str(doc_out)
                    if drc != 0:
                        any_failures = True
                        if not args.continue_on_error:
                            break
            continue

        any_failures = True
        items.append(
            {
                "name": name,
                "source": str(shipment_dir),
                "dest": None,
                "checksums_rc": int(verify_rc),
                "traceability_rc": None,
                "traceability_report": None,
                "metadata": _read_project_metadata(shipment_dir),
            }
        )
        if not args.continue_on_error:
            break

    if args.dry_run:
        print("\nDRY-RUN: would write intake report and archive checksums.")
        return 0 if not any_failures else 1

    output_dir.mkdir(parents=True, exist_ok=True)
    intake_report = {
        "output": str(output_dir),
        "shipments": items,
        "failures": any_failures,
    }
    intake_report_path.write_text(
        json.dumps(intake_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nWrote intake report: {intake_report_path}")

    overview = {
        "title": "Subproject overview",
        "generated_at": _utc_now_iso(),
        "root": str(root) if root is not None else None,
        "recursive": bool(getattr(args, "recursive", False)),
        "checksums": True,
        "traceability": bool(getattr(args, "traceability", False)),
        "doctor": bool(getattr(args, "doctor", False)),
        "output": str(output_dir),
        "projects": items,
    }
    overview_json_path.write_text(
        json.dumps(overview, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"Wrote Subproject overview JSON: {overview_json_path}")

    sphinx_src = output_dir / "_sphinx"
    html_out = output_dir / "_build/html"
    _write_workspace_overview_sphinx_source(
        source_dir=sphinx_src,
        html_out_dir=html_out,
        overview=overview,
    )

    print(f"Building intake overview HTML: {sphinx_src} -> {html_out}")
    rc = _run_sphinx_build(sphinx_src, html_out)
    if rc != 0:
        return int(rc)

    try:
        shutil.rmtree(sphinx_src)
    except OSError:
        pass

    entry = html_out / "index.html"
    if entry.is_file():
        print(entry)
    else:
        print(f"ERROR: overview entrypoint not found: {entry}", file=sys.stderr)
        return 2

    # Create an archive-level checksum manifest covering everything in the intake output.
    archive_manifest = output_dir / DEFAULT_CHECKSUM_MANIFEST
    rc = checksums_cli(["--root", str(output_dir), "--output", str(archive_manifest)])
    if rc != 0:
        return int(rc)
    print(f"Wrote archive manifest: {archive_manifest}")

    rc = _run_hooks(
        ws_config,
        args=args,
        phase="post",
        event="workspace.intake",
        cwd=Path.cwd(),
        env=env,
    )
    if rc != 0:
        return int(rc)

    return 0 if not any_failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="osqar", description="OSQAr helper CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build_docs = sub.add_parser(
        "build-docs",
        help="Build Sphinx HTML output (shorthand for 'shipment build-docs')",
    )
    p_build_docs.add_argument(
        "--project",
        default=".",
        help="Shipment project directory (default: .; must contain conf.py/index.rst)",
    )
    p_build_docs.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_build_docs.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_build_docs.add_argument(
        "--output",
        default=None,
        help="Output directory (default: <project>/_build/html)",
    )
    p_build_docs.add_argument(
        "--open",
        action="store_true",
        help="Open the built index.html in your default browser",
    )
    p_build_docs.set_defaults(func=cmd_shipment_build_docs)

    p_open = sub.add_parser(
        "open-docs",
        help="Open built HTML documentation (index.html) in your default browser",
    )
    open_group = p_open.add_mutually_exclusive_group(required=False)
    open_group.add_argument(
        "--project",
        default=".",
        help="Project directory (default: .; opens <project>/_build/html/index.html)",
    )
    open_group.add_argument(
        "--shipment",
        default=None,
        help="Shipment directory (opens <shipment>/index.html)",
    )
    open_group.add_argument(
        "--path",
        default=None,
        help="HTML file or directory (if directory: opens <dir>/index.html)",
    )
    p_open.add_argument(
        "--print-only",
        action="store_true",
        help="Only print the resolved index.html path",
    )
    p_open.set_defaults(func=cmd_open_docs)

    p_doc = sub.add_parser(
        "doctor",
        help="Full status report for debugging (environment + optional shipment consistency checks)",
    )
    p_doc.add_argument(
        "--project",
        default=".",
        help="Project directory to check (default: .)",
    )
    p_doc.add_argument(
        "--shipment",
        default=None,
        help="Built shipment directory to check (default: <project>/_build/html if present)",
    )
    p_doc.add_argument(
        "--json-report",
        default=None,
        help="Write a machine-readable JSON report to this path",
    )
    p_doc.add_argument(
        "--traceability",
        action="store_true",
        help="Also run traceability checks if needs.json is available (non-writing)",
    )
    p_doc.add_argument(
        "--needs-json",
        default=None,
        help="Override needs.json path for --traceability",
    )
    p_doc.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum verify (repeatable)",
    )
    p_doc.add_argument(
        "--skip-checksums",
        action="store_true",
        help="Skip checksum verification even if SHA256SUMS is present",
    )
    p_doc.add_argument(
        "--skip-traceability",
        action="store_true",
        help="Skip traceability checks even if needs.json is present",
    )
    p_doc.add_argument(
        "--skip-shipment-checks",
        action="store_true",
        help="Skip shipment artifact checks (index.html, needs.json, SHA256SUMS, metadata)",
    )
    p_doc.add_argument(
        "--skip-env-checks",
        action="store_true",
        help="Skip environment checks (useful when diagnosing received shipments)",
    )
    p_doc.add_argument("--enforce-req-has-test", action="store_true")
    p_doc.add_argument("--enforce-arch-traces-req", action="store_true")
    p_doc.add_argument("--enforce-test-traces-req", action="store_true")
    p_doc.set_defaults(func=cmd_doctor)

    p_new = sub.add_parser(
        "new", help="Create a new OSQAr project from a language template"
    )
    p_new.add_argument("--language", choices=sorted(TEMPLATES.keys()), required=True)
    p_new.add_argument(
        "--name", required=True, help="Project name (used for folder name by default)"
    )
    p_new.add_argument(
        "--destination", default=None, help="Destination directory (default: ./<name>)"
    )
    p_new.add_argument(
        "--template",
        choices=["basic", "example"],
        default="basic",
        help="Template profile (default: basic; 'example' copies the full reference examples)",
    )
    p_new.add_argument(
        "--force", action="store_true", help="Overwrite destination if it exists"
    )
    p_new.set_defaults(func=cmd_new)

    p_tr = sub.add_parser(
        "traceability", help="Run traceability checks on an exported needs.json"
    )
    p_tr.add_argument("needs_json", type=Path, help="Path to needs.json")
    p_tr.add_argument(
        "--json-report", type=Path, default=None, help="Write JSON report to this path"
    )
    p_tr.add_argument(
        "--enforce-req-has-test",
        action="store_true",
        help="Also enforce REQ_* → TEST_* coverage",
    )
    p_tr.add_argument(
        "--enforce-arch-traces-req",
        action="store_true",
        help="Also enforce ARCH_* → REQ_* coverage",
    )
    p_tr.add_argument(
        "--enforce-test-traces-req",
        action="store_true",
        help="Also enforce TEST_* → REQ_* coverage",
    )
    p_tr.set_defaults(func=cmd_traceability)

    p_ct = sub.add_parser(
        "code-trace",
        help=(
            "Scan implementation/tests for need IDs in comments and optionally enforce coverage against needs.json"
        ),
    )
    p_ct.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Project root directory to scan (default: .)",
    )
    p_ct.add_argument(
        "--needs-json",
        type=Path,
        default=None,
        help="Optional needs.json to define expected REQ_/ARCH_/TEST_ IDs",
    )
    p_ct.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write machine-readable JSON report to this path",
    )
    p_ct.add_argument(
        "--impl-dir",
        action="append",
        default=[],
        help="Implementation directory/file relative to --root (repeatable; default: auto-detect)",
    )
    p_ct.add_argument(
        "--test-dir",
        action="append",
        default=[],
        help="Test directory/file relative to --root (repeatable; default: auto-detect)",
    )
    p_ct.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) relative to --root (repeatable)",
    )
    p_ct.add_argument(
        "--ext",
        action="append",
        default=[],
        help="File extension to scan, including leading dot (repeatable)",
    )
    p_ct.add_argument(
        "--max-bytes",
        type=int,
        default=2_000_000,
        help="Skip files larger than this many bytes (default: 2000000)",
    )
    p_ct.add_argument(
        "--enforce-req-in-impl",
        action="store_true",
        help="Fail if any REQ_* from needs.json is not found in implementation sources",
    )
    p_ct.add_argument(
        "--enforce-arch-in-impl",
        action="store_true",
        help="Fail if any ARCH_* from needs.json is not found in implementation sources",
    )
    p_ct.add_argument(
        "--enforce-test-in-tests",
        action="store_true",
        help="Fail if any TEST_* from needs.json is not found in test sources",
    )
    p_ct.add_argument(
        "--enforce-no-unknown-ids",
        action="store_true",
        help="Fail if code mentions IDs that are not present in needs.json",
    )
    p_ct.set_defaults(func=cmd_code_trace)

    p_sum = sub.add_parser(
        "checksum", help="Generate or verify shipment checksum manifests"
    )
    sum_sub = p_sum.add_subparsers(dest="checksum_cmd", required=True)

    p_gen = sum_sub.add_parser("generate", help="Generate SHA256SUMS for a directory")
    p_gen.add_argument("--root", type=Path, required=True)
    p_gen.add_argument("--output", type=Path, required=True)
    p_gen.add_argument(
        "--exclude", action="append", default=[], help="Exclude glob (repeatable)"
    )
    p_gen.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write machine-readable JSON report to this path",
    )
    p_gen.set_defaults(func=cmd_checksums_generate)

    p_ver = sum_sub.add_parser("verify", help="Verify a directory against SHA256SUMS")
    p_ver.add_argument("--root", type=Path, required=True)
    p_ver.add_argument("--manifest", type=Path, required=True)
    p_ver.add_argument(
        "--exclude", action="append", default=[], help="Exclude glob (repeatable)"
    )
    p_ver.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write machine-readable JSON report to this path",
    )
    p_ver.set_defaults(func=cmd_checksums_verify)

    p_fw = sub.add_parser(
        "framework",
        help="Framework bundle operations (used for CI/release packaging)",
    )
    fw_sub = p_fw.add_subparsers(dest="framework_cmd", required=True)
    p_fwb = fw_sub.add_parser(
        "bundle",
        help="Assemble a framework bundle directory (docs + CLI + templates)",
    )
    p_fwb.add_argument(
        "--version",
        required=True,
        help="Release/tag version, e.g. v0.4.2",
    )
    p_fwb.add_argument(
        "--docs-dir",
        default=Path("_build/html"),
        help="Path to built framework HTML docs (default: _build/html)",
    )
    p_fwb.add_argument(
        "--output-dir",
        default=Path("_dist"),
        help="Output/staging directory to create bundle under (default: _dist)",
    )
    p_fwb.set_defaults(func=cmd_framework_bundle)

    p_ship = sub.add_parser(
        "shipment", help="Work with shippable evidence bundles (build, clean, verify)"
    )
    ship_sub = p_ship.add_subparsers(dest="shipment_cmd", required=True)

    p_prep = ship_sub.add_parser(
        "prepare",
        help="Build docs, run traceability + checksums, and optionally archive a shippable evidence bundle",
    )
    p_prep.add_argument("--project", required=True, help="Shipment project directory")
    p_prep.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_prep.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_prep.add_argument(
        "--shipment",
        default=None,
        help="Shipment output directory (default: <project>/_build/html)",
    )
    p_prep.add_argument(
        "--clean", action="store_true", help="Clean generated outputs before building"
    )
    p_prep.add_argument(
        "--dry-run", action="store_true", help="Print destructive ops without executing"
    )
    p_prep.add_argument(
        "--script",
        default=None,
        help="Test/build script name (default: build-and-test.sh)",
    )
    p_prep.add_argument(
        "--reproducible",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable reproducible build/test mode for this shipment (default: enabled)",
    )
    p_prep.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip running the build step (if commands.build is configured)",
    )
    p_prep.add_argument(
        "--build-command",
        dest="build_command",
        default=None,
        help="Override build command (otherwise use commands.build from osqar_project.json)",
    )
    p_prep.add_argument(
        "--skip-tests", action="store_true", help="Skip running the test/build script"
    )
    p_prep.add_argument(
        "--test-command",
        dest="test_command",
        default=None,
        help="Override test/build command (otherwise use commands.test from osqar_project.json or --script)",
    )
    p_prep.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum generation",
    )
    p_prep.add_argument("--enforce-req-has-test", action="store_true")
    p_prep.add_argument("--enforce-arch-traces-req", action="store_true")
    p_prep.add_argument("--enforce-test-traces-req", action="store_true")
    p_prep.add_argument(
        "--archive",
        action="store_true",
        help="Also create a .zip of the shipment directory",
    )
    p_prep.add_argument(
        "--archive-output",
        default=None,
        help="Archive output path (default: <shipment>.zip)",
    )
    p_prep.add_argument(
        "--doctor",
        action="store_true",
        help="Also write a doctor report into the shipped directory before generating checksums",
    )
    p_prep.add_argument(
        "--skip-code-trace",
        action="store_true",
        help="Skip source-level code traceability check (code-trace)",
    )
    p_prep.add_argument(
        "--code-trace-warn-only",
        action="store_true",
        help="Do not fail the shipment if code-trace reports issues; emit warnings instead",
    )
    p_prep.add_argument(
        "--enforce-no-unknown-ids",
        action="store_true",
        help="Fail code-trace if unknown IDs are found in code (optional)",
    )
    p_prep.set_defaults(func=cmd_shipment_prepare)

    p_ver = ship_sub.add_parser(
        "verify",
        help="Verify a received shipment directory (integrity + optional traceability re-check)",
    )
    p_ver.add_argument("--shipment", required=True, help="Received shipment directory")
    p_ver.add_argument(
        "--config-root",
        default=".",
        help="Root directory for workspace config lookup (default: .)",
    )
    p_ver.add_argument(
        "--config",
        default=None,
        help="Workspace configuration JSON (default: <config-root>/osqar_workspace.json)",
    )
    p_ver.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_ver.add_argument(
        "--verify-command",
        action="append",
        default=[],
        help="Extra integrator-side verification command to run after built-in checks (repeatable)",
    )
    p_ver.add_argument(
        "--manifest",
        default=None,
        help="Checksum manifest (default: <shipment>/SHA256SUMS)",
    )
    p_ver.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum verify",
    )
    p_ver.add_argument(
        "--traceability",
        action="store_true",
        help="Also validate needs.json traceability",
    )
    p_ver.add_argument("--needs-json", default=None, help="Override needs.json path")
    p_ver.add_argument(
        "--json-report",
        default=None,
        help="Write verification-side traceability report",
    )
    p_ver.add_argument(
        "--report-json",
        default=None,
        help="Write a machine-readable verification summary report",
    )
    p_ver.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures",
    )
    p_ver.add_argument(
        "--skip-code-trace",
        action="store_true",
        help="Skip source-level code traceability check (code-trace)",
    )
    p_ver.add_argument(
        "--code-trace-warn-only",
        action="store_true",
        help="Do not fail verification if code-trace reports issues; emit warnings instead",
    )
    p_ver.add_argument(
        "--enforce-no-unknown-ids",
        action="store_true",
        help="Fail code-trace if unknown IDs are found in code (optional)",
    )
    p_ver.add_argument("--enforce-req-has-test", action="store_true")
    p_ver.add_argument("--enforce-arch-traces-req", action="store_true")
    p_ver.add_argument("--enforce-test-traces-req", action="store_true")
    p_ver.set_defaults(func=cmd_shipment_verify)

    p_list = ship_sub.add_parser(
        "list", help="Discover shipment projects under a directory"
    )
    p_list.add_argument(
        "--root", default=".", help="Root directory to scan (default: .)"
    )
    p_list.add_argument(
        "--recursive", action="store_true", help="Recursively scan for conf.py"
    )
    p_list.add_argument("--format", choices=["pretty", "paths"], default="pretty")
    p_list.set_defaults(func=cmd_shipment_list)

    p_build = ship_sub.add_parser(
        "build-docs", help="Build Sphinx HTML output for a shipment project"
    )
    p_build.add_argument(
        "--project",
        default=".",
        help="Shipment project directory (default: .; must contain conf.py/index.rst)",
    )
    p_build.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_build.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_build.add_argument(
        "--output",
        default=None,
        help="Output directory (default: <project>/_build/html)",
    )
    p_build.add_argument(
        "--open",
        action="store_true",
        help="Open the built index.html in your default browser",
    )
    p_build.set_defaults(func=cmd_shipment_build_docs)

    p_tests = ship_sub.add_parser(
        "run-tests", help="Run a shipment's build-and-test script"
    )
    p_tests.add_argument("--project", required=True, help="Shipment project directory")
    p_tests.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_tests.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_tests.add_argument(
        "--command",
        default=None,
        help="Override test/build command (otherwise read commands.test from osqar_project.json or use --script)",
    )
    p_tests.add_argument(
        "--script", default=None, help="Script name (default: build-and-test.sh)"
    )
    p_tests.add_argument(
        "--reproducible",
        action="store_true",
        help="Enable reproducible mode for this run (sets OSQAR_REPRODUCIBLE=1; best-effort SOURCE_DATE_EPOCH)",
    )
    p_tests.set_defaults(func=cmd_shipment_run_tests)

    p_build = ship_sub.add_parser(
        "run-build",
        help="Run a project-specific build command (configured per project)",
    )
    p_build.add_argument("--project", required=True, help="Shipment project directory")
    p_build.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_build.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_build.add_argument(
        "--command",
        default=None,
        help="Override build command (otherwise read commands.build from <project>/osqar_project.json)",
    )
    p_build.add_argument(
        "--reproducible",
        action="store_true",
        help="Enable reproducible mode for this run (sets OSQAR_REPRODUCIBLE=1; best-effort SOURCE_DATE_EPOCH)",
    )
    p_build.set_defaults(func=cmd_shipment_run_build)

    p_clean = ship_sub.add_parser(
        "clean", help="Remove generated outputs (conservative by default)"
    )
    p_clean.add_argument("--project", required=True, help="Shipment project directory")
    p_clean.add_argument(
        "--dry-run", action="store_true", help="Print what would be removed"
    )
    p_clean.add_argument(
        "--aggressive", action="store_true", help="Also remove 'diagrams/' if present"
    )
    p_clean.set_defaults(func=cmd_shipment_clean)

    p_tr2 = ship_sub.add_parser(
        "traceability", help="Run traceability checks for a built shipment directory"
    )
    p_tr2.add_argument(
        "--shipment",
        required=True,
        help="Shipment directory (usually <project>/_build/html)",
    )
    p_tr2.add_argument(
        "--needs-json",
        default=None,
        help="Override needs.json path (default: <shipment>/needs.json)",
    )
    p_tr2.add_argument(
        "--json-report",
        default=None,
        help="Write JSON report (default: <shipment>/traceability_report.json)",
    )
    p_tr2.add_argument("--enforce-req-has-test", action="store_true")
    p_tr2.add_argument("--enforce-arch-traces-req", action="store_true")
    p_tr2.add_argument("--enforce-test-traces-req", action="store_true")
    p_tr2.set_defaults(func=cmd_shipment_traceability)

    p_cs = ship_sub.add_parser(
        "checksums",
        help="Generate or verify checksum manifests for a shipment directory",
    )
    p_cs.add_argument("--shipment", required=True, help="Shipment directory")
    p_cs.add_argument(
        "--manifest",
        default=None,
        help="Manifest path (default: <shipment>/SHA256SUMS)",
    )
    p_cs.add_argument(
        "--exclude", action="append", default=[], help="Exclude glob (repeatable)"
    )
    p_cs.add_argument(
        "--json-report",
        default=None,
        help="Write machine-readable JSON report to this path",
    )
    p_cs.add_argument("mode", choices=["generate", "verify"], help="Operation")
    p_cs.set_defaults(func=cmd_shipment_checksums)

    p_rep = ship_sub.add_parser(
        "copy-test-reports", help="Copy raw JUnit XML into the shipment directory"
    )
    p_rep.add_argument("--project", required=True, help="Shipment project directory")
    p_rep.add_argument(
        "--shipment",
        default=None,
        help="Shipment directory (default: <project>/_build/html)",
    )
    p_rep.add_argument(
        "--glob",
        action="append",
        default=[],
        help="Glob to match report files (repeatable)",
    )
    p_rep.add_argument("--dry-run", action="store_true")
    p_rep.set_defaults(func=cmd_shipment_copy_test_reports)

    p_pkg = ship_sub.add_parser(
        "package", help="Archive a shipment directory into a .zip"
    )
    p_pkg.add_argument("--shipment", required=True, help="Shipment directory")
    p_pkg.add_argument(
        "--output",
        default=None,
        help="Archive output path (default: <shipment>.zip)",
    )
    p_pkg.add_argument("--dry-run", action="store_true")
    p_pkg.set_defaults(func=cmd_shipment_package)

    p_meta = ship_sub.add_parser(
        "metadata",
        help="Add project metadata (descriptive info, URLs, origin) to a shipment",
    )
    meta_sub = p_meta.add_subparsers(dest="metadata_cmd", required=True)
    p_meta_write = meta_sub.add_parser(
        "write", help="Write osqar_project.json into a shipment directory"
    )
    p_meta_write.add_argument("--shipment", required=True, help="Shipment directory")
    p_meta_write.add_argument(
        "--name", default=None, help="Human-friendly project name"
    )
    p_meta_write.add_argument(
        "--id", dest="project_id", default=None, help="Stable project identifier"
    )
    p_meta_write.add_argument(
        "--version", default=None, help="Project/shipment version"
    )
    p_meta_write.add_argument("--description", default=None, help="Short description")
    p_meta_write.add_argument(
        "--url", action="append", default=[], help="URL as KEY=VALUE (repeatable)"
    )
    p_meta_write.add_argument(
        "--origin",
        action="append",
        default=[],
        help="Origin as KEY=VALUE (repeatable), e.g. url=... revision=...",
    )
    p_meta_write.add_argument(
        "--set",
        action="append",
        default=[],
        help="Set arbitrary metadata as KEY=VALUE (supports dotted keys, e.g. supplier.name=ACME)",
    )
    p_meta_write.add_argument("--overwrite", action="store_true")
    p_meta_write.add_argument("--dry-run", action="store_true")
    p_meta_write.set_defaults(func=cmd_shipment_metadata_write)

    p_ws = sub.add_parser(
        "workspace", help="Operate on multiple shipments/projects in a directory"
    )
    ws_sub = p_ws.add_subparsers(dest="workspace_cmd", required=True)

    p_wl = ws_sub.add_parser(
        "list",
        help="List discovered shipments (discover by scanning for SHA256SUMS)",
    )
    p_wl.add_argument(
        "--root", default=".", help="Root directory containing received shipments"
    )
    p_wl.add_argument(
        "--recursive", action="store_true", help="Recursively scan for SHA256SUMS"
    )
    p_wl.add_argument(
        "--format",
        choices=["table", "paths", "json"],
        default="table",
        help="Output format (default: table)",
    )
    p_wl.add_argument(
        "--json-report",
        default=None,
        help="Write JSON output to this path (only used with --format json)",
    )
    p_wl.set_defaults(func=cmd_workspace_list)

    p_wr = ws_sub.add_parser(
        "report",
        help="Generate a Subproject overview without copying shipments",
    )
    p_wr.add_argument(
        "--root", default=".", help="Root directory containing received shipments"
    )
    p_wr.add_argument(
        "--config",
        default=None,
        help="Workspace configuration JSON (default: <root>/osqar_workspace.json)",
    )
    p_wr.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_wr.add_argument(
        "--recursive", action="store_true", help="Recursively scan for SHA256SUMS"
    )
    p_wr.add_argument(
        "--output",
        required=True,
        help="Output directory for subproject_overview.json and the HTML overview under <output>/_build/html",
    )
    p_wr.add_argument(
        "--checksums",
        action="store_true",
        help="Also verify checksums for each shipment",
    )
    p_wr.add_argument(
        "--traceability",
        action="store_true",
        help="Also validate needs.json traceability for each shipment (non-writing)",
    )
    p_wr.add_argument(
        "--doctor",
        action="store_true",
        help="Also run doctor (shipment-mode) for each discovered shipment and write per-shipment JSON reports",
    )
    p_wr.add_argument("--needs-json", default=None, help="Override needs.json path")
    p_wr.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum verify",
    )
    p_wr.add_argument("--enforce-req-has-test", action="store_true")
    p_wr.add_argument("--enforce-arch-traces-req", action="store_true")
    p_wr.add_argument("--enforce-test-traces-req", action="store_true")
    p_wr.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing after a failure",
    )
    p_wr.add_argument("--json-report", default=None, help="Write a JSON summary report")
    p_wr.add_argument(
        "--open",
        action="store_true",
        help="Open the rendered HTML overview in your default browser",
    )
    p_wr.set_defaults(func=cmd_workspace_report)

    p_wd = ws_sub.add_parser(
        "diff",
        help="Diff two workspace reports (e.g., subproject_overview.json)",
    )
    p_wd.add_argument("old", help="Old report JSON")
    p_wd.add_argument("new", help="New report JSON")
    p_wd.set_defaults(func=cmd_workspace_diff)

    p_wv = ws_sub.add_parser(
        "verify", help="Verify many shipments (discover by scanning for SHA256SUMS)"
    )
    p_wv.add_argument(
        "--root", default=".", help="Root directory containing received shipments"
    )
    p_wv.add_argument(
        "--config",
        default=None,
        help="Workspace configuration JSON (default: <root>/osqar_workspace.json)",
    )
    p_wv.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_wv.add_argument(
        "--verify-command",
        action="append",
        default=[],
        help="Extra integrator-side verification command to run after built-in checks for each shipment (repeatable)",
    )
    p_wv.add_argument(
        "--recursive", action="store_true", help="Recursively scan for SHA256SUMS"
    )
    p_wv.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum verify",
    )
    p_wv.add_argument(
        "--traceability",
        action="store_true",
        help="Also validate needs.json traceability",
    )
    p_wv.add_argument(
        "--doctor",
        action="store_true",
        help="Also run doctor (shipment-mode) for each discovered shipment",
    )
    p_wv.add_argument("--needs-json", default=None, help="Override needs.json path")
    p_wv.add_argument("--enforce-req-has-test", action="store_true")
    p_wv.add_argument("--enforce-arch-traces-req", action="store_true")
    p_wv.add_argument("--enforce-test-traces-req", action="store_true")
    p_wv.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue verifying after a failure",
    )
    p_wv.add_argument(
        "--json-report", default=None, help="Write a workspace JSON summary report"
    )
    p_wv.set_defaults(func=cmd_workspace_verify)

    p_wi = ws_sub.add_parser(
        "intake",
        help="Verify and archive multiple shipments into a single intake directory (copies remain byte-identical)",
    )
    p_wi.add_argument(
        "shipments",
        nargs="*",
        help="Explicit shipment directories (optional if using --root)",
    )
    p_wi.add_argument(
        "--root",
        default=None,
        help="Root directory to scan for shipments (by SHA256SUMS)",
    )
    p_wi.add_argument(
        "--config",
        default=None,
        help="Workspace configuration JSON (default: <root>/osqar_workspace.json; or ./osqar_workspace.json if no --root)",
    )
    p_wi.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${_HOOK_DISABLE_ENV}=1)",
    )
    p_wi.add_argument(
        "--recursive", action="store_true", help="Recursively scan for SHA256SUMS"
    )
    p_wi.add_argument("--output", required=True, help="Output intake archive directory")
    p_wi.add_argument(
        "--force", action="store_true", help="Overwrite output directory if it exists"
    )
    p_wi.add_argument("--dry-run", action="store_true")
    p_wi.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum verify",
    )
    p_wi.add_argument(
        "--traceability",
        action="store_true",
        help="Also generate integrator-side traceability reports",
    )
    p_wi.add_argument(
        "--doctor",
        action="store_true",
        help="Also run doctor (shipment-mode) for each intaked shipment and write per-shipment JSON reports",
    )
    p_wi.add_argument("--needs-json", default=None, help="Override needs.json path")
    p_wi.add_argument("--enforce-req-has-test", action="store_true")
    p_wi.add_argument("--enforce-arch-traces-req", action="store_true")
    p_wi.add_argument("--enforce-test-traces-req", action="store_true")
    p_wi.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue intaking after a failure",
    )
    p_wi.set_defaults(func=cmd_workspace_intake)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
