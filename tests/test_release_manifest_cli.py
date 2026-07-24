from __future__ import annotations

import json
import os
from pathlib import Path

from tools.osqar_cli import main

REVISION = "a" * 40

def test_release_manifest_cli_generates_description_and_verifies(tmp_path: Path) -> None:
    (tmp_path / "shipment.zip").write_text("zip bytes\n", encoding="utf-8")
    manifest = tmp_path / "OSQAR-RELEASE-MANIFEST.json"
    description = tmp_path / "release.md"

    rc = main(
        [
            "release-manifest",
            "generate",
            "--root",
            str(tmp_path),
            "--output",
            str(manifest),
            "--source-revision",
            REVISION,
            "--release-version",
            "v0.10.0",
            "--producer-command",
            "osqar shipment prepare",
            "--tool-version",
            "0.9.0",
            "--description-output",
            str(description),
        ]
    )

    assert rc == 0
    assert "shipment.zip" in description.read_text()
    assert main(["release-manifest", "verify", "--root", str(tmp_path), "--manifest", str(manifest)]) == 0
    (tmp_path / "extra.txt").write_text("extra\n", encoding="utf-8")
    report = tmp_path.parent / "release-verification.json"
    assert main(
        [
            "release-manifest",
            "verify",
            "--root",
            str(tmp_path),
            "--manifest",
            str(manifest),
            "--report-json",
            str(report),
        ]
    ) == 1
    assert json.loads(report.read_text())["unexpected"] == ["extra.txt"]


def test_verify_rejects_report_inside_shipment_without_stale_pass(tmp_path: Path) -> None:
    (tmp_path / "asset").write_text("asset", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    assert main([
        "release-manifest", "generate", "--root", str(tmp_path), "--output", str(manifest),
        "--release-version", "v1", "--source-revision", REVISION,
        "--producer-command", "build", "--tool-version", "1",
    ]) == 0
    report = tmp_path / "report.json"

    assert main([
        "release-manifest", "verify", "--root", str(tmp_path), "--manifest", str(manifest),
        "--report-json", str(report),
    ]) == 2
    assert not report.exists()


def test_generate_refusal_preserves_output_payload_bytes(tmp_path: Path) -> None:
    output = tmp_path / "payload.bin"
    sentinel = b"\x00existing payload\xff"
    output.write_bytes(sentinel)

    assert main([
        "release-manifest", "generate", "--root", str(tmp_path), "--output", str(output),
        "--release-version", "v1", "--source-revision", REVISION,
        "--producer-command", "build", "--tool-version", "1",
    ]) == 2
    assert output.read_bytes() == sentinel


def test_verify_rejects_external_hardlink_report_alias_to_payload_without_modification(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "asset"
    sentinel = b"immutable payload"
    payload.write_bytes(sentinel)
    manifest = tmp_path / "manifest.json"
    assert main([
        "release-manifest", "generate", "--root", str(tmp_path), "--output", str(manifest),
        "--release-version", "v1", "--source-revision", REVISION,
        "--producer-command", "build", "--tool-version", "1",
    ]) == 0
    report = tmp_path.parent / f"{tmp_path.name}-report.json"
    os.link(payload, report)

    assert main([
        "release-manifest", "verify", "--root", str(tmp_path), "--manifest", str(manifest),
        "--report-json", str(report),
    ]) == 2
    assert payload.read_bytes() == sentinel
    assert report.read_bytes() == sentinel


def test_verify_rejects_external_symlink_report_alias_without_modification(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "asset"
    sentinel = b"immutable payload"
    payload.write_bytes(sentinel)
    manifest = tmp_path / "manifest.json"
    assert main([
        "release-manifest", "generate", "--root", str(tmp_path), "--output", str(manifest),
        "--release-version", "v1", "--source-revision", REVISION,
        "--producer-command", "build", "--tool-version", "1",
    ]) == 0
    report = tmp_path.parent / f"{tmp_path.name}-symlink-report.json"
    report.symlink_to(payload)

    assert main([
        "release-manifest", "verify", "--root", str(tmp_path), "--manifest", str(manifest),
        "--report-json", str(report),
    ]) == 2
    assert payload.read_bytes() == sentinel


def test_verify_rejects_hardlink_report_alias_to_manifest_without_modification(
    tmp_path: Path,
) -> None:
    (tmp_path / "asset").write_text("asset", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    assert main([
        "release-manifest", "generate", "--root", str(tmp_path), "--output", str(manifest),
        "--release-version", "v1", "--source-revision", REVISION,
        "--producer-command", "build", "--tool-version", "1",
    ]) == 0
    sentinel = manifest.read_bytes()
    report = tmp_path.parent / f"{tmp_path.name}-manifest-report.json"
    os.link(manifest, report)

    assert main([
        "release-manifest", "verify", "--root", str(tmp_path), "--manifest", str(manifest),
        "--report-json", str(report),
    ]) == 2
    assert manifest.read_bytes() == sentinel
