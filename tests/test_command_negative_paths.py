from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tools import osqar_cmd_sign
from tools.osqar_cli import main


def _project_with_needs(root: Path, name: str, payload: object) -> Path:
    project = root / name
    project.mkdir()
    (project / "conf.py").write_text("project = 'fixture'\n", encoding="utf-8")
    (project / "index.rst").write_text("Fixture\n=======\n", encoding="utf-8")
    (project / "needs.json").write_text(json.dumps(payload), encoding="utf-8")
    return project


def test_workspace_combine_rejects_malformed_project_needs(
    tmp_path: Path, capsys
) -> None:
    project = _project_with_needs(tmp_path, "broken", {})
    (project / "needs.json").write_text("{ malformed", encoding="utf-8")

    rc = main(
        [
            "workspace",
            "combine",
            "--root",
            str(tmp_path),
            "--output",
            str(tmp_path / "combined.json"),
        ]
    )

    assert rc == 2
    assert "failed to parse" in capsys.readouterr().err.lower()
    assert not (tmp_path / "combined.json").exists()


def test_workspace_combine_rejects_duplicate_need_ids(
    tmp_path: Path, capsys
) -> None:
    _project_with_needs(
        tmp_path,
        "duplicate",
        {"needs": [{"id": "REQ_DUP"}, {"id": "REQ_DUP"}]},
    )

    rc = main(
        [
            "workspace",
            "combine",
            "--root",
            str(tmp_path),
            "--output",
            str(tmp_path / "combined.json"),
        ]
    )

    assert rc == 2
    assert "duplicate need id: REQ_DUP" in capsys.readouterr().err
    assert not (tmp_path / "combined.json").exists()


def _write_baseline(project: Path, tag: str, manifest: object, needs: object) -> None:
    baseline = project / ".osqar-baselines" / tag
    baseline.mkdir(parents=True)
    (baseline / "baseline-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (baseline / "needs.json").write_text(json.dumps(needs), encoding="utf-8")


def test_baseline_diff_rejects_non_object_manifest(tmp_path: Path, capsys) -> None:
    _write_baseline(tmp_path, "old", [], {"needs": [{"id": "REQ_OLD"}]})
    _write_baseline(
        tmp_path,
        "new",
        {
            "schema": "osqar.baseline_manifest.v1",
            "tag": "new",
            "needs_file": "needs.json",
            "needs_count": 1,
        },
        {"needs": [{"id": "REQ_NEW"}]},
    )

    rc = main(["baseline", "diff", "old", "new", "--project", str(tmp_path)])

    assert rc == 2
    assert "baseline 'old' not found or invalid" in capsys.readouterr().err


def test_sign_create_rejects_success_without_signature(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "SHA256SUMS"
    signature = tmp_path / "SHA256SUMS.sig"
    manifest.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )

    rc = main(
        [
            "sign",
            "create",
            "--manifest",
            str(manifest),
            "--output",
            str(signature),
        ]
    )

    assert rc == 1
    assert "did not create signature" in capsys.readouterr().err.lower()
    assert not signature.exists()


def test_sign_create_removes_partial_signature_after_producer_failure(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "SHA256SUMS"
    signature = tmp_path / "SHA256SUMS.sig"
    manifest.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")

    def fail_after_partial_output(argv, **_kwargs):
        output = Path(argv[argv.index("--output") + 1])
        output.write_bytes(b"partial signature")
        return subprocess.CompletedProcess(argv, 7, "", "producer failed")

    monkeypatch.setattr(subprocess, "run", fail_after_partial_output)

    rc = main(
        [
            "sign",
            "create",
            "--manifest",
            str(manifest),
            "--output",
            str(signature),
        ]
    )

    assert rc == 1
    assert "signing failed (rc=7)" in capsys.readouterr().err
    assert not signature.exists()


def test_sign_create_cleanup_failure_does_not_mask_producer_failure(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "SHA256SUMS"
    signature = tmp_path / "SHA256SUMS.sig"
    manifest.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")

    def fail_after_partial_output(argv, **_kwargs):
        output = Path(argv[argv.index("--output") + 1])
        output.write_bytes(b"partial signature")
        return subprocess.CompletedProcess(argv, 7, "", "producer failed")

    original_unlink = Path.unlink

    def deny_cleanup(path: Path, *args, **kwargs):
        if path == signature and path.exists():
            raise PermissionError("cleanup denied")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_after_partial_output)
    monkeypatch.setattr(Path, "unlink", deny_cleanup)

    rc = main(
        [
            "sign",
            "create",
            "--manifest",
            str(manifest),
            "--output",
            str(signature),
        ]
    )

    assert rc == 1
    error = capsys.readouterr().err
    assert "signing failed (rc=7)" in error
    assert "failed to remove signature output: cleanup denied" in error
    assert signature.read_bytes() == b"partial signature"


def test_sign_create_rejects_armored_output_equal_to_manifest_before_producer(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "manifest.asc"
    manifest.write_text("payload", encoding="utf-8")
    producer_called = False
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")

    def record_producer(*_args, **_kwargs):
        nonlocal producer_called
        producer_called = True
        raise AssertionError("producer must not run")

    monkeypatch.setattr(subprocess, "run", record_producer)

    rc = main(
        [
            "sign",
            "create",
            "--manifest",
            str(manifest),
            "--output",
            str(manifest),
            "--armor",
        ]
    )

    assert rc == 2
    assert capsys.readouterr().err == "ERROR: signature output aliases manifest\n"
    assert manifest.read_text(encoding="utf-8") == "payload"
    assert not producer_called


def test_sign_create_rejects_resolved_symlink_alias_before_producer(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "manifest"
    manifest.write_text("payload", encoding="utf-8")
    output_alias = tmp_path / "signature.asc"
    output_alias.symlink_to(manifest)
    producer_called = False
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")

    def record_producer(*_args, **_kwargs):
        nonlocal producer_called
        producer_called = True
        raise AssertionError("producer must not run")

    monkeypatch.setattr(subprocess, "run", record_producer)

    rc = main(
        [
            "sign",
            "create",
            "--manifest",
            str(manifest),
            "--output",
            str(output_alias),
            "--armor",
        ]
    )

    assert rc == 2
    assert capsys.readouterr().err == "ERROR: signature output aliases manifest\n"
    assert manifest.read_text(encoding="utf-8") == "payload"
    assert output_alias.is_symlink()
    assert not producer_called


def test_sign_create_cleans_partial_output_when_producer_raises_oserror(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "SHA256SUMS"
    signature = tmp_path / "SHA256SUMS.sig"
    manifest.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")

    def deny_after_partial_output(argv, **_kwargs):
        output = Path(argv[argv.index("--output") + 1])
        output.write_bytes(b"partial signature")
        raise PermissionError("execution denied")

    monkeypatch.setattr(subprocess, "run", deny_after_partial_output)

    rc = main(
        [
            "sign",
            "create",
            "--manifest",
            str(manifest),
            "--output",
            str(signature),
        ]
    )

    assert rc == 2
    assert capsys.readouterr().err == (
        "ERROR: cannot execute signing tool fake-gpg: execution denied\n"
    )
    assert not signature.exists()


def test_sign_create_cleans_output_when_postcondition_stat_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "SHA256SUMS"
    signature = tmp_path / "SHA256SUMS.sig"
    manifest.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")

    def produce_signature(argv, **_kwargs):
        output = Path(argv[argv.index("--output") + 1])
        output.write_bytes(b"signature")
        return subprocess.CompletedProcess(argv, 0, "", "")

    original_lstat = Path.lstat

    def deny_signature_lstat(path: Path, *args, **kwargs):
        if path == signature:
            raise PermissionError("postcondition stat denied")
        return original_lstat(path, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", produce_signature)
    monkeypatch.setattr(Path, "lstat", deny_signature_lstat)

    rc = main(
        [
            "sign",
            "create",
            "--manifest",
            str(manifest),
            "--output",
            str(signature),
        ]
    )

    assert rc == 2
    assert (
        "cannot validate signature output: postcondition stat denied"
        in capsys.readouterr().err
    )
    assert not signature.exists()


def test_sign_create_rejects_producer_created_alias_artifacts(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: "fake-gpg")

    for alias_kind in ("symlink", "hardlink", "directory"):
        case = tmp_path / alias_kind
        case.mkdir()
        manifest = case / "SHA256SUMS"
        signature = case / "SHA256SUMS.sig"
        external = case / "external.bin"
        manifest.write_text("payload", encoding="utf-8")
        external.write_bytes(b"NOT A SIGNATURE")

        def produce_alias(argv, **_kwargs):
            output = Path(argv[argv.index("--output") + 1])
            if alias_kind == "symlink":
                output.symlink_to(external)
            elif alias_kind == "hardlink":
                os.link(external, output)
            else:
                output.mkdir()
            return subprocess.CompletedProcess(argv, 0, "", "")

        monkeypatch.setattr(subprocess, "run", produce_alias)

        rc = main(
            [
                "sign",
                "create",
                "--manifest",
                str(manifest),
                "--output",
                str(signature),
            ]
        )

        assert rc == 1
        assert "expected a nonempty single-link regular file" in capsys.readouterr().err
        assert not signature.exists()
        assert external.read_bytes() == b"NOT A SIGNATURE"


def test_baseline_diff_rejects_stale_manifest_count(tmp_path: Path, capsys) -> None:
    for tag in ("old", "new"):
        _write_baseline(
            tmp_path,
            tag,
            {
                "schema": "osqar.baseline_manifest.v1",
                "tag": tag,
                "needs_file": "needs.json",
                "needs_count": 99 if tag == "old" else 1,
            },
            {"needs": [{"id": f"REQ_{tag.upper()}"}]},
        )

    rc = main(["baseline", "diff", "old", "new", "--project", str(tmp_path)])

    assert rc == 2
    assert "baseline 'old' not found or invalid" in capsys.readouterr().err
