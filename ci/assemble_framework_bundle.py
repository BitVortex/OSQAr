#!/usr/bin/env python3
"""Assemble a release bundle for the OSQAr framework.

This repository is primarily documentation + tooling. For GitHub Releases we
publish a single archive that contains:

- built framework documentation (HTML)
- CLI tooling (tools/ + repo-root wrappers)
- scaffolding templates (templates/)

The output of this script is a *staging directory* that a CI workflow can archive
in deterministic ways (tar --sort=name, --mtime, gzip -n, etc.).

The script is stdlib-only.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _ignore_common(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".DS_Store",
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def assemble_bundle(*, version: str, docs_dir: Path, output_dir: Path) -> Path:
    repo_root = _repo_root()
    docs_dir = docs_dir.resolve()
    output_dir = output_dir.resolve()

    bundle_root = output_dir / f"osqar-framework-{version}"

    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    # Built framework docs
    _copytree(docs_dir, bundle_root / "docs")

    # Tooling + templates
    _copytree(repo_root / "tools", bundle_root / "tools")
    _copytree(repo_root / "templates", bundle_root / "templates")

    # Convenience wrappers
    _copyfile(repo_root / "osqar", bundle_root / "osqar")
    if (repo_root / "osqar.cmd").is_file():
        _copyfile(repo_root / "osqar.cmd", bundle_root / "osqar.cmd")
    if (repo_root / "osqar.ps1").is_file():
        _copyfile(repo_root / "osqar.ps1", bundle_root / "osqar.ps1")

    # Metadata / licensing
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

    # Simple bundle README
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

    return bundle_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble OSQAr framework release bundle"
    )
    parser.add_argument(
        "--version", required=True, help="Release/tag version, e.g. v0.4.0"
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("_build/html"),
        help="Path to built framework HTML docs (default: _build/html)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("_dist"),
        help="Output/staging directory to create bundle under (default: _dist)",
    )

    args = parser.parse_args(argv)

    bundle = assemble_bundle(
        version=args.version, docs_dir=args.docs_dir, output_dir=args.output_dir
    )
    print(f"Assembled framework bundle at: {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
