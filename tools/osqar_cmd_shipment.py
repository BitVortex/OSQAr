#!/usr/bin/env python3
"""`osqar shipment ...` commands.

This module is stdlib-only and keeps the CLI entrypoint small.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import stat
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools import osqar_cli_util as u
from tools.code_trace_check import cli as code_trace_cli
from tools.generate_checksums import cli as checksums_cli
from tools.traceability_check import cli as traceability_cli


def cmd_shipment_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    projects: list[u.ShipmentProject] = []

    for candidate in u.iter_project_dirs(root, recursive=bool(args.recursive)):
        if not u.is_shipment_project_dir(candidate):
            continue
        projects.append(u.ShipmentProject(path=candidate, language=u.detect_language(candidate)))

    if getattr(args, "format", "pretty") == "paths":
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
    if not u.is_shipment_project_dir(project_dir):
        print(
            f"ERROR: not a shipment project directory (missing conf.py/index.rst): {project_dir}",
            file=sys.stderr,
        )
        return 2

    config = u.read_project_config(project_dir, explicit_path=getattr(args, "config", None))

    output_dir = (
        Path(args.output).resolve() if getattr(args, "output", None) else u.default_shipment_dir(project_dir)
    )

    env = {
        "OSQAR_PROJECT_DIR": str(project_dir),
        "OSQAR_DOCS_OUTPUT": str(output_dir),
    }
    rc = u.run_hooks(
        config,
        args=args,
        phase="pre",
        event="shipment.build-docs",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    print(f"Building docs: {project_dir} -> {output_dir}")
    rc = u.run_docs_build(project_dir, output_dir, config=config)
    if rc != 0:
        return int(rc)

    rc = u.run_hooks(
        config,
        args=args,
        phase="post",
        event="shipment.build-docs",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    if bool(getattr(args, "open", False)):
        entry = output_dir / "index.html"
        if entry.is_file():
            return int(u.open_in_browser(entry))
        print(f"WARNING: docs entrypoint not found: {entry}", file=sys.stderr)
        u.print_open_hint(entry)

    return 0


def cmd_shipment_run_tests(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    config = u.read_project_config(project_dir, explicit_path=getattr(args, "config", None))

    env = {"OSQAR_PROJECT_DIR": str(project_dir)}
    env.update(
        u.reproducible_env(project_dir, reproducible=bool(getattr(args, "reproducible", False)))
    )

    rc = u.run_hooks(
        config,
        args=args,
        phase="pre",
        event="shipment.run-tests",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    command_str = getattr(args, "command", None)
    if not command_str:
        commands = config.get("commands") if isinstance(config, dict) else None
        if isinstance(commands, dict) and isinstance(commands.get("test"), str):
            command_str = commands.get("test")

    if command_str:
        rc = u.run_command_string(str(command_str), cwd=project_dir, env=env)
    else:
        script = project_dir / (getattr(args, "script", None) or "build-and-test.sh")
        if not script.is_file():
            print(
                "ERROR: no test command configured and script not found. Provide --command, set commands.test in osqar_project.json, or provide --script.",
                file=sys.stderr,
            )
            return 2
        print(f"Running script: {script}")
        rc = u.run(["bash", str(script.name)], cwd=project_dir, env=env)

    if rc != 0:
        return int(rc)

    rc = u.run_hooks(
        config,
        args=args,
        phase="post",
        event="shipment.run-tests",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)
    return 0


def cmd_shipment_run_build(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project directory not found: {project_dir}", file=sys.stderr)
        return 2

    config = u.read_project_config(project_dir, explicit_path=getattr(args, "config", None))
    env = {"OSQAR_PROJECT_DIR": str(project_dir)}
    env.update(
        u.reproducible_env(project_dir, reproducible=bool(getattr(args, "reproducible", False)))
    )

    rc = u.run_hooks(
        config,
        args=args,
        phase="pre",
        event="shipment.run-build",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    command_str = getattr(args, "command", None)
    if not command_str:
        commands = config.get("commands") if isinstance(config, dict) else None
        if isinstance(commands, dict) and isinstance(commands.get("build"), str):
            command_str = commands.get("build")

    if not command_str:
        print(
            "ERROR: no build command configured. Pass --command or set commands.build in osqar_project.json in the project root.",
            file=sys.stderr,
        )
        return 2

    try:
        cmd = shlex.split(str(command_str))
    except ValueError as exc:
        print(f"ERROR: invalid build command: {exc}", file=sys.stderr)
        return 2
    if not cmd:
        print("ERROR: empty build command", file=sys.stderr)
        return 2

    print(f"Running build command: {command_str}")
    rc = u.run(cmd, cwd=project_dir, env=env)
    if rc != 0:
        return int(rc)

    rc = u.run_hooks(
        config,
        args=args,
        phase="post",
        event="shipment.run-build",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)
    return 0


def cmd_shipment_clean(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    dry_run = bool(getattr(args, "dry_run", False))

    to_remove = [
        project_dir / "_build",
        project_dir / "build",
        project_dir / "target",
        project_dir / "__pycache__",
        project_dir / ".pytest_cache",
        project_dir / "_diagrams",
    ]
    if bool(getattr(args, "aggressive", False)):
        to_remove.append(project_dir / "diagrams")

    removed_any = False
    for p in to_remove:
        if not p.exists():
            continue
        removed_any = True
        try:
            u.safe_rmtree(p, dry_run=dry_run)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    if not removed_any:
        print("Nothing to clean.")
        return 0
    print("DRY-RUN: clean complete." if dry_run else "Clean complete.")
    return 0


def cmd_shipment_traceability(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    needs_json = (
        Path(args.needs_json).resolve() if getattr(args, "needs_json", None) else u.find_needs_json(shipment_dir)
    )
    if needs_json is None or not needs_json.is_file():
        print(f"ERROR: needs.json not found in shipment: {shipment_dir}", file=sys.stderr)
        return 2

    json_report = (
        Path(args.json_report).resolve()
        if getattr(args, "json_report", None)
        else (shipment_dir / u.DEFAULT_TRACEABILITY_REPORT)
    )

    argv = [str(needs_json), "--json-report", str(json_report)]
    if bool(getattr(args, "enforce_req_has_test", False)):
        argv += ["--enforce-req-has-test"]
    if bool(getattr(args, "enforce_arch_traces_req", False)):
        argv += ["--enforce-arch-traces-req"]
    if bool(getattr(args, "enforce_test_traces_req", False)):
        argv += ["--enforce-test-traces-req"]

    return int(traceability_cli(argv))


def cmd_shipment_checksums(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    manifest = (
        Path(args.manifest).resolve() if getattr(args, "manifest", None) else (shipment_dir / u.DEFAULT_CHECKSUM_MANIFEST)
    )

    mode = getattr(args, "mode", "verify")
    if mode == "generate":
        argv: list[str] = ["--root", str(shipment_dir), "--output", str(manifest)]
        for ex in getattr(args, "exclude", []) or []:
            argv += ["--exclude", str(ex)]
        if getattr(args, "json_report", None):
            argv += ["--json-report", str(args.json_report)]
        return int(checksums_cli(argv))

    argv = ["--root", str(shipment_dir), "--verify", str(manifest)]
    for ex in getattr(args, "exclude", []) or []:
        argv += ["--exclude", str(ex)]
    if getattr(args, "json_report", None):
        argv += ["--json-report", str(args.json_report)]
    return int(checksums_cli(argv))


def cmd_shipment_copy_test_reports(args: argparse.Namespace) -> int:
    project_dir = Path(args.project).resolve()
    shipment_dir = (
        Path(args.shipment).resolve() if getattr(args, "shipment", None) else u.default_shipment_dir(project_dir)
    )
    globs = tuple(getattr(args, "glob", []) or [])
    globs = globs if globs else u.DEFAULT_TEST_REPORT_GLOBS
    return int(u.copy_test_reports(project_dir, shipment_dir, dry_run=bool(getattr(args, "dry_run", False)), globs=globs))


def cmd_shipment_package(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    if not shipment_dir.is_dir():
        print(f"ERROR: shipment directory not found: {shipment_dir}", file=sys.stderr)
        return 2

    out = Path(args.output).resolve() if getattr(args, "output", None) else shipment_dir.with_suffix(".zip")
    if out.suffix.lower() != ".zip":
        print(f"ERROR: only .zip archives are supported (got: {out})", file=sys.stderr)
        return 2
    root_name = shipment_dir.name

    if bool(getattr(args, "dry_run", False)):
        print(f"DRY-RUN: would create archive {out} from {shipment_dir}")
        return 0

    def zip_timestamp() -> tuple[int, int, int, int, int, int]:
        epoch_raw = os.environ.get("SOURCE_DATE_EPOCH")
        if epoch_raw:
            try:
                dt = datetime.fromtimestamp(int(epoch_raw), tz=timezone.utc)
            except (ValueError, OSError):
                dt = datetime.now(tz=timezone.utc)
        else:
            dt = datetime.now(tz=timezone.utc)
        if dt.year < 1980:
            dt = datetime(1980, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    zip_dt = zip_timestamp()
    files = sorted(
        (p for p in shipment_dir.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(shipment_dir).as_posix(),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_STORED) as zf:
        for src in files:
            if src.is_symlink():
                print(f"WARNING: skipping symlink in archive: {src}")
                continue

            rel = src.relative_to(shipment_dir).as_posix()
            arcname = f"{root_name}/{rel}"

            zi = zipfile.ZipInfo(filename=arcname, date_time=zip_dt)
            zi.compress_type = zipfile.ZIP_STORED

            mode = int(src.stat().st_mode) & 0o777
            zi.external_attr = (stat.S_IFREG | mode) << 16

            with src.open("rb") as fsrc, zf.open(zi, "w") as fdst:
                shutil.copyfileobj(fsrc, fdst)

    print(f"Wrote archive: {out}")
    return 0


def cmd_shipment_metadata_write(args: argparse.Namespace) -> int:
    shipment_dir = Path(args.shipment).resolve()
    if not shipment_dir.is_dir():
        print(f"ERROR: shipment directory not found: {shipment_dir}", file=sys.stderr)
        return 2

    metadata: dict[str, object] = {
        "schema": "osqar.shipment_project_metadata.v1",
        "written_at": u.utc_now_iso(),
    }

    if getattr(args, "name", None):
        metadata["name"] = args.name
    if getattr(args, "project_id", None):
        metadata["id"] = args.project_id
    if getattr(args, "version", None):
        metadata["version"] = args.version
    if getattr(args, "description", None):
        metadata["description"] = args.description

    try:
        if getattr(args, "url", None):
            metadata["urls"] = u.parse_kv(list(args.url))
        if getattr(args, "origin", None):
            metadata["origin"] = u.parse_kv(list(args.origin))
        if getattr(args, "set", None):
            for item in list(args.set):
                if "=" not in item:
                    raise ValueError(f"Expected KEY=VALUE, got: {item}")
                k, v = item.split("=", 1)
                u.set_nested_value(metadata, k.strip(), v.strip())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return int(
        u.write_project_metadata(
            shipment_dir,
            metadata,
            overwrite=bool(getattr(args, "overwrite", False)),
            dry_run=bool(getattr(args, "dry_run", False)),
        )
    )


def _shipment_prepare_impl(args: argparse.Namespace, *, label: str) -> int:
    project_dir = Path(args.project).resolve()
    if not u.is_shipment_project_dir(project_dir):
        print(
            f"ERROR: not a shipment project directory (missing conf.py/index.rst): {project_dir}",
            file=sys.stderr,
        )
        return 2

    config = u.read_project_config(project_dir, explicit_path=getattr(args, "config", None))
    shipment_dir = Path(args.shipment).resolve() if getattr(args, "shipment", None) else u.default_shipment_dir(project_dir)

    env = {"OSQAR_PROJECT_DIR": str(project_dir), "OSQAR_SHIPMENT_DIR": str(shipment_dir)}
    env.update(u.reproducible_env(project_dir, reproducible=bool(getattr(args, "reproducible", True))))

    rc = u.run_hooks(
        config,
        args=args,
        phase="pre",
        event="shipment.prepare",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    if bool(getattr(args, "clean", False)):
        rc = cmd_shipment_clean(
            argparse.Namespace(
                project=str(project_dir),
                dry_run=bool(getattr(args, "dry_run", False)),
                aggressive=False,
            )
        )
        if rc != 0:
            return int(rc)

    if not bool(getattr(args, "skip_build", False)):
        build_command = getattr(args, "build_command", None)
        if not build_command:
            commands = config.get("commands") if isinstance(config, dict) else None
            if isinstance(commands, dict) and isinstance(commands.get("build"), str):
                build_command = commands.get("build")

        if build_command:
            rc = cmd_shipment_run_build(
                argparse.Namespace(
                    project=str(project_dir),
                    command=str(build_command),
                    config=getattr(args, "config", None),
                    no_hooks=bool(getattr(args, "no_hooks", False)),
                    reproducible=bool(getattr(args, "reproducible", True)),
                )
            )
            if rc != 0:
                return int(rc)

    if not bool(getattr(args, "skip_tests", False)):
        script = project_dir / (getattr(args, "script", None) or "build-and-test.sh")
        rc = cmd_shipment_run_tests(
            argparse.Namespace(
                project=str(project_dir),
                script=str(script.name),
                command=getattr(args, "test_command", None),
                config=getattr(args, "config", None),
                no_hooks=bool(getattr(args, "no_hooks", False)),
                reproducible=bool(getattr(args, "reproducible", True)),
            )
        )
        if rc != 0:
            return int(rc)

    rc = u.run_docs_build(project_dir, shipment_dir, config=config)
    if rc != 0:
        return int(rc)

    # Bundle non-doc evidence alongside docs.
    u.copy_bundle_sources_and_reports(project_dir, shipment_dir, dry_run=bool(getattr(args, "dry_run", False)))
    u.copy_test_reports(project_dir, shipment_dir, dry_run=bool(getattr(args, "dry_run", False)), globs=u.DEFAULT_TEST_REPORT_GLOBS)

    # Code traceability check (source-level ID tags) against needs.json.
    if not bool(getattr(args, "skip_code_trace", False)):
        language = u.detect_language(project_dir)
        needs_json = shipment_dir / "needs.json"
        code_trace_report = shipment_dir / "code_trace_report.json"
        argv: list[str] = [
            "--root",
            str(shipment_dir),
            "--json-report",
            str(code_trace_report),
        ]
        if needs_json.is_file():
            argv += ["--needs-json", str(needs_json)]

        for d in (
            shipment_dir / "implementation" / "src",
            shipment_dir / "implementation" / "include",
            shipment_dir / "implementation" / "lib",
        ):
            argv += ["--impl-dir", str(d)]

        for d in u.code_trace_test_dirs_for_shipment(shipment_dir, language=language):
            argv += ["--test-dir", str(d)]

        exclude = list(getattr(args, "exclude", []) or []) + [
            "**/_build/**",
            "_build/**",
            "**/.venv/**",
            ".venv/**",
        ]
        for ex in exclude:
            argv += ["--exclude", str(ex)]

        argv += ["--enforce-req-in-impl", "--enforce-arch-in-impl", "--enforce-test-in-tests"]
        if bool(getattr(args, "enforce_no_unknown_ids", False)):
            argv += ["--enforce-no-unknown-ids"]

        rc_ct = int(code_trace_cli(argv))
        if rc_ct != 0:
            if bool(getattr(args, "code_trace_warn_only", False)):
                print(
                    f"WARNING: code-trace reported issues (rc={rc_ct}) but continuing due to --code-trace-warn-only",
                    file=sys.stderr,
                )
            else:
                return int(rc_ct)

    # Traceability report into shipment root.
    rc = cmd_shipment_traceability(
        argparse.Namespace(
            shipment=str(shipment_dir),
            needs_json=None,
            json_report=str(shipment_dir / u.DEFAULT_TRACEABILITY_REPORT),
            enforce_req_has_test=bool(getattr(args, "enforce_req_has_test", False)),
            enforce_arch_traces_req=bool(getattr(args, "enforce_arch_traces_req", False)),
            enforce_test_traces_req=bool(getattr(args, "enforce_test_traces_req", False)),
        )
    )
    if rc != 0:
        return int(rc)

    if bool(getattr(args, "doctor", False)):
        from tools.osqar_cmd_doctor import cmd_doctor

        doctor_report = shipment_dir / u.DEFAULT_DOCTOR_REPORT
        d_rc = int(
            cmd_doctor(
                argparse.Namespace(
                    project=str(project_dir),
                    shipment=str(shipment_dir),
                    json_report=str(doctor_report),
                    traceability=True,
                    needs_json=None,
                    exclude=list(getattr(args, "exclude", []) or []),
                    skip_checksums=True,
                    skip_traceability=False,
                    skip_shipment_checks=False,
                    skip_env_checks=False,
                    enforce_req_has_test=bool(getattr(args, "enforce_req_has_test", False)),
                    enforce_arch_traces_req=bool(getattr(args, "enforce_arch_traces_req", False)),
                    enforce_test_traces_req=bool(getattr(args, "enforce_test_traces_req", False)),
                )
            )
        )
        if d_rc != 0:
            print(
                f"ERROR: doctor found issues in the would-be shipment (rc={d_rc}); aborting before checksums generation",
                file=sys.stderr,
            )
            return int(d_rc)

    # Checksums: generate and immediately verify.
    rc = cmd_shipment_checksums(
        argparse.Namespace(
            shipment=str(shipment_dir),
            manifest=str(shipment_dir / u.DEFAULT_CHECKSUM_MANIFEST),
            mode="generate",
            exclude=list(getattr(args, "exclude", []) or []),
            json_report=None,
        )
    )
    if rc != 0:
        return int(rc)

    rc = cmd_shipment_checksums(
        argparse.Namespace(
            shipment=str(shipment_dir),
            manifest=str(shipment_dir / u.DEFAULT_CHECKSUM_MANIFEST),
            mode="verify",
            exclude=list(getattr(args, "exclude", []) or []),
            json_report=None,
        )
    )
    if rc != 0:
        return int(rc)

    if bool(getattr(args, "archive", False)):
        rc = cmd_shipment_package(
            argparse.Namespace(
                shipment=str(shipment_dir),
                output=getattr(args, "archive_output", None),
                dry_run=bool(getattr(args, "dry_run", False)),
            )
        )
        if rc != 0:
            return int(rc)

    print(f"{label} ready: {shipment_dir}")
    rc = u.run_hooks(
        config,
        args=args,
        phase="post",
        event="shipment.prepare",
        cwd=project_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)
    return 0


def cmd_shipment_prepare(args: argparse.Namespace) -> int:
    return int(_shipment_prepare_impl(args, label="Shipment"))


def _shipment_verify_static_checks(
    shipment_dir: Path,
) -> tuple[list[dict[str, object]], list[str], list[str]]:
    checks: list[dict[str, object]] = []
    warnings: list[str] = []
    errors: list[str] = []

    def warn(msg: str) -> None:
        print(f"WARN: {msg}")
        warnings.append(msg)

    def bad(msg: str) -> None:
        print(f"ERROR: {msg}")
        errors.append(msg)

    index = shipment_dir / "index.html"
    if index.is_file():
        checks.append({"name": "shipment.index_html", "status": "ok", "path": str(index)})
    else:
        warn("shipment is missing index.html")
        checks.append(
            {"name": "shipment.index_html", "status": "missing", "path": str(index)}
        )

    md_path = shipment_dir / u.DEFAULT_PROJECT_METADATA
    md = u.read_project_metadata(shipment_dir)
    if md_path.is_file() and md:
        checks.append({"name": "shipment.metadata", "status": "ok", "path": str(md_path)})
        if not md.get("version"):
            warn("shipment metadata has no version")
        origin = md.get("origin")
        if not isinstance(origin, dict) or not origin:
            warn("shipment metadata has no origin")
    elif md_path.is_file() and not md:
        bad(f"failed to parse shipment metadata: {md_path}")
        checks.append({"name": "shipment.metadata", "status": "error", "path": str(md_path)})
    else:
        bad("shipment has no osqar_project.json metadata")
        checks.append({"name": "shipment.metadata", "status": "missing", "path": str(md_path)})

    needs_json = u.find_needs_json(shipment_dir)
    if needs_json and needs_json.is_file():
        checks.append({"name": "shipment.needs_json", "status": "ok", "path": str(needs_json)})
    else:
        warn("shipment has no needs.json")
        checks.append({"name": "shipment.needs_json", "status": "missing", "path": str(shipment_dir / "needs.json")})

    tr_report = shipment_dir / u.DEFAULT_TRACEABILITY_REPORT
    if tr_report.is_file():
        checks.append({"name": "shipment.traceability_report", "status": "ok", "path": str(tr_report)})
    else:
        warn("shipment is missing traceability_report.json")
        checks.append({"name": "shipment.traceability_report", "status": "missing", "path": str(tr_report)})

    return checks, warnings, errors


def _shipment_verify_impl(args: argparse.Namespace, *, label: str) -> int:
    import tempfile

    shipment_dir = Path(args.shipment).resolve()
    if not shipment_dir.is_dir():
        print(f"ERROR: shipment directory not found: {shipment_dir}", file=sys.stderr)
        return 2

    ws_root = Path(getattr(args, "config_root", ".")).expanduser().resolve()
    ws_config = u.read_workspace_config(ws_root, explicit_path=getattr(args, "config", None))

    env = {
        "OSQAR_SHIPMENT_DIR": str(shipment_dir),
        "OSQAR_WORKSPACE_ROOT": str(ws_root),
    }
    rc = u.run_hooks(
        ws_config,
        args=args,
        phase="pre",
        event="shipment.verify",
        cwd=shipment_dir,
        env=env,
    )
    if rc != 0:
        return int(rc)

    manifest = (
        Path(args.manifest).resolve() if getattr(args, "manifest", None) else (shipment_dir / u.DEFAULT_CHECKSUM_MANIFEST)
    )
    if not manifest.is_file():
        print(f"ERROR: checksum manifest not found: {manifest}", file=sys.stderr)
        return 2

    checks, warns, errs = _shipment_verify_static_checks(shipment_dir)

    checksums_report_data: Optional[dict] = None
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tf:
        tmp_checksums = Path(tf.name)
    try:
        rc_checksums = cmd_shipment_checksums(
            argparse.Namespace(
                shipment=str(shipment_dir),
                manifest=str(manifest),
                mode="verify",
                exclude=list(getattr(args, "exclude", []) or []),
                json_report=str(tmp_checksums),
            )
        )
        if tmp_checksums.is_file():
            try:
                data = json.loads(tmp_checksums.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    checksums_report_data = data
            except Exception:
                pass
        if rc_checksums != 0:
            errs.append("checksums verify failed")
    finally:
        try:
            tmp_checksums.unlink(missing_ok=True)
        except Exception:
            pass

    trace_rc: Optional[int] = None
    trace_report: Optional[str] = None
    tmp_trace_report: Optional[Path] = None
    if bool(getattr(args, "traceability", False)):
        if getattr(args, "json_report", None):
            report = Path(args.json_report).resolve()
        else:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tf:
                tmp_trace_report = Path(tf.name)
            report = tmp_trace_report

        trace_rc = int(
            cmd_shipment_traceability(
                argparse.Namespace(
                    shipment=str(shipment_dir),
                    needs_json=getattr(args, "needs_json", None),
                    json_report=str(report),
                    enforce_req_has_test=bool(getattr(args, "enforce_req_has_test", False)),
                    enforce_arch_traces_req=bool(getattr(args, "enforce_arch_traces_req", False)),
                    enforce_test_traces_req=bool(getattr(args, "enforce_test_traces_req", False)),
                )
            )
        )
        trace_report = str(report)
        if trace_rc != 0:
            errs.append("traceability check failed")

        needs_json = (
            u.find_needs_json(shipment_dir)
            if not getattr(args, "needs_json", None)
            else Path(args.needs_json)
        )
        if needs_json is None or not Path(needs_json).is_file():
            errs.append("traceability requested but needs.json not found")

        if tmp_trace_report is not None:
            try:
                tmp_trace_report.unlink(missing_ok=True)
            except Exception:
                pass

    code_trace_rc: Optional[int] = None
    code_trace_report: Optional[str] = None
    tmp_code_trace_report: Optional[Path] = None
    if not bool(getattr(args, "skip_code_trace", False)):
        language = u.detect_shipment_language(shipment_dir)
        needs_json_path = (
            Path(args.needs_json).resolve()
            if getattr(args, "needs_json", None)
            else (shipment_dir / "needs.json")
        )

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tf:
            tmp_code_trace_report = Path(tf.name)
        report = tmp_code_trace_report

        argv: list[str] = ["--root", str(shipment_dir), "--json-report", str(report)]
        if needs_json_path.is_file():
            argv += ["--needs-json", str(needs_json_path)]
        for d in (
            shipment_dir / "implementation" / "src",
            shipment_dir / "implementation" / "include",
            shipment_dir / "implementation" / "lib",
        ):
            argv += ["--impl-dir", str(d)]
        for d in u.code_trace_test_dirs_for_shipment(shipment_dir, language=language):
            argv += ["--test-dir", str(d)]
        exclude = list(getattr(args, "exclude", []) or []) + [
            "**/_build/**",
            "_build/**",
            "**/.venv/**",
            ".venv/**",
        ]
        for ex in exclude:
            argv += ["--exclude", str(ex)]
        argv += ["--enforce-req-in-impl", "--enforce-arch-in-impl", "--enforce-test-in-tests"]
        if bool(getattr(args, "enforce_no_unknown_ids", False)):
            argv += ["--enforce-no-unknown-ids"]

        code_trace_rc = int(code_trace_cli(argv))
        code_trace_report = str(report)
        if code_trace_rc != 0:
            if bool(getattr(args, "code_trace_warn_only", False)):
                warns.append("code-trace check reported issues")
            else:
                errs.append("code-trace check failed")

        if tmp_code_trace_report is not None:
            try:
                tmp_code_trace_report.unlink(missing_ok=True)
            except Exception:
                pass

    strict = bool(getattr(args, "strict", False))
    rc_final = 0
    if errs:
        rc_final = 1
    elif strict and (warns or errs):
        rc_final = 1

    if getattr(args, "report_json", None):
        out = Path(args.report_json).expanduser().resolve()
        report_payload: dict[str, object] = {
            "schema": "osqar.shipment_verify_report.v1",
            "generated_at": u.utc_now_iso(),
            "shipment": str(shipment_dir),
            "manifest": str(manifest),
            "checksums_rc": int(rc_checksums),
            "checksums_report": checksums_report_data,
            "traceability": bool(getattr(args, "traceability", False)),
            "traceability_rc": int(trace_rc) if trace_rc is not None else None,
            "traceability_report": trace_report,
            "code_trace": not bool(getattr(args, "skip_code_trace", False)),
            "code_trace_rc": int(code_trace_rc) if code_trace_rc is not None else None,
            "code_trace_report": code_trace_report,
            "warnings": warns,
            "errors": errs,
            "checks": checks,
            "metadata": u.read_project_metadata(shipment_dir),
            "needs_summary": u.read_needs_summary_from_shipment(shipment_dir),
        }
        u.write_json_report(out, report_payload)
        print(f"Wrote shipment verify report: {out}")

    if rc_final == 0:
        extra_cmds = list(getattr(args, "verify_command", []) or [])
        for cmd in extra_cmds:
            vrc = u.run_command_string(str(cmd), cwd=shipment_dir, env=env)
            if vrc != 0:
                errs.append("custom verify command failed")
                rc_final = 1
                break

    if rc_final == 0:
        print(f"{label} passed.")
        rc2 = u.run_hooks(
            ws_config,
            args=args,
            phase="post",
            event="shipment.verify",
            cwd=shipment_dir,
            env=env,
        )
        return 0 if rc2 == 0 else int(rc2)

    print(f"{label} FAILED.")
    u.run_hooks(
        ws_config,
        args=args,
        phase="post",
        event="shipment.verify",
        cwd=shipment_dir,
        env=env,
    )
    return 1


def cmd_shipment_verify(args: argparse.Namespace) -> int:
    return int(_shipment_verify_impl(args, label="Shipment verification"))


def register_build_docs_shortcut(sub: argparse._SubParsersAction) -> None:
    p_build_docs = sub.add_parser(
        "build-docs",
        help="Build Sphinx HTML output (shorthand for 'shipment build-docs')",
    )
    p_build_docs.add_argument(
        "--project",
        default=".",
        help="Shipment project directory (default: .; must contain conf.py/index.rst)",
    )
    p_build_docs.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_build_docs.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
    )
    p_build_docs.add_argument(
        "--output",
        default=None,
        help="Output directory (default: <project>/_build/html)",
    )
    p_build_docs.add_argument(
        "--open",
        action="store_true",
        help="Open the built index.html in your default browser",
    )
    p_build_docs.set_defaults(func=cmd_shipment_build_docs)


def register(sub: argparse._SubParsersAction) -> None:
    p_ship = sub.add_parser(
        "shipment",
        help="Work with shippable evidence bundles (build, clean, verify)",
    )
    ship_sub = p_ship.add_subparsers(dest="shipment_cmd", required=True)

    p_prep = ship_sub.add_parser(
        "prepare",
        help="Build docs, run traceability + checksums, and optionally archive a shippable evidence bundle",
    )
    p_prep.add_argument("--project", required=True, help="Shipment project directory")
    p_prep.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_prep.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
    )
    p_prep.add_argument(
        "--shipment",
        default=None,
        help="Shipment output directory (default: <project>/_build/html)",
    )
    p_prep.add_argument(
        "--clean",
        action="store_true",
        help="Clean generated outputs before building",
    )
    p_prep.add_argument(
        "--dry-run",
        action="store_true",
        help="Print destructive ops without executing",
    )
    p_prep.add_argument(
        "--script",
        default=None,
        help="Test/build script name (default: build-and-test.sh)",
    )
    p_prep.add_argument(
        "--reproducible",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable reproducible build/test mode for this shipment (default: enabled)",
    )
    p_prep.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip running the build step (if commands.build is configured)",
    )
    p_prep.add_argument(
        "--build-command",
        dest="build_command",
        default=None,
        help="Override build command (otherwise use commands.build from osqar_project.json)",
    )
    p_prep.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running the test/build script",
    )
    p_prep.add_argument(
        "--test-command",
        dest="test_command",
        default=None,
        help="Override test/build command (otherwise use commands.test from osqar_project.json or --script)",
    )
    p_prep.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum generation",
    )
    p_prep.add_argument("--enforce-req-has-test", action="store_true")
    p_prep.add_argument("--enforce-arch-traces-req", action="store_true")
    p_prep.add_argument("--enforce-test-traces-req", action="store_true")
    p_prep.add_argument(
        "--archive",
        action="store_true",
        help="Also create a .zip of the shipment directory",
    )
    p_prep.add_argument(
        "--archive-output",
        default=None,
        help="Archive output path (default: <shipment>.zip)",
    )
    p_prep.add_argument(
        "--doctor",
        action="store_true",
        help="Also write a doctor report into the shipped directory before generating checksums",
    )
    p_prep.add_argument(
        "--skip-code-trace",
        action="store_true",
        help="Skip source-level code traceability check (code-trace)",
    )
    p_prep.add_argument(
        "--code-trace-warn-only",
        action="store_true",
        help="Do not fail the shipment if code-trace reports issues; emit warnings instead",
    )
    p_prep.add_argument(
        "--enforce-no-unknown-ids",
        action="store_true",
        help="Fail code-trace if unknown IDs are found in code (optional)",
    )
    p_prep.set_defaults(func=cmd_shipment_prepare)

    p_ver = ship_sub.add_parser(
        "verify",
        help="Verify a received shipment directory (integrity + optional traceability re-check)",
    )
    p_ver.add_argument("--shipment", required=True, help="Received shipment directory")
    p_ver.add_argument(
        "--config-root",
        default=".",
        help="Root directory for workspace config lookup (default: .)",
    )
    p_ver.add_argument(
        "--config",
        default=None,
        help="Workspace configuration JSON (default: <config-root>/osqar_workspace.json)",
    )
    p_ver.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
    )
    p_ver.add_argument(
        "--verify-command",
        action="append",
        default=[],
        help="Extra integrator-side verification command to run after built-in checks (repeatable)",
    )
    p_ver.add_argument(
        "--manifest",
        default=None,
        help="Checksum manifest (default: <shipment>/SHA256SUMS)",
    )
    p_ver.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob(s) for checksum verify",
    )
    p_ver.add_argument(
        "--traceability",
        action="store_true",
        help="Also validate needs.json traceability",
    )
    p_ver.add_argument("--needs-json", default=None, help="Override needs.json path")
    p_ver.add_argument(
        "--json-report",
        default=None,
        help="Write verification-side traceability report",
    )
    p_ver.add_argument(
        "--report-json",
        default=None,
        help="Write a machine-readable verification summary report",
    )
    p_ver.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures",
    )
    p_ver.add_argument(
        "--skip-code-trace",
        action="store_true",
        help="Skip source-level code traceability check (code-trace)",
    )
    p_ver.add_argument(
        "--code-trace-warn-only",
        action="store_true",
        help="Do not fail verification if code-trace reports issues; emit warnings instead",
    )
    p_ver.add_argument(
        "--enforce-no-unknown-ids",
        action="store_true",
        help="Fail code-trace if unknown IDs are found in code (optional)",
    )
    p_ver.add_argument("--enforce-req-has-test", action="store_true")
    p_ver.add_argument("--enforce-arch-traces-req", action="store_true")
    p_ver.add_argument("--enforce-test-traces-req", action="store_true")
    p_ver.set_defaults(func=cmd_shipment_verify)

    p_list = ship_sub.add_parser("list", help="Discover shipment projects under a directory")
    p_list.add_argument("--root", default=".", help="Root directory to scan (default: .)")
    p_list.add_argument("--recursive", action="store_true", help="Recursively scan for conf.py")
    p_list.add_argument("--format", choices=["pretty", "paths"], default="pretty")
    p_list.set_defaults(func=cmd_shipment_list)

    p_build = ship_sub.add_parser("build-docs", help="Build Sphinx HTML output for a shipment project")
    p_build.add_argument(
        "--project",
        default=".",
        help="Shipment project directory (default: .; must contain conf.py/index.rst)",
    )
    p_build.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_build.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
    )
    p_build.add_argument(
        "--output",
        default=None,
        help="Output directory (default: <project>/_build/html)",
    )
    p_build.add_argument(
        "--open",
        action="store_true",
        help="Open the built index.html in your default browser",
    )
    p_build.set_defaults(func=cmd_shipment_build_docs)

    p_tests = ship_sub.add_parser("run-tests", help="Run a shipment's build-and-test script")
    p_tests.add_argument("--project", required=True, help="Shipment project directory")
    p_tests.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_tests.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
    )
    p_tests.add_argument(
        "--command",
        default=None,
        help="Override test/build command (otherwise read commands.test from osqar_project.json or use --script)",
    )
    p_tests.add_argument("--script", default=None, help="Script name (default: build-and-test.sh)")
    p_tests.add_argument(
        "--reproducible",
        action="store_true",
        help="Enable reproducible mode for this run (sets OSQAR_REPRODUCIBLE=1; best-effort SOURCE_DATE_EPOCH)",
    )
    p_tests.set_defaults(func=cmd_shipment_run_tests)

    p_build2 = ship_sub.add_parser(
        "run-build",
        help="Run a project-specific build command (configured per project)",
    )
    p_build2.add_argument("--project", required=True, help="Shipment project directory")
    p_build2.add_argument(
        "--config",
        default=None,
        help="Project configuration JSON (default: <project>/osqar_project.json)",
    )
    p_build2.add_argument(
        "--no-hooks",
        action="store_true",
        help=f"Disable pre/post hooks (also disable via ${u.HOOK_DISABLE_ENV}=1)",
    )
    p_build2.add_argument(
        "--command",
        default=None,
        help="Override build command (otherwise read commands.build from <project>/osqar_project.json)",
    )
    p_build2.add_argument(
        "--reproducible",
        action="store_true",
        help="Enable reproducible mode for this run (sets OSQAR_REPRODUCIBLE=1; best-effort SOURCE_DATE_EPOCH)",
    )
    p_build2.set_defaults(func=cmd_shipment_run_build)

    p_clean = ship_sub.add_parser("clean", help="Remove generated outputs (conservative by default)")
    p_clean.add_argument("--project", required=True, help="Shipment project directory")
    p_clean.add_argument("--dry-run", action="store_true", help="Print what would be removed")
    p_clean.add_argument(
        "--aggressive",
        action="store_true",
        help="Also remove 'diagrams/' if present",
    )
    p_clean.set_defaults(func=cmd_shipment_clean)

    p_tr2 = ship_sub.add_parser("traceability", help="Run traceability checks for a built shipment directory")
    p_tr2.add_argument("--shipment", required=True, help="Shipment directory (usually <project>/_build/html)")
    p_tr2.add_argument(
        "--needs-json",
        default=None,
        help="Override needs.json path (default: <shipment>/needs.json)",
    )
    p_tr2.add_argument(
        "--json-report",
        default=None,
        help="Write JSON report (default: <shipment>/traceability_report.json)",
    )
    p_tr2.add_argument("--enforce-req-has-test", action="store_true")
    p_tr2.add_argument("--enforce-arch-traces-req", action="store_true")
    p_tr2.add_argument("--enforce-test-traces-req", action="store_true")
    p_tr2.set_defaults(func=cmd_shipment_traceability)

    p_cs = ship_sub.add_parser(
        "checksums",
        help="Generate or verify checksum manifests for a shipment directory",
    )
    p_cs.add_argument("--shipment", required=True, help="Shipment directory")
    p_cs.add_argument(
        "--manifest",
        default=None,
        help="Manifest path (default: <shipment>/SHA256SUMS)",
    )
    p_cs.add_argument("--exclude", action="append", default=[], help="Exclude glob (repeatable)")
    p_cs.add_argument(
        "--json-report",
        default=None,
        help="Write machine-readable JSON report to this path",
    )
    p_cs.add_argument("mode", choices=["generate", "verify"], help="Operation")
    p_cs.set_defaults(func=cmd_shipment_checksums)

    p_rep = ship_sub.add_parser("copy-test-reports", help="Copy raw JUnit XML into the shipment directory")
    p_rep.add_argument("--project", required=True, help="Shipment project directory")
    p_rep.add_argument(
        "--shipment",
        default=None,
        help="Shipment directory (default: <project>/_build/html)",
    )
    p_rep.add_argument(
        "--glob",
        action="append",
        default=[],
        help="Glob to match report files (repeatable)",
    )
    p_rep.add_argument("--dry-run", action="store_true")
    p_rep.set_defaults(func=cmd_shipment_copy_test_reports)

    p_pkg = ship_sub.add_parser("package", help="Archive a shipment directory into a .zip")
    p_pkg.add_argument("--shipment", required=True, help="Shipment directory")
    p_pkg.add_argument(
        "--output",
        default=None,
        help="Archive output path (default: <shipment>.zip)",
    )
    p_pkg.add_argument("--dry-run", action="store_true")
    p_pkg.set_defaults(func=cmd_shipment_package)

    p_meta = ship_sub.add_parser(
        "metadata",
        help="Add project metadata (descriptive info, URLs, origin) to a shipment",
    )
    meta_sub = p_meta.add_subparsers(dest="metadata_cmd", required=True)
    p_meta_write = meta_sub.add_parser("write", help="Write osqar_project.json into a shipment directory")
    p_meta_write.add_argument("--shipment", required=True, help="Shipment directory")
    p_meta_write.add_argument("--name", default=None, help="Human-friendly project name")
    p_meta_write.add_argument("--id", dest="project_id", default=None, help="Stable project identifier")
    p_meta_write.add_argument("--version", default=None, help="Project/shipment version")
    p_meta_write.add_argument("--description", default=None, help="Short description")
    p_meta_write.add_argument("--url", action="append", default=[], help="URL as KEY=VALUE (repeatable)")
    p_meta_write.add_argument(
        "--origin",
        action="append",
        default=[],
        help="Origin as KEY=VALUE (repeatable), e.g. url=... revision=...",
    )
    p_meta_write.add_argument(
        "--set",
        action="append",
        default=[],
        help="Set arbitrary metadata as KEY=VALUE (supports dotted keys, e.g. supplier.name=ACME)",
    )
    p_meta_write.add_argument("--overwrite", action="store_true")
    p_meta_write.add_argument("--dry-run", action="store_true")
    p_meta_write.set_defaults(func=cmd_shipment_metadata_write)
