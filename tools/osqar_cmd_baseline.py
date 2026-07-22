#!/usr/bin/env python3
"""`osqar baseline` — versioned requirement baselines for change management."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


BASELINE_DIR_NAME = ".osqar-baselines"
MANIFEST_FILE = "baseline-manifest.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _baseline_dir(project_dir: Path) -> Path:
    return project_dir / BASELINE_DIR_NAME


def _valid_tag(tag: str) -> bool:
    """Baseline tags: alphanumeric + hyphens + dots + underscores."""
    if not tag or not tag.strip():
        return False
    return all(c.isalnum() or c in "-._" for c in tag)


from tools.traceability_check import _load_needs


def _count_needs(needs_path: Path) -> int:
    """Count needs in a JSON or YAML file."""
    try:
        needs = _load_needs(needs_path)
        return len(needs)
    except Exception:
        return 0


def cmd_baseline_snapshot(args: argparse.Namespace) -> int:
    tag: str = args.tag.strip()
    if not _valid_tag(tag):
        print(f"ERROR: invalid baseline tag: {tag!r}", file=sys.stderr)
        return 2

    project_dir: Path = Path(getattr(args, "project", ".")).expanduser().resolve()
    needs_json: Path = (
        Path(args.needs_json).expanduser().resolve()
        if getattr(args, "needs_json", None)
        else (project_dir / "_build" / "html" / "needs.json")
    )

    if not needs_json.is_file():
        print(f"ERROR: needs file not found: {needs_json}", file=sys.stderr)
        print(
            "Hint: build docs first (osqar shipment build-docs) or pass --needs-json",
            file=sys.stderr,
        )
        return 2

    baseline_root = _baseline_dir(project_dir)
    tag_dir = baseline_root / tag

    if tag_dir.exists():
        if not getattr(args, "force", False):
            print(
                f"ERROR: baseline {tag!r} already exists. Use --force to overwrite.",
                file=sys.stderr,
            )
            return 2
        shutil.rmtree(tag_dir)

    tag_dir.mkdir(parents=True, exist_ok=True)

    # Copy needs file (preserve extension for YAML support)
    needs_filename = needs_json.name  # e.g. "needs.json" or "needs.yaml"
    shutil.copy2(needs_json, tag_dir / needs_filename)

    # Write manifest
    needs_count = _count_needs(needs_json)
    parent = getattr(args, "parent", None)
    manifest: dict[str, Any] = {
        "schema": "osqar.baseline_manifest.v1",
        "tag": tag,
        "created_at": _utc_now_iso(),
        "message": str(getattr(args, "message", "") or "").strip(),
        "needs_file": needs_filename,
        "needs_count": needs_count,
    }
    if parent:
        manifest["parent"] = str(parent).strip()

    (tag_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"Baseline snapshot created: {tag!r} ({needs_count} needs)")
    print(f"  path: {tag_dir}")
    return 0


def _load_baseline(dirpath: Path) -> Optional[dict[str, Any]]:
    """Load a baseline's manifest + needs. Returns None if invalid."""
    manifest_path = dirpath / MANIFEST_FILE
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(manifest, dict):
        return None
    if manifest.get("schema") != "osqar.baseline_manifest.v1":
        return None
    if manifest.get("tag") != dirpath.name:
        return None

    # Support both old (needs_json) and new (needs_file) manifest keys.
    needs_filename = manifest.get("needs_file") or manifest.get("needs_json", "needs.json")
    if not isinstance(needs_filename, str) or not needs_filename:
        return None
    needs_relative = Path(needs_filename)
    if needs_relative.is_absolute() or len(needs_relative.parts) != 1:
        return None
    needs_path = dirpath / needs_relative
    if not needs_path.is_file():
        return None

    try:
        needs_data = _load_needs(needs_path)
    except Exception:
        return None
    expected_count = manifest.get("needs_count")
    if (
        not isinstance(expected_count, int)
        or isinstance(expected_count, bool)
        or expected_count != len(needs_data)
    ):
        return None
    need_ids = [
        str(need.get("id", "")).strip()
        for need in needs_data
        if isinstance(need, dict)
    ]
    if len(need_ids) != len(needs_data) or any(not need_id for need_id in need_ids):
        return None
    if len(set(need_ids)) != len(need_ids):
        return None
    return {"manifest": manifest, "needs_data": needs_data}


def _extract_needs(data: Any) -> dict[str, dict[str, Any]]:
    """Normalize needs data (list from _load_needs or raw dict) into {id: need_dict}."""
    needs: dict[str, dict[str, Any]] = {}

    if isinstance(data, list):
        # Already normalized by _load_needs
        for n in data:
            if isinstance(n, dict) and n.get("id"):
                needs[str(n["id"])] = n
        return needs

    raw: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if isinstance(data.get("needs"), list):
            raw = [n for n in data["needs"] if isinstance(n, dict)]
        elif isinstance(data.get("versions"), dict):
            versions = data["versions"]
            current = data.get("current_version", "")
            if current in versions and isinstance(versions[current], dict):
                v = versions[current]
                if isinstance(v.get("needs"), dict):
                    raw = [{"id": str(k), **n} for k, n in v["needs"].items() if isinstance(n, dict)]
                elif isinstance(v.get("needs"), list):
                    raw = [n for n in v["needs"] if isinstance(n, dict)]
        elif isinstance(data.get("needs"), dict):
            raw = [{"id": str(k), **n} for k, n in data["needs"].items() if isinstance(n, dict)]

    for n in raw:
        nid = str(n.get("id", ""))
        if nid:
            needs[nid] = n
    return needs


def _diff_needs(
    old: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute structured diff between two need sets."""
    old_ids = set(old)
    new_ids = set(new)

    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    common = sorted(old_ids & new_ids)
    unchanged: list[str] = []
    modified: list[dict[str, Any]] = []

    for nid in common:
        old_need = old[nid]
        new_need = new[nid]
        changes: dict[str, Any] = {}
        for field in ("status", "title", "content"):
            ov = str(old_need.get(field, "")).strip()
            nv = str(new_need.get(field, "")).strip()
            if ov != nv:
                changes[field] = {"old": ov, "new": nv}

        old_links = set(
            str(l) for l in (old_need.get("links") or [])
            if l and isinstance(l, str)
        )
        new_links = set(
            str(l) for l in (new_need.get("links") or [])
            if l and isinstance(l, str)
        )
        if old_links != new_links:
            added_links = sorted(new_links - old_links)
            removed_links = sorted(old_links - new_links)
            link_changes: dict[str, list[str]] = {}
            if added_links:
                link_changes["added"] = added_links
            if removed_links:
                link_changes["removed"] = removed_links
            changes["links"] = link_changes

        old_tags = set(str(t) for t in (old_need.get("tags") or []) if t)
        new_tags = set(str(t) for t in (new_need.get("tags") or []) if t)
        if old_tags != new_tags:
            changes["tags"] = {
                "added": sorted(new_tags - old_tags),
                "removed": sorted(old_tags - new_tags),
            }

        if changes:
            modified.append({"id": nid, "changes": changes})
        else:
            unchanged.append(nid)

    return {
        "added": [{"id": nid, "title": str(new[nid].get("title", new[nid].get("content", ""))).strip()} for nid in added],
        "removed": [{"id": nid, "title": str(old[nid].get("title", old[nid].get("content", ""))).strip()} for nid in removed],
        "modified": modified,
        "unchanged": len(unchanged),
        "counts": {
            "old_total": len(old),
            "new_total": len(new),
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "unchanged": len(unchanged),
        },
    }


def cmd_baseline_list(args: argparse.Namespace) -> int:
    project_dir: Path = Path(getattr(args, "project", ".")).expanduser().resolve()
    baseline_root = _baseline_dir(project_dir)

    if not baseline_root.is_dir():
        print("No baselines found.")
        return 0

    tags = sorted(
        (d for d in baseline_root.iterdir() if d.is_dir()),
        key=lambda d: d.name,
    )
    if not tags:
        print("No baselines found.")
        return 0

    for tag_dir in tags:
        bl = _load_baseline(tag_dir)
        if bl is None:
            print(f"  {tag_dir.name:20s}  (invalid — missing manifest or needs.json)")
            continue
        m = bl["manifest"]
        msg = m.get("message", "")
        count = m.get("needs_count", "?")
        created = m.get("created_at", "?")[:10]
        parent = f"  parent={m['parent']}" if m.get("parent") else ""
        print(f"  {tag_dir.name:20s}  {created}  {count:>4} needs  {msg}{parent}")

    return 0


def cmd_baseline_diff(args: argparse.Namespace) -> int:
    project_dir: Path = Path(getattr(args, "project", ".")).expanduser().resolve()
    baseline_root = _baseline_dir(project_dir)
    tag_old: str = args.tag_old.strip()
    tag_new: str = args.tag_new.strip()

    bl_old = _load_baseline(baseline_root / tag_old)
    bl_new = _load_baseline(baseline_root / tag_new)

    if bl_old is None:
        print(f"ERROR: baseline {tag_old!r} not found or invalid", file=sys.stderr)
        return 2
    if bl_new is None:
        print(f"ERROR: baseline {tag_new!r} not found or invalid", file=sys.stderr)
        return 2

    old_needs = _extract_needs(bl_old["needs_data"])
    new_needs = _extract_needs(bl_new["needs_data"])
    diff = _diff_needs(old_needs, new_needs)

    verbose = bool(getattr(args, "verbose", False))
    output_format = getattr(args, "format", "text") or "text"

    if output_format == "json":
        report: dict[str, Any] = {
            "schema": "osqar.baseline_diff.v1",
            "old_tag": tag_old,
            "new_tag": tag_new,
            "old_manifest": bl_old["manifest"],
            "new_manifest": bl_new["manifest"],
            **diff,
        }
        json_report = getattr(args, "json_report", None)
        if json_report:
            out = Path(json_report).expanduser().resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Baseline diff written: {out}")
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    # Text format
    c = diff["counts"]
    print(f"\nBaseline diff: {tag_old} → {tag_new}")
    print(f"  {c['old_total']} → {c['new_total']} needs "
          f"(+{c['added']} added, {c['modified']} modified, {c['removed']} removed, {c['unchanged']} unchanged)")

    for item in diff["added"]:
        print(f"\n  [ADDED]    {item['id']}")
        if item["title"]:
            print(f"             {item['title']}")

    for item in diff["removed"]:
        print(f"\n  [REMOVED]  {item['id']}")
        if item["title"]:
            print(f"             {item['title']}")

    for item in diff["modified"]:
        print(f"\n  [MODIFIED] {item['id']}")
        for field, change in item["changes"].items():
            if field == "links":
                if isinstance(change, dict):
                    if "added" in change:
                        print(f"             links: +{', '.join(change['added'])}")
                    if "removed" in change:
                        print(f"             links: -{', '.join(change['removed'])}")
            elif field == "tags":
                if isinstance(change, dict):
                    if "added" in change:
                        print(f"             tags: +{', '.join(change['added'])}")
                    if "removed" in change:
                        print(f"             tags: -{', '.join(change['removed'])}")
            elif verbose and isinstance(change, dict):
                print(f"             {field}: {change.get('old', '')!r} → {change.get('new', '')!r}")

    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p_bl = sub.add_parser(
        "baseline",
        help="Versioned requirement baselines (snapshot / diff / list)",
    )
    bl_sub = p_bl.add_subparsers(dest="baseline_cmd", required=True)

    # baseline snapshot
    p_snap = bl_sub.add_parser("snapshot", help="Snapshot current needs.json as a baseline")
    p_snap.add_argument("--tag", required=True, help="Baseline tag (e.g., v1.0, release-2026Q2)")
    p_snap.add_argument("--message", default="", help="Human-readable description of this baseline")
    p_snap.add_argument("--parent", default=None, help="Parent baseline tag (for lineage)")
    p_snap.add_argument("--needs-json", type=Path, default=None, help="Path to needs.json or needs.yaml")
    p_snap.add_argument("--project", default=".", help="Project directory (default: .)")
    p_snap.add_argument("--force", action="store_true", help="Overwrite existing baseline")
    p_snap.set_defaults(func=cmd_baseline_snapshot)

    # baseline list
    p_list = bl_sub.add_parser("list", help="List stored baselines")
    p_list.add_argument("--project", default=".", help="Project directory (default: .)")
    p_list.set_defaults(func=cmd_baseline_list)

    # baseline diff
    p_diff = bl_sub.add_parser("diff", help="Diff two baselines")
    p_diff.add_argument("tag_old", help="Old baseline tag")
    p_diff.add_argument("tag_new", help="New baseline tag")
    p_diff.add_argument("--project", default=".", help="Project directory (default: .)")
    p_diff.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")
    p_diff.add_argument("--verbose", "-v", action="store_true", help="Show full field-level changes")
    p_diff.add_argument("--json-report", type=Path, default=None, help="Write JSON report to this path")
    p_diff.set_defaults(func=cmd_baseline_diff)
