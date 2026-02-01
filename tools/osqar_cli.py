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
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Dict

from tools.generate_checksums import cli as checksums_cli
from tools.traceability_check import cli as traceability_cli


TEMPLATES: dict[str, Path] = {
    "c": Path("examples/c_hello_world"),
    "cpp": Path("examples/cpp_hello_world"),
    "python": Path("examples/python_hello_world"),
    "rust": Path("examples/rust_hello_world"),
}


DEFAULT_BUILD_DIR = Path("_build/html")
DEFAULT_CHECKSUM_MANIFEST = Path("SHA256SUMS")
DEFAULT_TRACEABILITY_REPORT = Path("traceability_report.json")
DEFAULT_PROJECT_METADATA = Path("osqar_project.json")

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
    if (project_dir / "pyproject.toml").is_file() or (project_dir / "requirements.txt").is_file():
        return "python"
    for probe in (project_dir / "src", project_dir / "tests"):
        if probe.is_dir() and any(p.suffix == ".py" for p in probe.rglob("*") if p.is_file()):
            return "python"
    if (project_dir / "CMakeLists.txt").is_file():
        # Try to disambiguate C vs C++ based on sources.
        src_root = project_dir / "src"
        if src_root.is_dir():
            has_cpp = any(p.suffix in {".cpp", ".cc", ".cxx"} for p in src_root.rglob("*") if p.is_file())
            if has_cpp:
                return "cpp"
        return "c"
    return "unknown"


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


def _run_sphinx_build(project_dir: Path, output_dir: Path) -> int:
    project_dir = project_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)

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


def _copy_test_reports(project_dir: Path, shipment_dir: Path, *, dry_run: bool, globs: tuple[str, ...]) -> int:
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
        print(f"WARNING: failed to read project metadata: {path} ({exc})", file=sys.stderr)
        return None


def _read_needs_summary_from_shipment(shipment_dir: Path) -> Optional[dict[str, int]]:
    needs_json = _find_needs_json(shipment_dir)
    if needs_json is None:
        return None

    try:
        data = json.loads(needs_json.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to parse needs.json: {needs_json} ({exc})", file=sys.stderr)
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
    }


def _write_project_metadata(shipment_dir: Path, metadata: dict, *, overwrite: bool, dry_run: bool) -> int:
    shipment_dir = shipment_dir.resolve()
    shipment_dir.mkdir(parents=True, exist_ok=True)
    path = shipment_dir / DEFAULT_PROJECT_METADATA
    if path.exists() and not overwrite:
        print(f"ERROR: metadata already exists (use --overwrite): {path}", file=sys.stderr)
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
    template = TEMPLATES.get(args.language)
    if template is None:
        print(f"ERROR: Unsupported language: {args.language}", file=sys.stderr)
        return 2

    repo_root = Path.cwd()
    src = (repo_root / template).resolve()
    if not src.is_dir():
        print(f"ERROR: Template directory not found: {src}", file=sys.stderr)
        return 2

    dest = Path(args.destination).resolve() if args.destination else (repo_root / args.name).resolve()

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
    print(f"Template: {src}")
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


def cmd_checksums_generate(args: argparse.Namespace) -> int:
    argv = ["--root", str(args.root), "--output", str(args.output)]
    for ex in args.exclude:
        argv += ["--exclude", ex]
    return checksums_cli(argv)


def cmd_checksums_verify(args: argparse.Namespace) -> int:
    argv = ["--root", str(args.root), "--verify", str(args.manifest)]
    for ex in args.exclude:
        argv += ["--exclude", ex]
    return checksums_cli(argv)


def cmd_shipment_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    projects: list[ShipmentProject] = []

    for candidate in _iter_project_dirs(root, recursive=args.recursive):
        if not _is_shipment_project_dir(candidate):
            continue
        projects.append(ShipmentProject(path=candidate, language=_detect_language(candidate)))

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
        print(f"ERROR: not a shipment project directory (missing conf.py/index.rst): {project_dir}", file=sys.stderr)
        return 2

    output_dir = Path(args.output).resolve() if args.output else _default_shipment_dir(project_dir)
    print(f"Building Sphinx HTML: {project_dir} -> {output_dir}")
    return _run_sphinx_build(project_dir, output_dir)


def cmd_shipment_run_tests(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    script = project_dir / (args.script or "build-and-test.sh")

    if not script.is_file():
        print(f"ERROR: test/build script not found: {script}", file=sys.stderr)
        return 2

    print(f"Running script: {script}")
    return _run(["bash", str(script.name)], cwd=project_dir)


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
    needs_json = Path(args.needs_json).resolve() if args.needs_json else _find_needs_json(shipment_dir)
    if needs_json is None or not needs_json.is_file():
        print(f"ERROR: needs.json not found in shipment: {shipment_dir}", file=sys.stderr)
        return 2

    json_report = Path(args.json_report).resolve() if args.json_report else (shipment_dir / DEFAULT_TRACEABILITY_REPORT)

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
    manifest = Path(args.manifest).resolve() if args.manifest else (shipment_dir / DEFAULT_CHECKSUM_MANIFEST)

    if args.mode == "generate":
        argv = ["--root", str(shipment_dir), "--output", str(manifest)]
        for ex in args.exclude:
            argv += ["--exclude", ex]
        return checksums_cli(argv)

    argv = ["--root", str(shipment_dir), "--verify", str(manifest)]
    for ex in args.exclude:
        argv += ["--exclude", ex]
    return checksums_cli(argv)


def cmd_shipment_copy_test_reports(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    shipment_dir = Path(args.shipment).resolve() if args.shipment else _default_shipment_dir(project_dir)
    globs = tuple(args.glob) if args.glob else _DEFAULT_TEST_REPORT_GLOBS
    return _copy_test_reports(project_dir, shipment_dir, dry_run=bool(args.dry_run), globs=globs)


def cmd_shipment_package(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    if not shipment_dir.is_dir():
        print(f"ERROR: shipment directory not found: {shipment_dir}", file=sys.stderr)
        return 2

    out = Path(args.output).resolve() if args.output else shipment_dir.with_suffix(".tar.gz")
    root_name = shipment_dir.name

    if args.dry_run:
        print(f"DRY-RUN: would create archive {out} from {shipment_dir}")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, "w:gz") as tf:
        tf.add(str(shipment_dir), arcname=root_name)

    print(f"Wrote archive: {out}")
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


def cmd_supplier_prepare(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    if not _is_shipment_project_dir(project_dir):
        print(f"ERROR: not a shipment project directory (missing conf.py/index.rst): {project_dir}", file=sys.stderr)
        return 2

    shipment_dir = Path(args.shipment).resolve() if args.shipment else _default_shipment_dir(project_dir)

    if args.clean:
        rc = cmd_shipment_clean(argparse.Namespace(project=str(project_dir), dry_run=args.dry_run, aggressive=False))
        if rc != 0:
            return rc

    if not args.skip_tests:
        # Best-effort: if no script exists, continue (some shipments are docs-only).
        script = project_dir / (args.script or "build-and-test.sh")
        if script.is_file():
            rc = cmd_shipment_run_tests(argparse.Namespace(project=str(project_dir), script=str(script.name)))
            if rc != 0:
                return rc
        else:
            print(f"NOTE: no test/build script found at {script}; skipping tests.")

    rc = _run_sphinx_build(project_dir, shipment_dir)
    if rc != 0:
        return rc

    # Copy raw test reports into the shipped directory (optional but recommended).
    _copy_test_reports(project_dir, shipment_dir, dry_run=bool(args.dry_run), globs=_DEFAULT_TEST_REPORT_GLOBS)

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
        return rc

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
        return rc

    rc = cmd_shipment_checksums(
        argparse.Namespace(
            shipment=str(shipment_dir),
            manifest=str(shipment_dir / DEFAULT_CHECKSUM_MANIFEST),
            mode="verify",
            exclude=args.exclude,
        )
    )
    if rc != 0:
        return rc

    if args.archive:
        rc = cmd_shipment_package(
            argparse.Namespace(shipment=str(shipment_dir), output=args.archive_output, dry_run=args.dry_run)
        )
        if rc != 0:
            return rc

    print(f"Supplier shipment ready: {shipment_dir}")
    return 0


def cmd_integrator_verify(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    if not shipment_dir.is_dir():
        print(f"ERROR: shipment directory not found: {shipment_dir}", file=sys.stderr)
        return 2

    manifest = Path(args.manifest).resolve() if args.manifest else (shipment_dir / DEFAULT_CHECKSUM_MANIFEST)
    if not manifest.is_file():
        print(f"ERROR: checksum manifest not found: {manifest}", file=sys.stderr)
        return 2

    rc = cmd_shipment_checksums(
        argparse.Namespace(shipment=str(shipment_dir), manifest=str(manifest), mode="verify", exclude=args.exclude)
    )
    if rc != 0:
        return rc

    if args.traceability:
        report = Path(args.json_report).resolve() if args.json_report else (shipment_dir / "traceability_report.integrator.json")
        rc = cmd_shipment_traceability(
            argparse.Namespace(
                shipment=str(shipment_dir),
                needs_json=args.needs_json,
                json_report=str(report),
                enforce_req_has_test=args.enforce_req_has_test,
                enforce_arch_traces_req=args.enforce_arch_traces_req,
                enforce_test_traces_req=args.enforce_test_traces_req,
            )
        )
        if rc != 0:
            return rc

    print("Integrator verification passed.")
    return 0


def _iter_shipment_dirs(root: Path, *, recursive: bool) -> list[Path]:
    root = root.resolve()
    if not root.exists():
        return []

    results: set[Path] = set()

    def consider(candidate: Path) -> None:
        if not candidate.is_dir():
            return
        if any(part in _IGNORED_DIR_NAMES for part in candidate.parts):
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
    shipments = _iter_shipment_dirs(root, recursive=bool(args.recursive))
    if not shipments:
        print(f"No shipments found under: {root}")
        return 1

    failures: list[dict[str, object]] = []
    successes: list[dict[str, object]] = []

    for shipment_dir in shipments:
        print(f"\n== Verifying shipment: {shipment_dir}")
        rc = cmd_integrator_verify(
            argparse.Namespace(
                shipment=str(shipment_dir),
                manifest=None,
                exclude=args.exclude,
                traceability=bool(args.traceability),
                needs_json=args.needs_json,
                json_report=None,
                enforce_req_has_test=bool(args.enforce_req_has_test),
                enforce_arch_traces_req=bool(args.enforce_arch_traces_req),
                enforce_test_traces_req=bool(args.enforce_test_traces_req),
            )
        )

        entry = {
            "shipment": str(shipment_dir),
            "rc": int(rc),
            "metadata": _read_project_metadata(shipment_dir),
        }
        if rc == 0:
            successes.append(entry)
            continue

        failures.append(entry)
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
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nWrote workspace report: {report_path}")

    if failures:
        print(f"\nWorkspace verify FAILED: {len(failures)} / {len(successes) + len(failures)}")
        return 1

    print(f"\nWorkspace verify OK: {len(successes)}")
    return 0


def cmd_workspace_intake(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else None
    output_dir = Path(args.output).resolve()

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

    if output_dir.exists():
        if not args.force:
            print(f"ERROR: output already exists (use --force to overwrite): {output_dir}", file=sys.stderr)
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
    overview_md_path = output_dir / "subproject_overview.md"

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
                exclude=args.exclude,
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
                    "metadata": _read_project_metadata(dest),
                    "needs_summary": _read_needs_summary_from_shipment(dest),
                    "docs_entrypoint": (
                        f"shipments/{name}/index.html" if (dest / "index.html").is_file() else None
                    ),
                }
            )
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
    intake_report_path.write_text(json.dumps(intake_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWrote intake report: {intake_report_path}")

    overview = {
        "title": "Subproject overview",
        "generated_at": _utc_now_iso(),
        "output": str(output_dir),
        "projects": items,
    }
    overview_json_path.write_text(json.dumps(overview, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _md_escape(s: str) -> str:
        return s.replace("|", "\\|").replace("\n", " ")

    lines: list[str] = []
    lines.append("# Subproject overview\n")
    lines.append(f"Generated at: {overview['generated_at']}\n\n")
    lines.append("| Project | Version | Origin | URLs | Needs | REQ | ARCH | TEST | Checksums | Traceability |\n")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|\n")
    for it in items:
        md = it.get("metadata") or {}
        display_name = _md_escape(str(md.get("name") or it.get("name") or ""))
        docs_link = it.get("docs_entrypoint")
        if isinstance(docs_link, str) and docs_link:
            project_cell = f"[{display_name}]({docs_link})"
        else:
            project_cell = display_name

        version = _md_escape(str(md.get("version") or ""))
        origin_val = ""
        origin = md.get("origin")
        if isinstance(origin, dict):
            origin_val = _md_escape(str(origin.get("url") or origin.get("repo") or origin.get("source") or ""))
        urls_val = ""
        urls = md.get("urls")
        if isinstance(urls, dict) and urls:
            parts = []
            for k, v in sorted(urls.items()):
                parts.append(f"{_md_escape(str(k))}: {_md_escape(str(v))}")
            urls_val = "<br>".join(parts)

        checksums_rc = it.get("checksums_rc")
        trace_rc = it.get("traceability_rc")
        needs = it.get("needs_summary") or {}
        n_total = needs.get("needs_total", "") if isinstance(needs, dict) else ""
        n_req = needs.get("req_total", "") if isinstance(needs, dict) else ""
        n_arch = needs.get("arch_total", "") if isinstance(needs, dict) else ""
        n_test = needs.get("test_total", "") if isinstance(needs, dict) else ""
        lines.append(
            f"| {project_cell} | {version} | {origin_val} | {urls_val} | {n_total} | {n_req} | {n_arch} | {n_test} | {checksums_rc} | {trace_rc if trace_rc is not None else ''} |\n"
        )

    overview_md_path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote Subproject overview: {overview_md_path}")
    _print_open_hint(overview_md_path)

    # Create an archive-level checksum manifest covering everything in the intake output.
    archive_manifest = output_dir / DEFAULT_CHECKSUM_MANIFEST
    rc = checksums_cli(["--root", str(output_dir), "--output", str(archive_manifest)])
    if rc != 0:
        return int(rc)
    print(f"Wrote archive manifest: {archive_manifest}")

    return 0 if not any_failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="osqar", description="OSQAr helper CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="Create a new OSQAr project from a language template")
    p_new.add_argument("--language", choices=sorted(TEMPLATES.keys()), required=True)
    p_new.add_argument("--name", required=True, help="Project name (used for folder name by default)")
    p_new.add_argument("--destination", default=None, help="Destination directory (default: ./<name>)")
    p_new.add_argument("--force", action="store_true", help="Overwrite destination if it exists")
    p_new.set_defaults(func=cmd_new)

    p_tr = sub.add_parser("traceability", help="Run traceability checks on an exported needs.json")
    p_tr.add_argument("needs_json", type=Path, help="Path to needs.json")
    p_tr.add_argument("--json-report", type=Path, default=None, help="Write JSON report to this path")
    p_tr.add_argument("--enforce-req-has-test", action="store_true", help="Also enforce REQ_* → TEST_* coverage")
    p_tr.add_argument("--enforce-arch-traces-req", action="store_true", help="Also enforce ARCH_* → REQ_* coverage")
    p_tr.add_argument("--enforce-test-traces-req", action="store_true", help="Also enforce TEST_* → REQ_* coverage")
    p_tr.set_defaults(func=cmd_traceability)

    p_sum = sub.add_parser("checksum", help="Generate or verify shipment checksum manifests")
    sum_sub = p_sum.add_subparsers(dest="checksum_cmd", required=True)

    p_gen = sum_sub.add_parser("generate", help="Generate SHA256SUMS for a directory")
    p_gen.add_argument("--root", type=Path, required=True)
    p_gen.add_argument("--output", type=Path, required=True)
    p_gen.add_argument("--exclude", action="append", default=[], help="Exclude glob (repeatable)")
    p_gen.set_defaults(func=cmd_checksums_generate)

    p_ver = sum_sub.add_parser("verify", help="Verify a directory against SHA256SUMS")
    p_ver.add_argument("--root", type=Path, required=True)
    p_ver.add_argument("--manifest", type=Path, required=True)
    p_ver.add_argument("--exclude", action="append", default=[], help="Exclude glob (repeatable)")
    p_ver.set_defaults(func=cmd_checksums_verify)

    p_ship = sub.add_parser("shipment", help="Work with shippable evidence bundles (build, clean, verify)")
    ship_sub = p_ship.add_subparsers(dest="shipment_cmd", required=True)

    p_list = ship_sub.add_parser("list", help="Discover shipment projects under a directory")
    p_list.add_argument("--root", default=".", help="Root directory to scan (default: .)")
    p_list.add_argument("--recursive", action="store_true", help="Recursively scan for conf.py")
    p_list.add_argument("--format", choices=["pretty", "paths"], default="pretty")
    p_list.set_defaults(func=cmd_shipment_list)

    p_build = ship_sub.add_parser("build-docs", help="Build Sphinx HTML output for a shipment project")
    p_build.add_argument("--project", required=True, help="Shipment project directory (contains conf.py/index.rst)")
    p_build.add_argument("--output", default=None, help="Output directory (default: <project>/_build/html)")
    p_build.set_defaults(func=cmd_shipment_build_docs)

    p_tests = ship_sub.add_parser("run-tests", help="Run a shipment's build-and-test script")
    p_tests.add_argument("--project", required=True, help="Shipment project directory")
    p_tests.add_argument("--script", default=None, help="Script name (default: build-and-test.sh)")
    p_tests.set_defaults(func=cmd_shipment_run_tests)

    p_clean = ship_sub.add_parser("clean", help="Remove generated outputs (conservative by default)")
    p_clean.add_argument("--project", required=True, help="Shipment project directory")
    p_clean.add_argument("--dry-run", action="store_true", help="Print what would be removed")
    p_clean.add_argument("--aggressive", action="store_true", help="Also remove 'diagrams/' if present")
    p_clean.set_defaults(func=cmd_shipment_clean)

    p_tr2 = ship_sub.add_parser("traceability", help="Run traceability checks for a built shipment directory")
    p_tr2.add_argument("--shipment", required=True, help="Shipment directory (usually <project>/_build/html)")
    p_tr2.add_argument("--needs-json", default=None, help="Override needs.json path (default: <shipment>/needs.json)")
    p_tr2.add_argument("--json-report", default=None, help="Write JSON report (default: <shipment>/traceability_report.json)")
    p_tr2.add_argument("--enforce-req-has-test", action="store_true")
    p_tr2.add_argument("--enforce-arch-traces-req", action="store_true")
    p_tr2.add_argument("--enforce-test-traces-req", action="store_true")
    p_tr2.set_defaults(func=cmd_shipment_traceability)

    p_cs = ship_sub.add_parser("checksums", help="Generate or verify checksum manifests for a shipment directory")
    p_cs.add_argument("--shipment", required=True, help="Shipment directory")
    p_cs.add_argument("--manifest", default=None, help="Manifest path (default: <shipment>/SHA256SUMS)")
    p_cs.add_argument("--exclude", action="append", default=[], help="Exclude glob (repeatable)")
    p_cs.add_argument("mode", choices=["generate", "verify"], help="Operation")
    p_cs.set_defaults(func=cmd_shipment_checksums)

    p_rep = ship_sub.add_parser("copy-test-reports", help="Copy raw JUnit XML into the shipment directory")
    p_rep.add_argument("--project", required=True, help="Shipment project directory")
    p_rep.add_argument("--shipment", default=None, help="Shipment directory (default: <project>/_build/html)")
    p_rep.add_argument("--glob", action="append", default=[], help="Glob to match report files (repeatable)")
    p_rep.add_argument("--dry-run", action="store_true")
    p_rep.set_defaults(func=cmd_shipment_copy_test_reports)

    p_pkg = ship_sub.add_parser("package", help="Archive a shipment directory into a .tar.gz")
    p_pkg.add_argument("--shipment", required=True, help="Shipment directory")
    p_pkg.add_argument("--output", default=None, help="Archive output path (default: <shipment>.tar.gz)")
    p_pkg.add_argument("--dry-run", action="store_true")
    p_pkg.set_defaults(func=cmd_shipment_package)

    p_meta = ship_sub.add_parser("metadata", help="Add project metadata (descriptive info, URLs, origin) to a shipment")
    meta_sub = p_meta.add_subparsers(dest="metadata_cmd", required=True)
    p_meta_write = meta_sub.add_parser("write", help="Write osqar_project.json into a shipment directory")
    p_meta_write.add_argument("--shipment", required=True, help="Shipment directory")
    p_meta_write.add_argument("--name", default=None, help="Human-friendly project name")
    p_meta_write.add_argument("--id", dest="project_id", default=None, help="Stable project identifier")
    p_meta_write.add_argument("--version", default=None, help="Project/shipment version")
    p_meta_write.add_argument("--description", default=None, help="Short description")
    p_meta_write.add_argument("--url", action="append", default=[], help="URL as KEY=VALUE (repeatable)")
    p_meta_write.add_argument("--origin", action="append", default=[], help="Origin as KEY=VALUE (repeatable), e.g. url=... revision=...")
    p_meta_write.add_argument(
        "--set",
        action="append",
        default=[],
        help="Set arbitrary metadata as KEY=VALUE (supports dotted keys, e.g. supplier.name=ACME)",
    )
    p_meta_write.add_argument("--overwrite", action="store_true")
    p_meta_write.add_argument("--dry-run", action="store_true")
    p_meta_write.set_defaults(func=cmd_shipment_metadata_write)

    p_sup = sub.add_parser("supplier", help="Supplier-focused shipment workflows")
    sup_sub = p_sup.add_subparsers(dest="supplier_cmd", required=True)
    p_prepare = sup_sub.add_parser(
        "prepare",
        help="Build docs, run traceability + checksums, and optionally archive a shippable evidence bundle",
    )
    p_prepare.add_argument("--project", required=True, help="Shipment project directory")
    p_prepare.add_argument("--shipment", default=None, help="Shipment output directory (default: <project>/_build/html)")
    p_prepare.add_argument("--clean", action="store_true", help="Clean generated outputs before building")
    p_prepare.add_argument("--dry-run", action="store_true", help="Print destructive ops without executing")
    p_prepare.add_argument("--script", default=None, help="Test/build script name (default: build-and-test.sh)")
    p_prepare.add_argument("--skip-tests", action="store_true", help="Skip running the test/build script")
    p_prepare.add_argument("--exclude", action="append", default=[], help="Exclude glob(s) for checksum generation")
    p_prepare.add_argument("--enforce-req-has-test", action="store_true")
    p_prepare.add_argument("--enforce-arch-traces-req", action="store_true")
    p_prepare.add_argument("--enforce-test-traces-req", action="store_true")
    p_prepare.add_argument("--archive", action="store_true", help="Also create a .tar.gz of the shipment directory")
    p_prepare.add_argument("--archive-output", default=None, help="Archive output path (default: <shipment>.tar.gz)")
    p_prepare.set_defaults(func=cmd_supplier_prepare)

    p_int = sub.add_parser("integrator", help="Integrator-focused shipment intake workflows")
    int_sub = p_int.add_subparsers(dest="integrator_cmd", required=True)
    p_verify = int_sub.add_parser("verify", help="Verify checksum manifest and optionally re-run traceability checks")
    p_verify.add_argument("--shipment", required=True, help="Received shipment directory")
    p_verify.add_argument("--manifest", default=None, help="Checksum manifest (default: <shipment>/SHA256SUMS)")
    p_verify.add_argument("--exclude", action="append", default=[], help="Exclude glob(s) for checksum verify")
    p_verify.add_argument("--traceability", action="store_true", help="Also validate needs.json traceability")
    p_verify.add_argument("--needs-json", default=None, help="Override needs.json path")
    p_verify.add_argument("--json-report", default=None, help="Write integrator-side traceability report")
    p_verify.add_argument("--enforce-req-has-test", action="store_true")
    p_verify.add_argument("--enforce-arch-traces-req", action="store_true")
    p_verify.add_argument("--enforce-test-traces-req", action="store_true")
    p_verify.set_defaults(func=cmd_integrator_verify)

    p_ws = sub.add_parser("workspace", help="Operate on multiple shipments/projects in a directory")
    ws_sub = p_ws.add_subparsers(dest="workspace_cmd", required=True)

    p_wv = ws_sub.add_parser("verify", help="Verify many shipments (discover by scanning for SHA256SUMS)")
    p_wv.add_argument("--root", default=".", help="Root directory containing received shipments")
    p_wv.add_argument("--recursive", action="store_true", help="Recursively scan for SHA256SUMS")
    p_wv.add_argument("--exclude", action="append", default=[], help="Exclude glob(s) for checksum verify")
    p_wv.add_argument("--traceability", action="store_true", help="Also validate needs.json traceability")
    p_wv.add_argument("--needs-json", default=None, help="Override needs.json path")
    p_wv.add_argument("--enforce-req-has-test", action="store_true")
    p_wv.add_argument("--enforce-arch-traces-req", action="store_true")
    p_wv.add_argument("--enforce-test-traces-req", action="store_true")
    p_wv.add_argument("--continue-on-error", action="store_true", help="Continue verifying after a failure")
    p_wv.add_argument("--json-report", default=None, help="Write a workspace JSON summary report")
    p_wv.set_defaults(func=cmd_workspace_verify)

    p_wi = ws_sub.add_parser(
        "intake",
        help="Verify and archive multiple shipments into a single intake directory (copies remain byte-identical)",
    )
    p_wi.add_argument("shipments", nargs="*", help="Explicit shipment directories (optional if using --root)")
    p_wi.add_argument("--root", default=None, help="Root directory to scan for shipments (by SHA256SUMS)")
    p_wi.add_argument("--recursive", action="store_true", help="Recursively scan for SHA256SUMS")
    p_wi.add_argument("--output", required=True, help="Output intake archive directory")
    p_wi.add_argument("--force", action="store_true", help="Overwrite output directory if it exists")
    p_wi.add_argument("--dry-run", action="store_true")
    p_wi.add_argument("--exclude", action="append", default=[], help="Exclude glob(s) for checksum verify")
    p_wi.add_argument("--traceability", action="store_true", help="Also generate integrator-side traceability reports")
    p_wi.add_argument("--needs-json", default=None, help="Override needs.json path")
    p_wi.add_argument("--enforce-req-has-test", action="store_true")
    p_wi.add_argument("--enforce-arch-traces-req", action="store_true")
    p_wi.add_argument("--enforce-test-traces-req", action="store_true")
    p_wi.add_argument("--continue-on-error", action="store_true", help="Continue intaking after a failure")
    p_wi.set_defaults(func=cmd_workspace_intake)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
