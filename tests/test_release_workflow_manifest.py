from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "release.yml"


def test_release_workflow_closes_final_downloaded_payload_before_publication() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    inventory = jobs["release-inventory"]
    assert set(inventory["needs"]) >= {
        "python-distributions", "framework-bundle", "example-workspace"
    }
    steps = inventory["steps"]
    run = "\n".join(str(step.get("run", "")) for step in steps)
    assert "actions/download-artifact@v4" in {
        step.get("uses") for step in steps if step.get("uses")
    }
    assert "release-manifest generate" in run
    assert "release-manifest verify" in run
    assert "checksum verify" in run
    assert "--closed-set" in run
    assert '--release-version "${GITHUB_REF_NAME}"' in run
    assert '--source-revision "${GITHUB_SHA}"' in run
    final_generate = run.index("--output OSQAR-RELEASE-MANIFEST.json")
    assert run.index("cosign sign-blob") < final_generate
    assert run.index("release-attestation.intoto.jsonl") < final_generate
    assert any(step.get("uses") == "actions/attest-build-provenance@v2" for step in steps)
    assert "release-inventory" in jobs["publish"]["needs"]
    assert "release-inventory" in jobs["pypi-publish"]["needs"]


def test_release_upload_includes_payload_integrity_and_provenance_assets() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    publish = workflow["jobs"]["publish"]
    release = next(
        step for step in publish["steps"]
        if step.get("uses") == "softprops/action-gh-release@v2"
    )
    files = str(release["with"]["files"])
    for name in (
        "*.whl",
        "*.tar.gz",
        "SHA256SUMS",
        "OSQAR-RELEASE-MANIFEST.json",
        "OSQAR-RELEASE-PREMANIFEST.sigstore.json",
        "release-attestation.intoto.jsonl",
    ):
        assert name in files
    assert release["with"]["body_path"] == "dist/RELEASE-NOTES.md"
    assert "generate_release_notes" not in release["with"]
    assert "RELEASE-NOTES.md" not in files
    publish_run = "\n".join(str(step.get("run", "")) for step in publish["steps"])
    assert "render_release_description" in publish_run
    assert "dist/OSQAR-RELEASE-MANIFEST.json" in publish_run


def test_every_non_manifest_release_upload_is_in_checksum_and_final_inventory() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    inventory_steps = jobs["release-inventory"]["steps"]
    inventory_run = "\n".join(str(step.get("run", "")) for step in inventory_steps)
    publish = jobs["publish"]
    release = next(
        step for step in publish["steps"]
        if step.get("uses") == "softprops/action-gh-release@v2"
    )
    uploads = {
        line.strip()
        for line in str(release["with"]["files"]).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "dist/OSQAR-RELEASE-MANIFEST.json" in uploads
    assert all(upload.startswith("dist/") for upload in uploads)
    assert "find _release_payload -type f ! -name SHA256SUMS" in inventory_run
    assert "--root _release_payload" in inventory_run
    publish_download = next(
        step for step in publish["steps"]
        if step.get("uses") == "actions/download-artifact@v4"
    )
    assert publish_download["with"]["name"] == "osqar-accepted-release"
    assert inventory_run.index("release-attestation.intoto.jsonl") < inventory_run.index(
        "SHA256SUMS"
    )
    assert inventory_run.index("SHA256SUMS") < inventory_run.index(
        "--output OSQAR-RELEASE-MANIFEST.json"
    )
    verify_index = next(
        index for index, step in enumerate(inventory_steps)
        if "release-manifest verify" in str(step.get("run", ""))
    )
    upload_index = next(
        index for index, step in enumerate(inventory_steps)
        if step.get("uses") == "actions/upload-artifact@v4"
    )
    assert verify_index < upload_index
    assert not any(step.get("run") for step in inventory_steps[verify_index + 1:])
    accepted_upload = inventory_steps[upload_index]
    assert "RELEASE-NOTES.md" not in str(accepted_upload["with"]["path"])


def test_pypi_receives_only_the_exact_accepted_wheel_and_sdist() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["pypi-publish"]
    run = "\n".join(str(step.get("run", "")) for step in job["steps"])
    publish = next(
        step
        for step in job["steps"]
        if step.get("uses") == "pypa/gh-action-pypi-publish@release/v1"
    )

    assert "-maxdepth 1" in run
    assert "*.whl" in run
    assert "*.tar.gz" in run
    assert '"${#distributions[@]}" -eq 2' in run
    assert publish["with"]["packages-dir"] == "accepted/python-dist/"
