from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.generate_checksums import cli


def _line(path: str, content: bytes) -> str:
    return f"{hashlib.sha256(content).hexdigest()}  {path}\n"


def test_closed_set_rejects_unexpected_regular_file(tmp_path: Path) -> None:
    (tmp_path / "declared.txt").write_text("declared\n", encoding="utf-8")
    manifest = tmp_path / "SHA256SUMS"
    assert cli(["--root", str(tmp_path), "--output", str(manifest)]) == 0
    (tmp_path / "UNLISTED.txt").write_text("unexpected\n", encoding="utf-8")
    report = tmp_path.parent / "closed-report.json"

    assert cli(["--root", str(tmp_path), "--verify", str(manifest)]) == 0
    rc = cli(
        [
            "--root",
            str(tmp_path),
            "--verify",
            str(manifest),
            "--closed-set",
            "--json-report",
            str(report),
        ]
    )

    assert rc == 1
    payload = json.loads(report.read_text())
    assert payload["closed_set"] is True
    assert payload["unexpected"] == ["UNLISTED.txt"]
    assert payload["status"] == "FAIL"


def test_closed_set_honors_explicit_reported_exclusion(tmp_path: Path) -> None:
    data = b"declared\n"
    (tmp_path / "declared.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(_line("declared.txt", data), encoding="utf-8")
    (tmp_path / "transient.log").write_text("transient\n", encoding="utf-8")
    report = tmp_path.parent / "exclusion-report.json"

    rc = cli(
        [
            "--root",
            str(tmp_path),
            "--verify",
            str(manifest),
            "--closed-set",
            "--exclude",
            "*.log",
            "--json-report",
            str(report),
        ]
    )

    assert rc == 0
    payload = json.loads(report.read_text())
    assert "*.log" in payload["excluded"]
    assert payload["unexpected"] == []


def test_closed_set_report_inside_root_is_idempotently_excluded(tmp_path: Path) -> None:
    data = b"declared\n"
    (tmp_path / "declared.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(_line("declared.txt", data), encoding="utf-8")
    report = tmp_path / "evidence" / "checksum-report.json"
    argv = [
        "--root",
        str(tmp_path),
        "--verify",
        str(manifest),
        "--closed-set",
        "--json-report",
        str(report),
    ]

    assert cli(argv) == 0
    assert cli(argv) == 0
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "PASS"


def test_closed_set_excludes_only_exact_report_path_inside_root(tmp_path: Path) -> None:
    data = b"declared\n"
    (tmp_path / "declared.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(_line("declared.txt", data), encoding="utf-8")
    report = tmp_path / "reports" / "checksum.json"
    report.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "schema": "osqar.checksums_report.v1",
                "root": str(tmp_path.resolve()),
                "manifest": str(manifest.resolve()),
            }
        ),
        encoding="utf-8",
    )
    (report.parent / "other.json").write_text("must remain inventoried\n", encoding="utf-8")

    rc = cli(
        [
            "--root",
            str(tmp_path),
            "--verify",
            str(manifest),
            "--closed-set",
            "--json-report",
            str(report),
        ]
    )

    assert rc == 1
    assert json.loads(report.read_text(encoding="utf-8"))["unexpected"] == [
        "reports/other.json"
    ]


def test_generation_excludes_prior_report_inside_root_for_stable_reruns(
    tmp_path: Path,
) -> None:
    (tmp_path / "declared.txt").write_text("declared\n", encoding="utf-8")
    manifest = tmp_path / "SHA256SUMS"
    report = tmp_path / "evidence" / "checksum-report.json"
    argv = [
        "--root",
        str(tmp_path),
        "--output",
        str(manifest),
        "--json-report",
        str(report),
    ]

    assert cli(argv) == 0
    first_manifest = manifest.read_bytes()
    assert cli(argv) == 0

    assert manifest.read_bytes() == first_manifest
    assert b"checksum-report.json" not in first_manifest


def test_manifest_rejects_empty_inventory(tmp_path: Path) -> None:
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text("", encoding="utf-8")

    assert cli(["--root", str(tmp_path), "--verify", str(manifest), "--closed-set"]) == 2


def test_manifest_rejects_duplicate_paths(tmp_path: Path) -> None:
    data = b"x"
    (tmp_path / "x.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(_line("x.txt", data) * 2, encoding="utf-8")

    assert cli(["--root", str(tmp_path), "--verify", str(manifest), "--closed-set"]) == 2


def test_manifest_rejects_malformed_sha256(tmp_path: Path) -> None:
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text("not-a-hash  x.txt\n", encoding="utf-8")

    assert cli(["--root", str(tmp_path), "--verify", str(manifest), "--closed-set"]) == 2


def test_manifest_rejects_non_relative_path(tmp_path: Path) -> None:
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(f"{'0' * 64}  ../outside.txt\n", encoding="utf-8")

    assert cli(["--root", str(tmp_path), "--verify", str(manifest), "--closed-set"]) == 2
