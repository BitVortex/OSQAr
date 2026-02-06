#!/usr/bin/env python3
"""Shared utilities for the OSQAr CLI.

This module is intentionally stdlib-only.

It hosts:
- constants (default paths, ignored directories)
- small helpers (JSON/config loading, hook execution)
- Sphinx build helpers
- basic shipment/workspace utilities used across multiple commands
"""

from __future__ import annotations

import argparse
import json
import os
import os.path
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional


DEFAULT_BUILD_DIR = Path("_build/html")
DEFAULT_CHECKSUM_MANIFEST = Path("SHA256SUMS")
DEFAULT_TRACEABILITY_REPORT = Path("traceability_report.json")
DEFAULT_DOCTOR_REPORT = Path("doctor_report.json")
DEFAULT_PROJECT_METADATA = Path("osqar_project.json")
DEFAULT_WORKSPACE_CONFIG = Path("osqar_workspace.json")

HOOK_DISABLE_ENV = "OSQAR_DISABLE_HOOKS"

IGNORED_DIR_NAMES = {
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

DEFAULT_TEST_REPORT_GLOBS = (
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def relpath(from_dir: Path, to_path: Path) -> str:
    try:
        return os.path.relpath(os.fspath(to_path), start=os.fspath(from_dir))
    except Exception:
        return os.fspath(to_path)


def run(cmd: list[str], *, cwd: Path, env: Optional[Dict[str, str]] = None) -> int:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        proc = subprocess.run(cmd, cwd=str(cwd), env=merged_env)
    except FileNotFoundError as exc:
        print(f"ERROR: command not found: {cmd[0]} ({exc})", file=sys.stderr)
        return 127
    return int(proc.returncode)


def run_capture(cmd: list[str], *, cwd: Path) -> tuple[int, str]:
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


def write_json_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_json_dict(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to parse JSON: {path} ({exc})", file=sys.stderr)
        return None
    return data if isinstance(data, dict) else None


def read_project_config(project_dir: Path, *, explicit_path: Optional[str] = None) -> dict:
    if explicit_path:
        cfg_path = Path(explicit_path).expanduser().resolve()
    else:
        cfg_path = (project_dir / DEFAULT_PROJECT_METADATA).resolve()
    return read_json_dict(cfg_path) or {}


def read_workspace_config(root_dir: Path, *, explicit_path: Optional[str] = None) -> dict:
    if explicit_path:
        cfg_path = Path(explicit_path).expanduser().resolve()
    else:
        cfg_path = (root_dir / DEFAULT_WORKSPACE_CONFIG).resolve()
    return read_json_dict(cfg_path) or {}


def config_defaults_exclude(config: dict) -> list[str]:
    defaults = config.get("defaults") if isinstance(config, dict) else None
    if not isinstance(defaults, dict):
        return []
    ex = defaults.get("exclude")
    if isinstance(ex, list):
        return [str(x) for x in ex if isinstance(x, (str, int, float))]
    if isinstance(ex, str):
        return [ex]
    return []


def hook_commands(config: dict, *, phase: str, event: str) -> list[str]:
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


def hooks_enabled(args: argparse.Namespace) -> bool:
    if os.environ.get(HOOK_DISABLE_ENV):
        return False
    return not bool(getattr(args, "no_hooks", False))


def run_command_string(command: str, *, cwd: Path, env: dict[str, str]) -> int:
    try:
        argv = shlex.split(str(command))
    except ValueError as exc:
        print(f"ERROR: invalid command string: {exc}", file=sys.stderr)
        return 2
    if not argv:
        print("ERROR: empty command", file=sys.stderr)
        return 2
    print(f"Running: {command}")
    return run(argv, cwd=cwd, env=env)


def run_hooks(
    config: dict,
    *,
    args: argparse.Namespace,
    phase: str,
    event: str,
    cwd: Path,
    env: dict[str, str],
) -> int:
    if not hooks_enabled(args):
        return 0
    cmds = hook_commands(config, phase=phase, event=event)
    if not cmds:
        return 0
    print(f"Running {phase} hook(s) for {event}: {len(cmds)}")
    for cmd in cmds:
        rc = run_command_string(cmd, cwd=cwd, env=env)
        if rc != 0:
            print(f"ERROR: hook failed (rc={rc}): {event}", file=sys.stderr)
            return int(rc)
    return 0


def poetry_available() -> bool:
    return shutil.which("poetry") is not None


def project_uses_poetry(project_dir: Path) -> bool:
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        content = pyproject.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "[tool.poetry]" in content


def run_sphinx_build(project_dir: Path, output_dir: Path) -> int:
    project_dir = project_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    if project_uses_poetry(project_dir) and poetry_available():
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
        return run(cmd, cwd=project_dir)

    cmd = [sys.executable, "-m", "sphinx", "-b", "html", ".", str(output_dir)]
    return run(cmd, cwd=project_dir)


def run_docs_build(project_dir: Path, output_dir: Path, *, config: dict) -> int:
    commands = config.get("commands") if isinstance(config, dict) else None
    cmd = commands.get("docs") if isinstance(commands, dict) else None
    if isinstance(cmd, str) and cmd.strip():
        env = {
            "OSQAR_PROJECT_DIR": str(project_dir.resolve()),
            "OSQAR_DOCS_OUTPUT": str(output_dir.resolve()),
        }
        return run_command_string(str(cmd), cwd=project_dir, env=env)
    return run_sphinx_build(project_dir, output_dir)


def git_source_date_epoch(project_dir: Path) -> Optional[str]:
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


def reproducible_env(project_dir: Path, *, reproducible: bool) -> dict[str, str]:
    if not reproducible:
        return {}
    env: dict[str, str] = {
        "OSQAR_REPRODUCIBLE": "1",
    }
    if not os.environ.get("SOURCE_DATE_EPOCH"):
        epoch = git_source_date_epoch(project_dir)
        if epoch:
            env["SOURCE_DATE_EPOCH"] = epoch
    return env


def is_shipment_project_dir(path: Path) -> bool:
    return (path / "conf.py").is_file() and (path / "index.rst").is_file()


def default_shipment_dir(project_dir: Path) -> Path:
    return (project_dir / DEFAULT_BUILD_DIR).resolve()


def find_needs_json(shipment_dir: Path) -> Optional[Path]:
    candidate = shipment_dir / "needs.json"
    if candidate.is_file():
        return candidate
    for p in shipment_dir.rglob("needs.json"):
        if p.is_file():
            return p
    return None


def detect_language(project_dir: Path) -> str:
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


def detect_shipment_language(shipment_dir: Path) -> str:
    impl = (shipment_dir / "implementation").resolve()
    if impl.is_dir():
        return detect_language(impl)
    return detect_language(shipment_dir)


def iter_project_dirs(root: Path, *, recursive: bool) -> Iterable[Path]:
    root = root.resolve()
    if not root.is_dir():
        return

    if not recursive:
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name in IGNORED_DIR_NAMES:
                continue
            yield child
        return

    for conf in sorted(root.rglob("conf.py")):
        project_dir = conf.parent
        if any(part in IGNORED_DIR_NAMES for part in project_dir.parts):
            continue
        yield project_dir


def code_trace_test_dirs_for_shipment(shipment_dir: Path, *, language: str) -> list[str]:
    shipment_dir = shipment_dir.resolve()
    dirs: list[Path] = []

    tests_dir = shipment_dir / "tests"
    dirs.append(tests_dir)

    if language == "rust":
        dirs.append(shipment_dir / "implementation" / "src")

    return [str(d) for d in dirs]


def safe_rmtree(path: Path, *, dry_run: bool) -> None:
    path = path.resolve()
    if not path.exists():
        return
    if path == Path("/") or len(path.parts) < 3:
        raise ValueError(f"Refusing to remove unsafe path: {path}")

    if dry_run:
        print(f"DRY-RUN: would remove {path}")
        return
    shutil.rmtree(path)


def iter_test_report_files(project_dir: Path, globs: tuple[str, ...]) -> list[Path]:
    project_dir = project_dir.resolve()
    matches: set[Path] = set()

    for pattern in globs:
        for p in project_dir.glob(pattern):
            if not p.is_file():
                continue
            if any(part in IGNORED_DIR_NAMES for part in p.parts):
                continue
            matches.add(p.resolve())

    return sorted(matches)


def copy_test_reports(
    project_dir: Path, shipment_dir: Path, *, dry_run: bool, globs: tuple[str, ...]
) -> int:
    reports = iter_test_report_files(project_dir, globs)
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
        rel = src.relative_to(project_dir).as_posix().replace("..", "__")
        dest = dest_root / rel
        if dry_run:
            print(f"DRY-RUN: would copy {src} -> {dest}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    print(f"Copied {len(reports)} test reports into: {dest_root}")
    return 0


def copy_bundle_sources_and_reports(project_dir: Path, shipment_dir: Path, *, dry_run: bool) -> None:
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

    copy_tree(project_dir / "src", impl_dir / "src")
    copy_tree(project_dir / "include", impl_dir / "include")
    copy_tree(project_dir / "tests", tests_dir)

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

    copy_file(project_dir / "osqar_project.json", shipment_dir / "osqar_project.json")

    for fname in (
        "test_results.xml",
        "coverage_report.txt",
        "coverage.xml",
        "complexity_report.txt",
    ):
        copy_file(project_dir / fname, reports_dir / fname)

    for fname in (
        "test_results.xml",
        "coverage_report.txt",
        "coverage.xml",
        "complexity_report.txt",
    ):
        copy_file(project_dir / fname, shipment_dir / fname)


def set_nested_value(obj: dict, dotted_key: str, value: str) -> None:
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


def parse_kv(pairs: list[str]) -> dict[str, str]:
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


def read_project_metadata(shipment_dir: Path) -> Optional[dict]:
    path = (shipment_dir / DEFAULT_PROJECT_METADATA).resolve()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(
            f"WARNING: failed to read project metadata: {path} ({exc})", file=sys.stderr
        )
        return None


def read_needs_summary_from_shipment(shipment_dir: Path) -> Optional[dict[str, int]]:
    needs_json = find_needs_json(shipment_dir)
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
            if current_version in versions and isinstance(versions[current_version], dict):
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


def write_project_metadata(shipment_dir: Path, metadata: dict, *, overwrite: bool, dry_run: bool) -> int:
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


def logical_cwd() -> Path:
    return Path(os.environ.get("PWD") or os.getcwd())


def abspath_no_resolve(path: Path) -> Path:
    base = logical_cwd()
    p = path
    if not p.is_absolute():
        p = base / p
    return Path(os.path.normpath(os.fspath(p)))


def print_open_hint(path: Path) -> None:
    path = path.resolve()
    if sys.platform == "darwin":
        print(f"TIP: open {path}")
    elif sys.platform.startswith("linux"):
        print(f"TIP: xdg-open {path}")
    elif os.name == "nt":
        print(f"TIP: start {path}")
    else:
        print(f"TIP: open the file in your editor: {path}")


def open_in_browser(path: Path) -> int:
    path = path.resolve()
    if not path.exists():
        print(f"ERROR: path not found: {path}", file=sys.stderr)
        return 2

    if sys.platform == "darwin":
        rc = run(["open", str(path)], cwd=Path.cwd())
        if rc != 0:
            print_open_hint(path)
        return rc

    if sys.platform.startswith("linux"):
        rc = run(["xdg-open", str(path)], cwd=Path.cwd())
        if rc != 0:
            print_open_hint(path)
        return rc

    if os.name == "nt":
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: failed to open path: {path} ({exc})", file=sys.stderr)
            print_open_hint(path)
            return 2

    print_open_hint(path)
    return 0


def temp_json_report_path(*, suffix: str = ".json") -> Path:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=suffix, delete=False) as tf:
        return Path(tf.name)
