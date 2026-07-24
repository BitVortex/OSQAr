from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import pytest

from tools.release_manifest import generate_release_manifest, render_release_description, verify_release_manifest

REVISION = "a" * 40

def test_release_manifest_schema_is_packaged() -> None:
    schema = resources.files("osqar_data").joinpath("schemas/release-manifest-v1.schema.json")
    assert schema.is_file()
    payload = json.loads(schema.read_text(encoding="utf-8"))
    assert payload["$id"] == "https://osqar.dev/schemas/release-manifest-v1.schema.json"


def test_release_manifest_captures_provenance_and_verifies_closed_set(tmp_path: Path) -> None:
    (tmp_path / "docs.html").write_text("documentation\n", encoding="utf-8")
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"

    manifest = generate_release_manifest(
        root=tmp_path,
        output=output,
        source_revision=REVISION,
        release_version="v0.10.0",
        producer_command="osqar shipment prepare",
        tool_version="0.9.0",
        exclusions=["*.tmp"],
    )
    result = verify_release_manifest(root=tmp_path, manifest_path=output)

    assert manifest["schema"] == "osqar.release-manifest.v1"
    assert manifest["source_revision"] == REVISION
    assert manifest["producer"]["command"] == "osqar shipment prepare"
    assert manifest["artifacts"][0]["path"] == "docs.html"
    assert result.status == "PASS"


def test_release_manifest_rejects_unexpected_file(tmp_path: Path) -> None:
    (tmp_path / "declared.txt").write_text("declared\n", encoding="utf-8")
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"
    generate_release_manifest(
        root=tmp_path,
        output=output,
        source_revision=REVISION,
        release_version="v0.10.0",
        producer_command="build",
        tool_version="0.9.0",
        exclusions=[],
    )
    (tmp_path / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")

    result = verify_release_manifest(root=tmp_path, manifest_path=output)

    assert result.status == "FAIL"
    assert result.unexpected == ("unexpected.txt",)


def test_release_manifest_rejects_empty_declared_artifact(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"

    with pytest.raises(ValueError, match="artifact is empty"):
        generate_release_manifest(
            root=tmp_path,
            output=output,
            source_revision=REVISION,
        release_version="v0.10.0",
            producer_command="build",
            tool_version="0.9.0",
            exclusions=[],
        )

    assert not output.exists()


def test_release_manifest_rejects_duplicate_record(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"
    generate_release_manifest(
        root=tmp_path,
        output=output,
        source_revision=REVISION,
        release_version="v0.10.0",
        producer_command="build",
        tool_version="0.9.0",
        exclusions=[],
    )
    payload = json.loads(output.read_text())
    payload["artifacts"].append(dict(payload["artifacts"][0]))
    output.write_text(json.dumps(payload), encoding="utf-8")

    result = verify_release_manifest(root=tmp_path, manifest_path=output)

    assert result.status == "ERROR"
    assert any("duplicate artifact path" in error for error in result.errors)


def test_release_manifest_rejects_empty_shipment(tmp_path: Path) -> None:
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"

    try:
        generate_release_manifest(
            root=tmp_path,
            output=output,
            source_revision=REVISION,
        release_version="v0.10.0",
            producer_command="build",
            tool_version="0.9.0",
            exclusions=[],
        )
    except ValueError as exc:
        assert "no artifacts" in str(exc).lower()
    else:
        raise AssertionError("empty qualification shipment was accepted")


def test_release_manifest_deduplicates_exclusions(tmp_path: Path) -> None:
    (tmp_path / "asset.zip").write_text("asset", encoding="utf-8")
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"

    manifest = generate_release_manifest(
        root=tmp_path,
        output=output,
        source_revision=REVISION,
        release_version="v0.10.0",
        producer_command="build",
        tool_version="0.9.0",
        exclusions=["*.tmp", "*.tmp"],
    )

    assert manifest["exclusions"] == ["*.tmp"]


def test_release_description_is_derived_from_manifest(tmp_path: Path) -> None:
    (tmp_path / "asset.zip").write_text("asset", encoding="utf-8")
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"
    manifest = generate_release_manifest(
        root=tmp_path,
        output=output,
        source_revision=REVISION,
        release_version="v0.10.0",
        producer_command="build",
        tool_version="0.9.0",
        exclusions=[],
    )

    description = render_release_description(manifest)

    assert REVISION in description
    assert "asset.zip" in description
    assert "osqar.release-manifest.v1" in description


def test_runtime_rejects_schema_invalid_properties_and_types(tmp_path: Path) -> None:
    artifact = tmp_path / "asset.zip"
    artifact.write_text("asset", encoding="utf-8")
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"
    original = generate_release_manifest(
        root=tmp_path,
        output=output,
        source_revision=REVISION,
        release_version="v0.10.0",
        producer_command="build",
        tool_version="0.9.0",
        exclusions=[],
    )

    invalid_payloads = []
    payload = json.loads(json.dumps(original))
    payload["unknown"] = True
    invalid_payloads.append(payload)
    payload = json.loads(json.dumps(original))
    payload["producer"]["unknown"] = True
    invalid_payloads.append(payload)
    payload = json.loads(json.dumps(original))
    payload["artifacts"][0]["unknown"] = True
    invalid_payloads.append(payload)
    payload = json.loads(json.dumps(original))
    payload["source_revision"] = 123
    invalid_payloads.append(payload)

    for payload in invalid_payloads:
        output.write_text(json.dumps(payload), encoding="utf-8")
        result = verify_release_manifest(root=tmp_path, manifest_path=output)
        assert result.status == "ERROR"
        assert any("schema validation" in error for error in result.errors)


def test_release_manifest_rejects_symlink_artifacts(tmp_path: Path) -> None:
    external = tmp_path.parent / "external-release-artifact.txt"
    external.write_text("external", encoding="utf-8")
    link = tmp_path / "escape"
    link.symlink_to(external)
    output = tmp_path / "OSQAR-RELEASE-MANIFEST.json"

    with pytest.raises(ValueError, match="symbolic links"):
        generate_release_manifest(
            root=tmp_path,
            output=output,
            source_revision=REVISION,
        release_version="v0.10.0",
            producer_command="build",
            tool_version="0.9.0",
            exclusions=[],
        )


@pytest.mark.parametrize("bad_path", ["", "/absolute", "../escape", "a/../b", " a", "a\\b", "a//b"])
def test_release_manifest_rejects_noncanonical_paths(tmp_path: Path, bad_path: str) -> None:
    (tmp_path / "asset").write_text("asset", encoding="utf-8")
    output = tmp_path / "manifest.json"
    payload = generate_release_manifest(
        root=tmp_path, output=output, release_version="v1", source_revision=REVISION,
        producer_command="build", tool_version="1", exclusions=[],
    )
    payload["artifacts"][0]["path"] = bad_path
    output.write_text(json.dumps(payload), encoding="utf-8")

    result = verify_release_manifest(root=tmp_path, manifest_path=output)

    assert result.status == "ERROR"


def test_release_manifest_rejects_raw_paths_that_would_alias(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").write_text("asset", encoding="utf-8")
    output = tmp_path / "manifest.json"
    payload = generate_release_manifest(
        root=tmp_path, output=output, release_version="v1", source_revision=REVISION,
        producer_command="build", tool_version="1", exclusions=[],
    )
    duplicate = dict(payload["artifacts"][0])
    duplicate["path"] = "a//b"
    payload["artifacts"].append(duplicate)
    output.write_text(json.dumps(payload), encoding="utf-8")

    result = verify_release_manifest(root=tmp_path, manifest_path=output)

    assert result.status == "ERROR"


def test_release_manifest_identity_can_be_pinned(tmp_path: Path) -> None:
    (tmp_path / "asset").write_text("asset", encoding="utf-8")
    output = tmp_path / "manifest.json"
    generate_release_manifest(
        root=tmp_path, output=output, release_version="v1", source_revision=REVISION,
        producer_command="build", tool_version="1", exclusions=[],
    )

    result = verify_release_manifest(
        root=tmp_path, manifest_path=output,
        expected_release_version="v2", expected_source_revision="b" * 40,
    )

    assert result.status == "ERROR"
    assert any("release version mismatch" in error for error in result.errors)
    assert any("source revision mismatch" in error for error in result.errors)


def test_generation_refuses_to_clobber_payload_alias(tmp_path: Path) -> None:
    output = tmp_path / "manifest.json"
    output.write_text("payload", encoding="utf-8")

    with pytest.raises(ValueError, match="payload alias"):
        generate_release_manifest(
            root=tmp_path, output=output, release_version="v1", source_revision=REVISION,
            producer_command="build", tool_version="1", exclusions=[],
        )

    assert output.read_text(encoding="utf-8") == "payload"


@pytest.mark.parametrize(
    ("release_version", "source_revision"),
    [
        ("not-a-release-version", REVISION),
        ("1.2.3", REVISION),
        ("v1.2.3", "abc"),
        ("v1.2.3", "g" * 40),
        ("v1.2.3", "a" * 39),
    ],
)
def test_release_manifest_rejects_invalid_release_identity(
    tmp_path: Path, release_version: str, source_revision: str
) -> None:
    (tmp_path / "asset").write_text("asset", encoding="utf-8")

    with pytest.raises(ValueError, match="release_version|source_revision"):
        generate_release_manifest(
            root=tmp_path,
            output=tmp_path / "manifest.json",
            release_version=release_version,
            source_revision=source_revision,
            producer_command="build",
            tool_version="1",
            exclusions=[],
        )


def test_optional_missing_artifact_is_non_failing_but_present_optional_is_verified(
    tmp_path: Path,
) -> None:
    present = tmp_path / "present"
    present.write_text("present", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    payload = generate_release_manifest(
        root=tmp_path,
        output=manifest_path,
        release_version="v1.2.3",
        source_revision=REVISION,
        producer_command="build",
        tool_version="1",
        exclusions=[],
    )
    optional = dict(payload["artifacts"][0])
    optional["path"] = "optional"
    optional["required"] = False
    payload["artifacts"].append(optional)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = verify_release_manifest(root=tmp_path, manifest_path=manifest_path)
    assert result.status == "PASS"
    assert result.optional_missing == ("optional",)

    (tmp_path / "optional").write_text("wrong", encoding="utf-8")
    result = verify_release_manifest(root=tmp_path, manifest_path=manifest_path)
    assert result.status == "FAIL"
    assert result.mismatched == ("optional",)
