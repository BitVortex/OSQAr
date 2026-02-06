#!/usr/bin/env python3
"""`osqar workspace ...` commands.

Extracted from the former monolithic CLI to keep the entrypoint small.

Stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from tools import osqar_cli_util as u
from tools.generate_checksums import cli as checksums_cli
from tools.osqar_cmd_doctor import cmd_doctor
from tools.osqar_cmd_shipment import (
    cmd_shipment_checksums,
    cmd_shipment_traceability,
    cmd_shipment_verify,
)
from tools.traceability_check import cli as traceability_cli


def _iter_shipment_dirs(root: Path, *, recursive: bool) -> list[Path]:
    root = root.resolve()
    if not root.exists():
        return []

    results: set[Path] = set()

    # Workspace operations typically target built shipment directories, which by
    # default live under `<project>/_build/html`. Do not exclude `_build`/`build`/`target`
    # here, otherwise the default layout becomes undiscoverable.
    ignored_scan_names = u.IGNORED_DIR_NAMES - {"_build", "build", "target"}

    def consider(candidate: Path) -> None:
        if not candidate.is_dir():
            return
        if any(part in ignored_scan_names for part in candidate.parts):
            return
        manifest = candidate / u.DEFAULT_CHECKSUM_MANIFEST
        if manifest.is_file():
            results.add(candidate)

    if root.is_dir() and (root / u.DEFAULT_CHECKSUM_MANIFEST).is_file():
        return [root]

    if not recursive:
        if not root.is_dir():
            return []
        for child in sorted(root.iterdir()):
            consider(child)
        return sorted(results)

    if root.is_dir():
        for manifest in root.rglob(u.DEFAULT_CHECKSUM_MANIFEST.name):
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


def cmd_workspace_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    shipments = _iter_shipment_dirs(root, recursive=bool(args.recursive))
    if not shipments:
        print(f"No shipments found under: {root}")
        return 1

    items: list[dict[str, object]] = []
    for shipment_dir in shipments:
        shipment_dir = shipment_dir.resolve()
        md = u.read_project_metadata(shipment_dir)
        needs = u.read_needs_summary_from_shipment(shipment_dir)
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
        suffix: list[str] = []
        if name:
            suffix.append(f"name={name}")
        if version:
            suffix.append(f"version={version}")
        if n_total is not None:
            suffix.append(f"needs={n_total}")
        suffix.append("docs=yes" if it.get("has_docs") else "docs=no")
        print(f"- {it['shipment']}  ({', '.join(suffix)})")

    return 0


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

        # Workspace intake items use a different schema than workspace report items.
        # Prefer the stable intake name when metadata is not available.
        if item.get("name"):
            return str(item.get("name"))

        for k in ("shipment", "dest", "source"):
            v = item.get(k)
            if not v:
                continue
            try:
                return Path(str(v)).name
            except Exception:
                return str(v)

        return ""

    # `html_out_dir` is usually `<output>/_build/html`. This allows us to resolve
    # intake-style relative paths like `shipments/<name>/index.html`.
    workspace_output_dir = html_out_dir.parent.parent

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
        shipment = it.get("shipment") or it.get("dest") or it.get("source")
        shipment_dir = Path(str(shipment)).resolve() if shipment else None
        project_label = key_for_project(it)

        if not project_label:
            project_label = "(unnamed)"

        link = ""

        # Determine a docs entrypoint path.
        index: Optional[Path] = None
        docs_entry = it.get("docs_entrypoint")
        if docs_entry:
            candidate = (workspace_output_dir / str(docs_entry)).resolve()
            if candidate.is_file():
                index = candidate

        if index is None and shipment_dir is not None:
            candidate = shipment_dir / "index.html"
            if candidate.is_file():
                index = candidate

        if index is not None:
            rel = u.relpath(html_out_dir, index)
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


def cmd_workspace_report(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ws_config = u.read_workspace_config(root, explicit_path=getattr(args, "config", None))
    shipments = _iter_shipment_dirs(root, recursive=bool(args.recursive))
    if not shipments:
        print(f"No shipments found under: {root}")
        return 1

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    effective_excludes = u.config_defaults_exclude(ws_config) + list(
        getattr(args, "exclude", []) or []
    )

    env = {
        "OSQAR_WORKSPACE_ROOT": str(root),
        "OSQAR_WORKSPACE_OUTPUT": str(output_dir),
    }
    rc = u.run_hooks(
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
            manifest = shipment_dir / u.DEFAULT_CHECKSUM_MANIFEST
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
                else u.find_needs_json(shipment_dir)
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
                        enforce_req_has_test=bool(getattr(args, "enforce_req_has_test", False)),
                        enforce_arch_traces_req=bool(getattr(args, "enforce_arch_traces_req", False)),
                        enforce_test_traces_req=bool(getattr(args, "enforce_test_traces_req", False)),
                    )
                )
            )
            doctor_report = str(doctor_report_path)
            if doctor_rc != 0:
                any_failures = True

        index = shipment_dir / "index.html"
        docs_link = u.relpath(output_dir, index) if index.is_file() else None

        items.append(
            {
                "shipment": str(shipment_dir),
                "checksums_rc": checksums_rc,
                "checksums_report": checksums_report,
                "traceability_rc": trace_rc,
                "traceability_report": trace_report,
                "doctor_rc": doctor_rc,
                "doctor_report": doctor_report,
                "metadata": u.read_project_metadata(shipment_dir),
                "needs_summary": u.read_needs_summary_from_shipment(shipment_dir),
                "docs_entrypoint": docs_link,
            }
        )

        if any_failures and not args.continue_on_error:
            # Stop after the first failure if requested.
            if (checksums_rc not in (None, 0)) or (trace_rc not in (None, 0)):
                break

    overview = {
        "title": "Subproject overview",
        "generated_at": u.utc_now_iso(),
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
    rc = u.run_sphinx_build(sphinx_src, html_out)
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
        open_rc = u.open_in_browser(entry)
        if open_rc != 0:
            return int(open_rc)
    else:
        # CI/non-interactive usage: emit the path for easy consumption.
        print(entry)

    rc = u.run_hooks(
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
        needs = p.get("needs_summary") if isinstance(p.get("needs_summary"), dict) else {}
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


def cmd_workspace_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ws_config = u.read_workspace_config(root, explicit_path=getattr(args, "config", None))
    shipments = _iter_shipment_dirs(root, recursive=bool(args.recursive))
    if not shipments:
        print(f"No shipments found under: {root}")
        return 1

    effective_excludes = u.config_defaults_exclude(ws_config) + list(
        getattr(args, "exclude", []) or []
    )

    env = {
        "OSQAR_WORKSPACE_ROOT": str(root),
    }
    rc = u.run_hooks(
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
        rc = u.run_hooks(
            ws_config,
            args=args,
            phase="pre",
            event="workspace.verify.shipment",
            cwd=Path(shipment_dir),
            env=ship_env,
        )
        if rc != 0:
            failures.append({"shipment": str(shipment_dir), "rc": int(rc), "hook": "pre"})
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
                strict=False,
                config=getattr(args, "config", None),
                config_root=str(root),
                verify_command=list(getattr(args, "verify_command", []) or []),
                no_hooks=bool(getattr(args, "no_hooks", False)),
                enforce_req_has_test=bool(args.enforce_req_has_test),
                enforce_arch_traces_req=bool(args.enforce_arch_traces_req),
                enforce_test_traces_req=bool(args.enforce_test_traces_req),
                skip_code_trace=False,
                code_trace_warn_only=False,
                enforce_no_unknown_ids=False,
                report_json=None,
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
                        skip_traceability=not bool(getattr(args, "traceability", False)),
                        skip_shipment_checks=False,
                        skip_env_checks=True,
                        enforce_req_has_test=bool(getattr(args, "enforce_req_has_test", False)),
                        enforce_arch_traces_req=bool(getattr(args, "enforce_arch_traces_req", False)),
                        enforce_test_traces_req=bool(getattr(args, "enforce_test_traces_req", False)),
                    )
                )
            )
            doctor_report = str(out) if out is not None else None

        entry = {
            "shipment": str(shipment_dir),
            "rc": int(rc),
            "metadata": u.read_project_metadata(shipment_dir),
            "doctor_rc": int(doctor_rc) if doctor_rc is not None else None,
            "doctor_report": doctor_report,
        }
        if rc == 0:
            successes.append(entry)
            u.run_hooks(
                ws_config,
                args=args,
                phase="post",
                event="workspace.verify.shipment",
                cwd=Path(shipment_dir),
                env=ship_env,
            )
            continue

        failures.append(entry)
        u.run_hooks(
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
        print(f"\nWorkspace verify FAILED: {len(failures)} / {len(successes) + len(failures)}")
        u.run_hooks(
            ws_config,
            args=args,
            phase="post",
            event="workspace.verify",
            cwd=Path.cwd(),
            env=env,
        )
        return 1

    print(f"\nWorkspace verify OK: {len(successes)}")
    rc = u.run_hooks(
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
    ws_config = u.read_workspace_config(ws_root, explicit_path=getattr(args, "config", None))

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

    effective_excludes = u.config_defaults_exclude(ws_config) + list(
        getattr(args, "exclude", []) or []
    )

    env = {
        "OSQAR_WORKSPACE_ROOT": str(ws_root),
        "OSQAR_WORKSPACE_OUTPUT": str(output_dir),
    }
    rc = u.run_hooks(
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
            u.safe_rmtree(output_dir, dry_run=bool(args.dry_run))
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

        manifest = shipment_dir / u.DEFAULT_CHECKSUM_MANIFEST
        verify_rc = cmd_shipment_checksums(
            argparse.Namespace(
                shipment=str(shipment_dir),
                manifest=str(manifest),
                mode="verify",
                exclude=effective_excludes,
                json_report=None,
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
                    "metadata": u.read_project_metadata(dest),
                    "needs_summary": u.read_needs_summary_from_shipment(dest),
                    "docs_entrypoint": (
                        f"shipments/{name}/index.html" if (dest / "index.html").is_file() else None
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
                            skip_traceability=not bool(getattr(args, "traceability", False)),
                            skip_shipment_checks=False,
                            skip_env_checks=True,
                            enforce_req_has_test=bool(getattr(args, "enforce_req_has_test", False)),
                            enforce_arch_traces_req=bool(getattr(args, "enforce_arch_traces_req", False)),
                            enforce_test_traces_req=bool(getattr(args, "enforce_test_traces_req", False)),
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
                "metadata": u.read_project_metadata(shipment_dir),
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
        "generated_at": u.utc_now_iso(),
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
    rc = u.run_sphinx_build(sphinx_src, html_out)
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
    archive_manifest = output_dir / u.DEFAULT_CHECKSUM_MANIFEST
    rc = checksums_cli(["--root", str(output_dir), "--output", str(archive_manifest)])
    if rc != 0:
        return int(rc)
    print(f"Wrote archive manifest: {archive_manifest}")

    rc = u.run_hooks(
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


def register(sub: argparse._SubParsersAction) -> None:
    p_ws = sub.add_parser(
        "workspace",
        help="Work with an integrator workspace (multiple received shipments)",
    )
    ws_sub = p_ws.add_subparsers(dest="workspace_cmd", required=True)

    p_wl = ws_sub.add_parser(
        "list",
        help="List shipments (discover by scanning for SHA256SUMS)",
    )
    p_wl.add_argument(
        "--root", default=".", help="Root directory containing received shipments"
    )
    p_wl.add_argument(
        "--config",
        default=None,
        help="Workspace configuration JSON (default: <root>/osqar_workspace.json)",
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
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
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
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
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
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
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
