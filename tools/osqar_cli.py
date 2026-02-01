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
import shutil
import sys
from pathlib import Path

from tools.generate_checksums import cli as checksums_cli
from tools.traceability_check import cli as traceability_cli


TEMPLATES: dict[str, Path] = {
    "c": Path("examples/c_hello_world"),
    "cpp": Path("examples/cpp_hello_world"),
    "python": Path("examples/python_hello_world"),
    "rust": Path("examples/rust_hello_world"),
}


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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
