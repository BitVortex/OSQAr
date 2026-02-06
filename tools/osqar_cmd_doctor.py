#!/usr/bin/env python3
"""`osqar doctor` subcommand.

Provides a best-effort environment + shipment consistency report.

Design goals:
- stdlib-only
- non-destructive by default
- CI-friendly exit codes
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
from tools.traceability_check import cli as traceability_cli


def _doctor_best_effort_shipment_dir(
    project_dir: Path, explicit: Optional[str]
) -> Optional[Path]:
    if explicit:
        return Path(explicit).expanduser().resolve()
    default = (project_dir / u.DEFAULT_BUILD_DIR).resolve()
    return default if default.is_dir() else None


def _doctor_run_checksums_verify(
    *,
    shipment_dir: Path,
    manifest: Path,
    exclude: list[str],
) -> tuple[int, Optional[dict]]:
    tmp_path = u.temp_json_report_path()
    try:
        argv = [
            "--root",
            str(shipment_dir),
            "--verify",
            str(manifest),
            "--json-report",
            str(tmp_path),
        ]
        for ex in exclude:
            argv += ["--exclude", ex]
        rc = int(checksums_cli(argv))
        try:
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        return rc, data if isinstance(data, dict) else None
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _doctor_run_traceability(
    *,
    needs_json: Path,
    enforce_req_has_test: bool,
    enforce_arch_traces_req: bool,
    enforce_test_traces_req: bool,
) -> tuple[int, Optional[dict]]:
    tmp_path = u.temp_json_report_path()
    try:
        argv = [str(needs_json), "--json-report", str(tmp_path)]
        if enforce_req_has_test:
            argv += ["--enforce-req-has-test"]
        if enforce_arch_traces_req:
            argv += ["--enforce-arch-traces-req"]
        if enforce_test_traces_req:
            argv += ["--enforce-test-traces-req"]

        rc = int(traceability_cli(argv))
        try:
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        return rc, data if isinstance(data, dict) else None
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def cmd_doctor(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).expanduser().resolve()
    skip_env_checks = bool(getattr(args, "skip_env_checks", False))
    warnings: list[str] = []
    errors: list[str] = []
    checks: list[dict[str, object]] = []

    def info(msg: str) -> None:
        print(f"INFO: {msg}")

    def good(msg: str) -> None:
        print(f"OK: {msg}")

    def warn(msg: str) -> None:
        print(f"WARN: {msg}")
        warnings.append(msg)

    def issue(msg: str) -> None:
        print(f"ISSUE: {msg}")
        warnings.append(msg)

    def bad(msg: str) -> None:
        print(f"ERROR: {msg}")
        errors.append(msg)

    info(f"python={sys.executable}")
    info(f"platform={sys.platform}")

    if not skip_env_checks:
        if not project_dir.is_dir():
            bad(f"project directory not found: {project_dir}")
            return 2

        if u.is_shipment_project_dir(project_dir):
            good(f"project looks like a shipment project: {project_dir}")
        else:
            warn(f"project is missing conf.py/index.rst: {project_dir}")

        uses_poetry = u.project_uses_poetry(project_dir)
        poetry = shutil.which("poetry")
        if uses_poetry:
            if poetry:
                good("poetry found")
            else:
                bad("poetry not found but project uses Poetry (pyproject.toml)")
        else:
            if poetry:
                good("poetry found (project does not require it)")
            else:
                info("poetry not found")

        # Sphinx availability (in the environment that build-docs will use).
        if uses_poetry and poetry:
            rc, out = u.run_capture(
                [
                    "poetry",
                    "run",
                    "python",
                    "-c",
                    "import sphinx; print(sphinx.__version__)",
                ],
                cwd=project_dir,
            )
            if rc == 0:
                good(f"sphinx import OK (poetry env): {out}")
            else:
                bad(f"sphinx not available in poetry env (rc={rc}): {out}")
        else:
            rc, out = u.run_capture(
                [sys.executable, "-c", "import sphinx; print(sphinx.__version__)"],
                cwd=project_dir,
            )
            if rc == 0:
                good(f"sphinx import OK (current env): {out}")
            else:
                warn(
                    "sphinx not importable in current env; build-docs may still work if you use Poetry"
                )

        # PlantUML diagnostics.
        plantuml_cmd = shutil.which("plantuml")
        plantuml_jar = os.environ.get("PLANTUML_JAR")
        if plantuml_cmd:
            good(f"plantuml command found: {plantuml_cmd}")
        elif plantuml_jar:
            jar_path = Path(plantuml_jar).expanduser()
            if jar_path.is_file():
                java = shutil.which("java")
                if java:
                    good(f"PLANTUML_JAR set and java found: {jar_path}")
                else:
                    warn(f"PLANTUML_JAR set but java not found: {jar_path}")
            else:
                warn(f"PLANTUML_JAR set but file not found: {jar_path}")
        else:
            warn(
                "no PlantUML command or PLANTUML_JAR detected; builds may fall back to the public PlantUML server (internet required)"
            )

    shipment_override = getattr(args, "shipment", None)
    if skip_env_checks and shipment_override:
        shipment_dir = Path(shipment_override).expanduser().resolve()
    else:
        shipment_dir = _doctor_best_effort_shipment_dir(project_dir, shipment_override)
    if shipment_dir is None:
        info(
            "no shipment directory detected (build via: osqar build-docs) or pass --shipment"
        )
    else:
        info(f"shipment={shipment_dir}")
        if not shipment_dir.is_dir():
            bad(f"shipment directory not found: {shipment_dir}")
            shipment_dir = None

    # Shipment artifact checks (best-effort, non-destructive)
    if shipment_dir is not None and not bool(getattr(args, "skip_shipment_checks", False)):
        index = shipment_dir / "index.html"
        if index.is_file():
            good("shipment has index.html")
            checks.append(
                {"name": "shipment.index_html", "status": "ok", "path": str(index)}
            )
        else:
            issue("shipment is missing index.html (docs may not have been built)")
            checks.append(
                {
                    "name": "shipment.index_html",
                    "status": "missing",
                    "path": str(index),
                }
            )

        md_path = shipment_dir / u.DEFAULT_PROJECT_METADATA
        md = u.read_project_metadata(shipment_dir)
        if md_path.is_file() and md:
            good("shipment has osqar_project.json")
            if not md.get("version"):
                warn("shipment metadata has no version")
            origin = md.get("origin")
            if not isinstance(origin, dict) or not origin:
                warn("shipment metadata has no origin")
            checks.append(
                {"name": "shipment.metadata", "status": "ok", "path": str(md_path)}
            )
        elif md_path.is_file() and not md:
            bad(f"failed to parse shipment metadata: {md_path}")
            checks.append(
                {
                    "name": "shipment.metadata",
                    "status": "error",
                    "path": str(md_path),
                }
            )
        else:
            warn("shipment has no osqar_project.json metadata")
            checks.append(
                {
                    "name": "shipment.metadata",
                    "status": "missing",
                    "path": str(md_path),
                }
            )

        needs_json = u.find_needs_json(shipment_dir)
        if needs_json and needs_json.is_file():
            good("shipment has needs.json")
            checks.append(
                {
                    "name": "shipment.needs_json",
                    "status": "ok",
                    "path": str(needs_json),
                }
            )
        else:
            warn("shipment has no needs.json (traceability cannot be evaluated)")
            checks.append(
                {
                    "name": "shipment.needs_json",
                    "status": "missing",
                    "path": str((shipment_dir / "needs.json")),
                }
            )

        tr_report = shipment_dir / u.DEFAULT_TRACEABILITY_REPORT
        if tr_report.is_file():
            good("shipment has traceability_report.json")
            checks.append(
                {
                    "name": "shipment.traceability_report",
                    "status": "ok",
                    "path": str(tr_report),
                }
            )
        else:
            warn(
                "shipment is missing traceability_report.json (supplier-side traceability evidence not present)"
            )
            checks.append(
                {
                    "name": "shipment.traceability_report",
                    "status": "missing",
                    "path": str(tr_report),
                }
            )

        has_any_junit = False
        try:
            for pat in u.DEFAULT_TEST_REPORT_GLOBS:
                if any(shipment_dir.glob(pat)):
                    has_any_junit = True
                    break
        except Exception:
            has_any_junit = False
        if has_any_junit:
            good("shipment has raw JUnit XML test report(s)")
            checks.append({"name": "shipment.test_reports", "status": "ok"})
        else:
            warn("shipment has no raw JUnit XML test reports (optional but recommended)")
            checks.append({"name": "shipment.test_reports", "status": "missing"})

        manifest = shipment_dir / u.DEFAULT_CHECKSUM_MANIFEST
        if manifest.is_file():
            good("shipment has SHA256SUMS")
            checks.append(
                {
                    "name": "shipment.checksum_manifest",
                    "status": "ok",
                    "path": str(manifest),
                }
            )
        else:
            issue("shipment is missing SHA256SUMS (integrity cannot be verified)")
            checks.append(
                {
                    "name": "shipment.checksum_manifest",
                    "status": "missing",
                    "path": str(manifest),
                }
            )

        if manifest.is_file() and not bool(getattr(args, "skip_checksums", False)):
            rc, data = _doctor_run_checksums_verify(
                shipment_dir=shipment_dir,
                manifest=manifest,
                exclude=list(getattr(args, "exclude", []) or []),
            )
            if rc == 0:
                good("checksums verify OK")
                checks.append({"name": "checksums.verify", "status": "ok", "rc": rc})
            else:
                bad(f"checksums verify FAILED (rc={rc})")
                checks.append({"name": "checksums.verify", "status": "fail", "rc": rc})
            if data is not None:
                checks[-1]["report"] = data

        # Run traceability if requested OR if needs.json exists.
        wants_trace = bool(getattr(args, "traceability", False))
        if (not bool(getattr(args, "skip_traceability", False))) and (
            wants_trace or (needs_json and needs_json.is_file())
        ):
            if needs_json is None or not needs_json.is_file():
                bad("traceability check requested but needs.json not found")
            else:
                try:
                    data = json.loads(needs_json.read_text(encoding="utf-8"))
                except Exception as exc:  # noqa: BLE001
                    bad(f"failed to parse needs.json: {needs_json} ({exc})")
                    data = None

                has_any_needs = False
                if isinstance(data, dict):
                    if isinstance(data.get("needs"), list) and data.get("needs"):
                        has_any_needs = True
                    elif isinstance(data.get("versions"), dict):
                        versions = data.get("versions")
                        current_version = data.get("current_version", "")
                        if (
                            current_version in versions
                            and isinstance(versions[current_version], dict)
                            and versions[current_version].get("needs")
                        ):
                            has_any_needs = True

                if not has_any_needs:
                    warn(
                        f"needs.json contains no needs; skipping traceability check: {needs_json}"
                    )
                    checks.append(
                        {
                            "name": "traceability",
                            "status": "skipped",
                            "reason": "no needs",
                            "path": str(needs_json),
                        }
                    )
                else:
                    trc, treport = _doctor_run_traceability(
                        needs_json=needs_json,
                        enforce_req_has_test=bool(
                            getattr(args, "enforce_req_has_test", False)
                        ),
                        enforce_arch_traces_req=bool(
                            getattr(args, "enforce_arch_traces_req", False)
                        ),
                        enforce_test_traces_req=bool(
                            getattr(args, "enforce_test_traces_req", False)
                        ),
                    )
                    if trc == 0:
                        good(f"traceability OK: {needs_json}")
                        checks.append(
                            {
                                "name": "traceability",
                                "status": "ok",
                                "rc": trc,
                                "path": str(needs_json),
                            }
                        )
                    else:
                        bad(f"traceability FAILED (rc={trc}): {needs_json}")
                        checks.append(
                            {
                                "name": "traceability",
                                "status": "fail",
                                "rc": trc,
                                "path": str(needs_json),
                            }
                        )
                    if treport is not None:
                        checks[-1]["report"] = treport

    report: dict[str, object] = {
        "schema": "osqar.doctor_report.v1",
        "generated_at": u.utc_now_iso(),
        "project": str(project_dir),
        "shipment": str(shipment_dir) if shipment_dir is not None else None,
        "python": sys.executable,
        "platform": sys.platform,
        "warnings": warnings,
        "errors": errors,
        "checks": checks,
    }

    if getattr(args, "json_report", None):
        out = Path(args.json_report).expanduser().resolve()
        u.write_json_report(out, report)
        print(f"Wrote doctor report: {out}")

    # CI-friendly: return 1 if any issues (warnings or errors).
    return 0 if (not warnings and not errors) else 1


def register(sub: argparse._SubParsersAction) -> None:
    p_doc = sub.add_parser(
        "doctor",
        help=(
            "Full status report for debugging (environment + optional shipment consistency checks)"
        ),
    )
    p_doc.add_argument(
        "--project",
        default=".",
        help="Project directory to check (default: .)",
    )
    p_doc.add_argument(
        "--shipment",
        default=None,
        help="Built shipment directory to check (default: <project>/_build/html if present)",
    )
    p_doc.add_argument(
        "--json-report",
        default=None,
        help="Write a machine-readable JSON report to this path",
    )
    p_doc.add_argument(
        "--traceability",
        action="store_true",
        help="Also run traceability checks if needs.json is available (non-writing)",
    )
    p_doc.add_argument(
        "--needs-json",
        default=None,
        help="Override needs.json path for --traceability",
    )
    p_doc.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum verify (repeatable)",
    )
    p_doc.add_argument(
        "--skip-checksums",
        action="store_true",
        help="Skip checksum verification even if SHA256SUMS is present",
    )
    p_doc.add_argument(
        "--skip-traceability",
        action="store_true",
        help="Skip traceability checks even if needs.json is present",
    )
    p_doc.add_argument(
        "--skip-shipment-checks",
        action="store_true",
        help="Skip shipment artifact checks (index.html, needs.json, SHA256SUMS, metadata)",
    )
    p_doc.add_argument(
        "--skip-env-checks",
        action="store_true",
        help="Skip environment checks (useful when diagnosing received shipments)",
    )
    p_doc.add_argument("--enforce-req-has-test", action="store_true")
    p_doc.add_argument("--enforce-arch-traces-req", action="store_true")
    p_doc.add_argument("--enforce-test-traces-req", action="store_true")
    p_doc.set_defaults(func=cmd_doctor)
