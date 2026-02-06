#!/usr/bin/env python3
"""`osqar framework ...` commands (release/CI helpers)."""

from __future__ import annotations

import argparse
import shutil
import sys
from importlib import resources
from pathlib import Path


def cmd_framework_bundle(args: argparse.Namespace) -> int:
    version = str(args.version)
    docs_dir = Path(args.docs_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not docs_dir.is_dir():
        print(f"ERROR: docs dir not found: {docs_dir}", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[1]
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

    def _copy_resource_tree(src, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        for entry in src.iterdir():
            name = getattr(entry, "name", None) or str(entry).split("/")[-1]
            out = dst / str(name)
            if entry.is_dir():
                _copy_resource_tree(entry, out)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(entry.read_bytes())

    _copytree(docs_dir, bundle_root / "docs")
    _copytree(repo_root / "tools", bundle_root / "tools")

    templates_src = repo_root / "templates"
    if templates_src.is_dir():
        _copytree(templates_src, bundle_root / "templates")
    else:
        # PyPI installs do not have a repo-root `templates/` folder; use packaged resources.
        try:
            tmpl_res = resources.files("osqar_data").joinpath("templates")
            if not tmpl_res.is_dir():
                raise FileNotFoundError("Packaged templates not found")
            _copy_resource_tree(tmpl_res, bundle_root / "templates")
        except Exception as exc:
            print(f"ERROR: templates not found (repo or packaged): {exc}", file=sys.stderr)
            return 2

    if (repo_root / "osqar").is_file():
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


def register(sub: argparse._SubParsersAction) -> None:
    p_fw = sub.add_parser(
        "framework",
        help="Framework bundle operations (used for CI/release packaging)",
    )
    fw_sub = p_fw.add_subparsers(dest="framework_cmd", required=True)
    p_fwb = fw_sub.add_parser(
        "bundle",
        help="Assemble a framework bundle directory (docs + CLI + templates)",
    )
    p_fwb.add_argument("--version", required=True, help="Release/tag version, e.g. v0.4.2")
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
