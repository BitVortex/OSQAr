from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from tools import generate_checksums
from tools.osqar_cli import main as osqar_main


STALE_PASS = '{"schema":"osqar.checksums_report.v1","status":"PASS"}\n'


def test_checksum_mismatch_and_missing_return_failure_with_report(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "changed.txt").write_text("changed\n", encoding="utf-8")
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(
        "0" * 64 + "  changed.txt\n" + "1" * 64 + "  missing.txt\n",
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    report.write_text(STALE_PASS, encoding="utf-8")

    rc = generate_checksums.cli(
        ["--root", str(root), "--verify", str(manifest), "--json-report", str(report)]
    )

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert rc == 1
    assert payload["status"] == "FAIL"
    assert payload["missing"] == ["missing.txt"]
    assert payload["mismatched"] == ["changed.txt"]


def test_checksum_rejects_unsupported_algorithm(tmp_path: Path, capsys) -> None:
    root = tmp_path / "root"
    root.mkdir()
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text("", encoding="utf-8")

    rc = generate_checksums.cli(
        ["--root", str(root), "--algorithm", "not-a-hash", "--verify", str(manifest)]
    )

    assert rc == 2
    assert "unsupported algorithm" in capsys.readouterr().err.lower()


def test_checksum_rejects_missing_manifest(tmp_path: Path, capsys) -> None:
    root = tmp_path / "root"
    root.mkdir()

    rc = generate_checksums.cli(
        ["--root", str(root), "--verify", str(tmp_path / "missing")]
    )

    assert rc == 2
    assert "manifest not found" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("input_kind", ["missing", "malformed"])
def test_checksum_helper_invalidates_stale_pass_for_invalid_manifest(
    tmp_path: Path, input_kind: str
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    manifest = tmp_path / "SHA256SUMS"
    if input_kind == "malformed":
        manifest.write_text("not a manifest\n", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(STALE_PASS, encoding="utf-8")

    rc = generate_checksums.cli(
        ["--root", str(root), "--verify", str(manifest), "--json-report", str(report)]
    )

    assert rc == 2
    assert not report.exists()


def test_checksum_public_cli_invalidates_stale_pass_before_root_check(tmp_path: Path) -> None:
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text("not a manifest\n", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(STALE_PASS, encoding="utf-8")

    rc = osqar_main(
        [
            "checksum",
            "verify",
            "--root",
            str(tmp_path / "missing-root"),
            "--manifest",
            str(manifest),
            "--json-report",
            str(report),
        ]
    )

    assert rc == 2
    assert not report.exists()


def test_checksum_stops_before_verification_when_stale_report_cannot_be_invalidated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    data = b"payload\n"
    (root / "payload.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(
        f"{hashlib.sha256(data).hexdigest()}  payload.txt\n",
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    report.write_text(STALE_PASS, encoding="utf-8")
    original_unlink = Path.unlink
    verification_called = False

    def fail_report_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path == report:
            raise PermissionError("unlink denied")
        original_unlink(path, *args, **kwargs)

    def record_verification(*args: object, **kwargs: object):
        nonlocal verification_called
        verification_called = True
        return [], [], [], []

    monkeypatch.setattr(Path, "unlink", fail_report_unlink)
    monkeypatch.setattr(generate_checksums, "_verify_manifest", record_verification)

    assert generate_checksums.cli(
        ["--root", str(root), "--verify", str(manifest), "--json-report", str(report)]
    ) == 2
    assert capsys.readouterr().err == "ERROR: cannot invalidate JSON report: unlink denied\n"
    assert not verification_called
    assert report.read_text(encoding="utf-8") == STALE_PASS


def test_checksum_removes_partial_temporary_report_when_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    data = b"payload\n"
    (root / "payload.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(
        f"{hashlib.sha256(data).hexdigest()}  payload.txt\n",
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    report.write_text(STALE_PASS, encoding="utf-8")
    original_fdopen = os.fdopen

    class FailingWriter:
        def __init__(self, fd: int) -> None:
            self.stream = original_fdopen(fd, "w", encoding="utf-8")

        def __enter__(self):
            return self

        def write(self, _value: str) -> None:
            self.stream.write("{")
            self.stream.flush()
            raise OSError("write denied")

        def __exit__(self, *args: object) -> None:
            self.stream.close()

    monkeypatch.setattr(generate_checksums.os, "fdopen", lambda fd, *args, **kwargs: FailingWriter(fd))

    assert generate_checksums.cli(
        ["--root", str(root), "--verify", str(manifest), "--json-report", str(report)]
    ) == 2
    assert capsys.readouterr().err == "ERROR: cannot write JSON report: write denied\n"
    assert not report.exists()
    assert not list(tmp_path.glob(".report.json.*.tmp"))


def test_checksum_removes_temporary_report_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    data = b"payload\n"
    (root / "payload.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(
        f"{hashlib.sha256(data).hexdigest()}  payload.txt\n",
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    report.write_text(STALE_PASS, encoding="utf-8")

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("replace denied")

    monkeypatch.setattr(generate_checksums.os, "replace", fail_replace)

    assert generate_checksums.cli(
        ["--root", str(root), "--verify", str(manifest), "--json-report", str(report)]
    ) == 2
    assert capsys.readouterr().err == "ERROR: cannot write JSON report: replace denied\n"
    assert not report.exists()
    assert not list(tmp_path.glob(".report.json.*.tmp"))


def test_checksum_invalidates_complete_pass_temp_when_replace_and_unlink_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    data = b"payload\n"
    (root / "payload.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(f"{hashlib.sha256(data).hexdigest()}  payload.txt\n")
    report = tmp_path / "report.json"
    original_unlink = Path.unlink

    monkeypatch.setattr(
        generate_checksums.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace denied")),
    )

    def fail_temp_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path.name.startswith(".report.json."):
            raise PermissionError("unlink denied")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_temp_unlink)

    assert generate_checksums.cli(
        ["--root", str(root), "--verify", str(manifest), "--json-report", str(report)]
    ) == 2
    assert capsys.readouterr().err == (
        "ERROR: cannot write JSON report: replace denied; "
        "temporary cleanup failed: unlink denied\n"
    )
    [temporary] = list(tmp_path.glob(".report.json.*.tmp"))
    with pytest.raises(json.JSONDecodeError):
        json.loads(temporary.read_text(encoding="utf-8"))


@pytest.mark.parametrize("alias_kind", ["lexical", "symlink"])
def test_checksum_verify_rejects_report_manifest_collision_before_invalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    alias_kind: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    data = b"payload\n"
    (root / "payload.txt").write_bytes(data)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(f"{hashlib.sha256(data).hexdigest()}  payload.txt\n")
    before = manifest.read_bytes()
    report = manifest
    if alias_kind == "symlink":
        report = tmp_path / "report.json"
        report.symlink_to(manifest)
    verification_called = False

    def record_verification(*_args: object, **_kwargs: object):
        nonlocal verification_called
        verification_called = True
        return [], [], [], []

    monkeypatch.setattr(generate_checksums, "_verify_manifest", record_verification)

    assert generate_checksums.cli(
        ["--root", str(root), "--verify", str(manifest), "--json-report", str(report)]
    ) == 2
    assert capsys.readouterr().err == (
        "ERROR: JSON report resolves to the checksum manifest\n"
    )
    assert not verification_called
    assert manifest.read_bytes() == before
    if alias_kind == "symlink":
        assert report.is_symlink()


@pytest.mark.parametrize("alias_kind", ["lexical", "symlink"])
def test_checksum_verify_rejects_report_artifact_collision_before_invalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    alias_kind: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    artifact = root / "payload.txt"
    artifact.write_bytes(b"payload\n")
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(
        f"{hashlib.sha256(artifact.read_bytes()).hexdigest()}  payload.txt\n"
    )
    before = artifact.read_bytes()
    report = artifact
    if alias_kind == "symlink":
        report = tmp_path / "report.json"
        report.symlink_to(artifact)
    verification_called = False

    def record_verification(*_args: object, **_kwargs: object):
        nonlocal verification_called
        verification_called = True
        return [], [], [], []

    monkeypatch.setattr(generate_checksums, "_verify_manifest", record_verification)

    assert generate_checksums.cli(
        ["--root", str(root), "--verify", str(manifest), "--json-report", str(report)]
    ) == 2
    assert capsys.readouterr().err == (
        "ERROR: JSON report resolves to manifest-declared artifact: payload.txt\n"
    )
    assert not verification_called
    assert artifact.read_bytes() == before
    if alias_kind == "symlink":
        assert report.is_symlink()


@pytest.mark.parametrize("alias_kind", ["lexical", "symlink"])
def test_checksum_generate_rejects_report_manifest_collision_before_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    alias_kind: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "payload.txt").write_text("payload\n", encoding="utf-8")
    output = tmp_path / "SHA256SUMS"
    output.write_text("existing payload\n", encoding="utf-8")
    before = output.read_bytes()
    report = output
    if alias_kind == "symlink":
        report = tmp_path / "report.json"
        report.symlink_to(output)
    producer_called = False

    def record_producer(*_args: object, **_kwargs: object):
        nonlocal producer_called
        producer_called = True
        return []

    monkeypatch.setattr(generate_checksums, "_write_manifest", record_producer)

    assert generate_checksums.cli(
        ["--root", str(root), "--output", str(output), "--json-report", str(report)]
    ) == 2
    assert capsys.readouterr().err == (
        "ERROR: JSON report and manifest output resolve to the same path\n"
    )
    assert not producer_called
    assert output.read_bytes() == before
    if alias_kind == "symlink":
        assert report.is_symlink()


def test_checksum_generate_rejects_symlink_output_without_modifying_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    payload = root / "payload.txt"
    payload.write_bytes(b"VALID EVIDENCE\n")
    output = root / "SHA256SUMS"
    output.symlink_to(payload.name)

    rc = osqar_main(
        ["checksum", "generate", "--root", str(root), "--output", str(output)]
    )

    assert rc == 2
    assert "output must not be a symlink" in capsys.readouterr().err
    assert payload.read_bytes() == b"VALID EVIDENCE\n"
    assert output.is_symlink()


def test_checksum_generation_rejects_symlinked_root_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    external = tmp_path / "external.bin"
    external.write_bytes(b"external\n")
    (root / "payload.bin").symlink_to(external)
    output = tmp_path / "SHA256SUMS"

    rc = osqar_main(
        ["checksum", "generate", "--root", str(root), "--output", str(output)]
    )

    assert rc == 2
    assert "symlinked artifact is not permitted" in capsys.readouterr().err.lower()
    assert not output.exists()
    assert external.read_bytes() == b"external\n"


def test_checksum_closed_set_rejects_declared_symlink_outside_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    external = tmp_path / "external.bin"
    external.write_bytes(b"external\n")
    (root / "payload.bin").symlink_to(external)
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(
        f"{hashlib.sha256(external.read_bytes()).hexdigest()}  payload.bin\n",
        encoding="utf-8",
    )

    rc = osqar_main(
        [
            "checksum",
            "verify",
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--closed-set",
        ]
    )

    assert rc == 2
    assert "symlinked artifact is not permitted" in capsys.readouterr().err.lower()


def test_checksum_generate_rejects_hardlinked_output_without_modifying_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    payload = root / "payload.txt"
    payload.write_bytes(b"VALID EVIDENCE\n")
    output = root / "SHA256SUMS"
    os.link(payload, output)

    rc = osqar_main(
        ["checksum", "generate", "--root", str(root), "--output", str(output)]
    )

    assert rc == 2
    assert "single-link regular file" in capsys.readouterr().err
    assert payload.read_bytes() == b"VALID EVIDENCE\n"
    assert output.samefile(payload)


def test_checksum_generation_write_failure_preserves_prior_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "payload.txt").write_text("payload\n", encoding="utf-8")
    output = tmp_path / "SHA256SUMS"
    prior = b"0" * 64 + b"  prior.txt\n"
    output.write_bytes(prior)
    original_fdopen = os.fdopen

    class FailingWriter:
        def __init__(self, descriptor: int) -> None:
            self.stream = original_fdopen(descriptor, "w", encoding="utf-8")

        def write(self, _content: str) -> None:
            self.stream.write("PARTIAL")
            self.stream.flush()
            raise OSError("injected write failure")

        def close(self) -> None:
            self.stream.close()

    monkeypatch.setattr(
        generate_checksums.os,
        "fdopen",
        lambda descriptor, *_args, **_kwargs: FailingWriter(descriptor),
    )

    rc = generate_checksums.cli(["--root", str(root), "--output", str(output)])

    assert rc == 2
    assert "injected write failure" in capsys.readouterr().err
    assert output.read_bytes() == prior
    assert not list(tmp_path.glob(".SHA256SUMS.*.tmp"))


def test_checksum_generation_replace_failure_preserves_prior_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "payload.txt").write_text("payload\n", encoding="utf-8")
    output = tmp_path / "SHA256SUMS"
    prior = b"0" * 64 + b"  prior.txt\n"
    output.write_bytes(prior)
    monkeypatch.setattr(
        generate_checksums.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace denied")),
    )

    rc = generate_checksums.cli(["--root", str(root), "--output", str(output)])

    assert rc == 2
    assert "replace denied" in capsys.readouterr().err
    assert output.read_bytes() == prior
    assert not list(tmp_path.glob(".SHA256SUMS.*.tmp"))


def test_checksum_generation_close_failure_preserves_prior_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "payload.txt").write_text("payload\n", encoding="utf-8")
    output = tmp_path / "SHA256SUMS"
    prior = b"0" * 64 + b"  prior.txt\n"
    output.write_bytes(prior)
    original_fdopen = os.fdopen

    class CloseFailingWriter:
        def __init__(self, descriptor: int) -> None:
            self.stream = original_fdopen(descriptor, "w", encoding="utf-8")

        def __getattr__(self, name: str):
            return getattr(self.stream, name)

        def close(self) -> None:
            self.stream.close()
            raise OSError("close denied")

    monkeypatch.setattr(
        generate_checksums.os,
        "fdopen",
        lambda descriptor, *_args, **_kwargs: CloseFailingWriter(descriptor),
    )

    rc = generate_checksums.cli(["--root", str(root), "--output", str(output)])

    assert rc == 2
    assert "close denied" in capsys.readouterr().err
    assert output.read_bytes() == prior
    assert not list(tmp_path.glob(".SHA256SUMS.*.tmp"))


def test_checksum_generate_rejects_json_report_over_existing_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    payload = root / "evidence.bin"
    payload.write_bytes(b"IRREPLACEABLE EVIDENCE")
    manifest = root / "SHA256SUMS"

    rc = generate_checksums.cli(
        [
            "--root",
            str(root),
            "--output",
            str(manifest),
            "--json-report",
            str(payload),
        ]
    )

    assert rc == 2
    assert "aliases existing root artifact" in capsys.readouterr().err
    assert payload.read_bytes() == b"IRREPLACEABLE EVIDENCE"
    assert not manifest.exists()


def test_checksum_unsupported_algorithm_does_not_invalidate_aliased_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    payload = root / "evidence.bin"
    payload.write_bytes(b"IRREPLACEABLE EVIDENCE")
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text("0" * 64 + "  evidence.bin\n", encoding="utf-8")

    rc = generate_checksums.cli(
        [
            "--root",
            str(root),
            "--algorithm",
            "not-a-hash",
            "--verify",
            str(manifest),
            "--json-report",
            str(payload),
        ]
    )

    assert rc == 2
    assert "unsupported algorithm" in capsys.readouterr().err
    assert payload.read_bytes() == b"IRREPLACEABLE EVIDENCE"


@pytest.mark.parametrize(
    "algorithm", ["definitely-not-a-hash", "shake_128", "shake_256"]
)
def test_checksum_unsupported_algorithm_preserves_declared_prior_report_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], algorithm: str
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    payload = root / "payload.json"
    manifest = tmp_path / "SHA256SUMS"
    original = json.dumps(
        {
            "schema": "osqar.checksums_report.v1",
            "root": str(root.resolve()),
            "manifest": str(manifest.resolve()),
            "status": "PASS",
        }
    ).encode()
    payload.write_bytes(original)
    manifest.write_text("0" * 64 + "  payload.json\n", encoding="utf-8")

    rc = generate_checksums.cli(
        [
            "--root",
            str(root),
            "--algorithm",
            algorithm,
            "--verify",
            str(manifest),
            "--json-report",
            str(payload),
        ]
    )

    assert rc == 2
    assert "unsupported algorithm" in capsys.readouterr().err
    assert payload.read_bytes() == original


def test_checksum_generate_rejects_empty_inventory_without_publishing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    manifest = tmp_path / "SHA256SUMS"

    rc = generate_checksums.cli(["--root", str(root), "--output", str(manifest)])

    assert rc == 2
    assert "no entries" in capsys.readouterr().err
    assert not manifest.exists()
