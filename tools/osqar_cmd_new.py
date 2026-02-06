#!/usr/bin/env python3
"""`osqar new` project scaffolding subcommand."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from importlib import resources
from pathlib import Path

TEMPLATES_BASIC: dict[str, str] = {
    "c": "c",
    "cpp": "cpp",
    "python": "python",
    "rust": "rust",
}

TEMPLATES_EXAMPLE: dict[str, Path] = {
    "c": Path("examples/c_hello_world"),
    "cpp": Path("examples/cpp_hello_world"),
    "python": Path("examples/python_hello_world"),
    "rust": Path("examples/rust_hello_world"),
}

TEMPLATES: dict[str, str] = dict(TEMPLATES_BASIC)


def _repo_root() -> Path:
    # Repo root when running from the git checkout. In a PyPI install, this will
    # typically resolve to the site-packages directory and is not guaranteed to
    # contain repo assets like `examples/`.
    return Path(__file__).resolve().parents[1]


def _resource_dir(*parts: str):
    # `osqar_data` is packaged with templates for the PyPI distribution.
    # `resources.files()` returns a Traversable which may not be a real path
    # (e.g. in a zipped wheel).
    return resources.files("osqar_data").joinpath(*parts)


def _copy_resource_tree(src, dst: Path, *, merge: bool, force: bool) -> None:
    if dst.exists() and not merge:
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

    def should_ignore(name: str) -> bool:
        if name in ignore_names:
            return True
        if name.endswith(".pyc"):
            return True
        if name == ".DS_Store":
            return True
        return False

    dst.mkdir(parents=True, exist_ok=True)

    for entry in src.iterdir():
        name = getattr(entry, "name", None) or str(entry).split("/")[-1]
        if should_ignore(str(name)):
            continue

        out = dst / str(name)
        if entry.is_dir():
            _copy_resource_tree(entry, out, merge=True, force=force)
            continue

        # Best-effort copy for files.
        out.parent.mkdir(parents=True, exist_ok=True)
        with entry.open("rb") as fsrc:
            data = fsrc.read()
        out.write_bytes(data)

        # Restore executability for common scripts on POSIX.
        if os.name == "posix":
            if str(name).endswith(".sh") or str(name) in {"osqar", "osqar.cmd", "osqar.ps1"}:
                try:
                    st = out.stat()
                    out.chmod(st.st_mode | 0o111)
                except OSError:
                    pass


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
    if template_kind == "basic":
        template = TEMPLATES_BASIC.get(args.language)
        if template is None:
            print(f"ERROR: Unsupported language: {args.language}", file=sys.stderr)
            return 2
    else:
        template = None
        if args.language not in TEMPLATES_EXAMPLE:
            print(f"ERROR: Unsupported language: {args.language}", file=sys.stderr)
            return 2

    dest = (
        Path(args.destination).resolve()
        if args.destination
        else (Path.cwd() / args.name).resolve()
    )

    if dest.exists():
        if not args.force:
            print(f"ERROR: Destination already exists: {dest}", file=sys.stderr)
            return 2
        shutil.rmtree(dest)

    if template_kind == "basic":
        try:
            shared_src = _resource_dir("templates", "basic", "shared")
            lang_src = _resource_dir("templates", "basic", template)
        except ModuleNotFoundError:
            print(
                "ERROR: packaged templates not available (missing osqar_data).\n"
                "TIP: If you are running from the git repo, ensure your environment can import this workspace.",
                file=sys.stderr,
            )
            return 2

        if not shared_src.is_dir():
            print(
                f"ERROR: Shared template directory not found in package: {shared_src}",
                file=sys.stderr,
            )
            return 2
        if not lang_src.is_dir():
            print(
                f"ERROR: Template directory not found in package: {lang_src}",
                file=sys.stderr,
            )
            return 2

        dest.mkdir(parents=True, exist_ok=True)
        _copy_resource_tree(shared_src, dest, merge=True, force=bool(args.force))
        _copy_resource_tree(lang_src, dest, merge=True, force=bool(args.force))
        src = f"osqar_data:{lang_src}"
    else:
        repo_root = _repo_root()
        src = (repo_root / TEMPLATES_EXAMPLE[args.language]).resolve()
        if not src.is_dir():
            print(
                "ERROR: example templates are not included in the PyPI distribution.\n"
                "TIP: Use --template basic, or run from the git repo to use --template example.",
                file=sys.stderr,
            )
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
