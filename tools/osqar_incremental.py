#!/usr/bin/env python3
"""Incremental stage cache for `osqar shipment prepare`.

Stores a JSON manifest of stage input hashes so that `--incremental` mode
can skip stages whose inputs haven't changed since the last successful run.

The cache lives at ``<project>/.osqar-cache/stages.json``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


CACHE_DIR = ".osqar-cache"
STAGES_FILE = "stages.json"


def _cache_path(project_dir: Path) -> Path:
    return project_dir / CACHE_DIR / STAGES_FILE


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _hash_files(globs: list[str], root: Path) -> str:
    """Hash a set of files matching glob patterns under root."""
    h = hashlib.sha256()
    for g in globs:
        for p in sorted(root.glob(g)):
            if p.is_file():
                h.update(p.read_bytes())
    return h.hexdigest()


def _hash_command(cmd: str) -> str:
    return _hash_bytes(cmd.encode())


def compute_stage_inputs(
    project_dir: Path,
    config: dict[str, Any],
    *,
    skip_build: bool = False,
    skip_tests: bool = False,
    skip_verification: bool = False,
) -> dict[str, str]:
    """Compute input hashes for each pipeline stage.

    Returns ``{stage_name: sha256_hex}``.
    """
    stages: dict[str, str] = {}

    # Build stage: source files + build command
    if not skip_build:
        commands = config.get("commands") if isinstance(config, dict) else None
        build_cmd = str(commands.get("build", "")) if isinstance(commands, dict) else ""
        h = hashlib.sha256()
        if build_cmd:
            h.update(build_cmd.encode())
        # Hash source files under common source directories
        for src_dir in ("src", "include", "lib", "cjson-source"):
            d = project_dir / src_dir
            if d.is_dir():
                for p in sorted(d.rglob("*")):
                    if p.is_file() and ".git" not in str(p):
                        h.update(p.read_bytes())
        stages["build"] = h.hexdigest() if build_cmd else "noop"

    # Test stage: test sources + test command
    if not skip_tests:
        commands = config.get("commands") if isinstance(config, dict) else None
        test_cmd = str(commands.get("test", "")) if isinstance(commands, dict) else ""
        h = hashlib.sha256()
        if test_cmd:
            h.update(test_cmd.encode())
        for test_dir in ("tests", "test"):
            d = project_dir / test_dir
            if d.is_dir():
                for p in sorted(d.rglob("*")):
                    if p.is_file() and ".git" not in str(p):
                        h.update(p.read_bytes())
        # Also hash the build-and-test.sh script
        script = project_dir / "build-and-test.sh"
        if script.is_file():
            h.update(script.read_bytes())
        stages["test"] = h.hexdigest() if test_cmd or script.is_file() else "noop"

    # Verification stage: verification.run commands
    if not skip_verification:
        verification = config.get("verification") if isinstance(config, dict) else None
        activities = verification.get("run") if isinstance(verification, dict) else []
        h = hashlib.sha256()
        if isinstance(activities, list):
            for act in activities:
                if isinstance(act, dict):
                    cmd = str(act.get("command", ""))
                    if cmd:
                        h.update(cmd.encode())
        stages["verification"] = h.hexdigest() if activities else "noop"

    # Docs stage: RST files, conf.py, _static/
    h = hashlib.sha256()
    for rst in sorted(project_dir.glob("*.rst")):
        h.update(rst.read_bytes())
    conf = project_dir / "conf.py"
    if conf.is_file():
        h.update(conf.read_bytes())
    static_dir = project_dir / "_static"
    if static_dir.is_dir():
        for p in sorted(static_dir.rglob("*")):
            if p.is_file():
                h.update(p.read_bytes())
    osqar_config = project_dir / "osqar_project.json"
    if osqar_config.is_file():
        h.update(osqar_config.read_bytes())
    stages["docs"] = h.hexdigest()

    # Code-trace stage: depends on docs output (needs.json) + source
    # Mark as dependent on docs — we skip if docs was skipped
    stages["code_trace"] = stages.get("docs", "noop")  # same hash = same needs.json

    # Traceability stage: depends on docs output (needs.json)
    stages["traceability"] = stages.get("docs", "noop")

    # Checksums stage: always runs (fast, and depends on full shipment contents)
    stages["checksums"] = "always"

    return stages


def load_cache(project_dir: Path) -> dict[str, str]:
    """Load the cached stage hashes. Returns {} on any error."""
    cp = _cache_path(project_dir)
    if not cp.is_file():
        return {}
    try:
        data = json.loads(cp.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_cache(project_dir: Path, stages: dict[str, str]) -> None:
    """Save stage hashes to cache."""
    cp = _cache_path(project_dir)
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(stages, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clear_cache(project_dir: Path) -> None:
    """Remove the cache file."""
    cp = _cache_path(project_dir)
    if cp.is_file():
        cp.unlink()
