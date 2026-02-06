#!/usr/bin/env python3
"""`osqar new` project scaffolding subcommand."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TEMPLATES_BASIC: dict[str, Path] = {
    "c": Path("templates/basic/c"),
    "cpp": Path("templates/basic/cpp"),
    "python": Path("templates/basic/python"),
    "rust": Path("templates/basic/rust"),
}

TEMPLATE_BASIC_SHARED = Path("templates/basic/shared")

TEMPLATES_EXAMPLE: dict[str, Path] = {
    "c": Path("examples/c_hello_world"),
    "cpp": Path("examples/cpp_hello_world"),
    "python": Path("examples/python_hello_world"),
    "rust": Path("examples/rust_hello_world"),
}

TEMPLATES: dict[str, Path] = dict(TEMPLATES_BASIC)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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

    def _ignore(_directory: str, names: list[str]) -> set[str]:
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

    def _ignore(_directory: str, names: list[str]) -> set[str]:
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
            print(
                f"ERROR: Template directory not found: {lang_src}",
                file=sys.stderr,
            )
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

    project_title = f"OSQAr: {args.name} ({args.language})"
    _rewrite_conf_project(dest / "conf.py", project_title)
    _rewrite_readme_title(dest / "README.md", args.name)

    print(f"Created OSQAr project at: {dest}")
    print(f"Template: {src} ({template_kind})")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
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
