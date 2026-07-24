"""Versioned, closed-set release manifests for OSQAr shipments."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "osqar.release-manifest.v1"
MANIFEST_VERSION = 1
_RELEASE_VERSION_RE = re.compile(
    r"^v[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?"
    r"(?:\.post[0-9]+)?(?:\.dev[0-9]+)?"
    r"(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?$",
)
_SOURCE_REVISION_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")


@dataclass(frozen=True)
class ReleaseVerification:
    status: str
    ok: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    mismatched: tuple[str, ...] = ()
    empty: tuple[str, ...] = ()
    optional_missing: tuple[str, ...] = ()
    unexpected: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "osqar.release-manifest-report.v1",
            "status": self.status,
            "ok": list(self.ok),
            "missing": list(self.missing),
            "mismatched": list(self.mismatched),
            "empty": list(self.empty),
            "optional_missing": list(self.optional_missing),
            "unexpected": list(self.unexpected),
            "errors": list(self.errors),
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(
                f"symbolic links are not permitted in release inventories: {path}"
            )
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            files.append(path)
        elif not stat.S_ISDIR(mode):
            raise ValueError(f"special files are not permitted in release inventories: {path}")
    return files


def _schema_errors(payload: dict[str, Any]) -> list[str]:
    """Enforce the packaged v1 schema contract without an optional dependency."""

    errors: list[str] = []
    top_keys = {
        "schema", "manifest_version", "release_version", "source_revision",
        "producer", "exclusions", "artifacts",
    }
    if set(payload) != top_keys:
        errors.append(f"schema validation: top-level properties must be {sorted(top_keys)}")
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema validation: schema must be {SCHEMA!r}")
    if payload.get("manifest_version") != MANIFEST_VERSION:
        errors.append(f"schema validation: manifest_version must be {MANIFEST_VERSION}")
    release_version = payload.get("release_version")
    if not isinstance(release_version, str) or not _RELEASE_VERSION_RE.fullmatch(release_version):
        errors.append("schema validation: release_version must be a v-prefixed PEP 440 version")
    source_revision = payload.get("source_revision")
    if not isinstance(source_revision, str) or not _SOURCE_REVISION_RE.fullmatch(source_revision):
        errors.append("schema validation: source_revision must be a full 40- or 64-hex Git SHA")

    producer = payload.get("producer")
    producer_keys = {"command", "tool", "version"}
    if not isinstance(producer, dict) or set(producer) != producer_keys:
        errors.append(f"schema validation: producer properties must be {sorted(producer_keys)}")
    elif any(not isinstance(producer.get(key), str) or not producer[key] for key in producer_keys):
        errors.append("schema validation: producer values must be non-empty strings")

    exclusions = payload.get("exclusions")
    if not isinstance(exclusions, list) or any(
        not isinstance(item, str) or not item for item in exclusions
    ):
        errors.append("schema validation: exclusions must be non-empty strings")
    elif len(exclusions) != len(set(exclusions)):
        errors.append("schema validation: exclusions must be unique")

    artifacts = payload.get("artifacts")
    artifact_keys = {"path", "required", "size", "sha256", "producer_command"}
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("schema validation: artifacts must be a non-empty array")
    else:
        for index, artifact in enumerate(artifacts):
            prefix = f"schema validation: artifact {index}"
            if not isinstance(artifact, dict) or set(artifact) != artifact_keys:
                errors.append(f"{prefix} properties must be {sorted(artifact_keys)}")
                continue
            if not isinstance(artifact["path"], str) or not artifact["path"]:
                errors.append(f"{prefix} path must be a non-empty string")
            if not isinstance(artifact["required"], bool):
                errors.append(f"{prefix} required must be a boolean")
            size = artifact["size"]
            if isinstance(size, bool) or not isinstance(size, int) or size < 1:
                errors.append(f"{prefix} size must be an integer of at least 1")
            digest = artifact["sha256"]
            if not isinstance(digest, str) or len(digest) != 64 or any(
                character not in "0123456789abcdefABCDEF" for character in digest
            ):
                errors.append(f"{prefix} sha256 must be 64 hexadecimal characters")
            if not isinstance(artifact["producer_command"], str) or not artifact["producer_command"]:
                errors.append(f"{prefix} producer_command must be a non-empty string")
    return errors


def _validate_relpath(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("artifact path must be a non-empty string")
    if value != value.strip() or "\\" in value:
        raise ValueError(f"artifact path must use canonical POSIX form: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or value in {"", "."}
        or path.as_posix() != value
    ):
        raise ValueError(f"artifact path must be relative and contained: {value}")
    return path.as_posix()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _reject_symlink_components(root: Path, relpath: str) -> None:
    current = root
    for part in PurePosixPath(relpath).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(
                f"symbolic links are not permitted in release inventories: {relpath}"
            )


def generate_release_manifest(
    *,
    root: Path,
    output: Path,
    source_revision: str,
    release_version: str,
    producer_command: str,
    tool_version: str,
    exclusions: list[str],
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    output = output.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"shipment root is not a directory: {root}")
    if output.exists():
        existing, existing_errors = _load_manifest(output)
        if existing is None or existing_errors:
            raise ValueError(f"refusing to overwrite payload alias: {output}")
    if not release_version.strip() or not source_revision.strip() or not producer_command.strip() or not tool_version.strip():
        raise ValueError("release version, source revision, producer command, and tool version are required")
    if not _RELEASE_VERSION_RE.fullmatch(release_version):
        raise ValueError("release_version must be v followed by a PEP 440-compatible version")
    if not _SOURCE_REVISION_RE.fullmatch(source_revision):
        raise ValueError("source_revision must be a full 40- or 64-hex Git SHA")
    source_revision = source_revision.lower()
    if any(not isinstance(pattern, str) or not pattern.strip() for pattern in exclusions):
        raise ValueError("exclusions must be non-empty strings")
    normalized_exclusions = sorted(set(pattern.strip() for pattern in exclusions))

    excluded = list(normalized_exclusions)
    try:
        excluded.append(output.relative_to(root).as_posix())
    except ValueError:
        pass

    artifacts: list[dict[str, Any]] = []
    for path in _files(root):
        relative = path.relative_to(root).as_posix()
        if _matches(relative, excluded):
            continue
        size = path.stat().st_size
        if size == 0:
            raise ValueError(f"release shipment artifact is empty: {relative}")
        artifacts.append(
            {
                "path": relative,
                "required": True,
                "size": size,
                "sha256": _sha256(path),
                "producer_command": producer_command,
            }
        )
    if not artifacts:
        raise ValueError("qualification shipment contains no artifacts")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "manifest_version": MANIFEST_VERSION,
        "release_version": release_version,
        "source_revision": source_revision,
        "producer": {
            "command": producer_command,
            "tool": "osqar",
            "version": tool_version,
        },
        "exclusions": normalized_exclusions,
        "artifacts": artifacts,
    }
    schema_errors = _schema_errors(payload)
    if schema_errors:
        raise ValueError("generated release manifest violates schema: " + "; ".join(schema_errors))
    _atomic_write(output, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _load_manifest(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"failed to read release manifest: {exc}"]
    if not isinstance(payload, dict):
        return None, ["release manifest must be a JSON object"]

    try:
        errors: list[str] = _schema_errors(payload)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"failed to load packaged release-manifest schema: {exc}"]
    if payload.get("schema") != SCHEMA:
        errors.append(f"unsupported release manifest schema: {payload.get('schema')!r}")
    if not str(payload.get("source_revision") or "").strip():
        errors.append("source_revision is required")
    producer = payload.get("producer")
    if not isinstance(producer, dict) or any(
        not str(producer.get(field) or "").strip() for field in ("command", "tool", "version")
    ):
        errors.append("producer command, tool, and version are required")
    exclusions = payload.get("exclusions")
    if not isinstance(exclusions, list) or any(
        not isinstance(item, str) or not item.strip() for item in exclusions
    ):
        errors.append("exclusions must be a list of non-empty strings")
    elif len(exclusions) != len(set(exclusions)):
        errors.append("exclusions must not contain duplicates")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts must be a list")
    elif not artifacts:
        errors.append("release manifest must declare at least one artifact")
    return payload, errors


def verify_release_manifest(
    *,
    root: Path,
    manifest_path: Path,
    expected_release_version: str | None = None,
    expected_source_revision: str | None = None,
) -> ReleaseVerification:
    root = root.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if not root.is_dir():
        return ReleaseVerification(
            status="ERROR", errors=(f"shipment root is not a directory: {root}",)
        )
    payload, errors = _load_manifest(manifest_path)
    if payload is None or errors:
        return ReleaseVerification(status="ERROR", errors=tuple(errors))
    if expected_release_version is not None and payload["release_version"] != expected_release_version:
        if not _RELEASE_VERSION_RE.fullmatch(expected_release_version):
            errors.append("expected release_version must be v followed by a PEP 440-compatible version")
        errors.append(
            f"release version mismatch: expected {expected_release_version!r}, "
            f"found {payload['release_version']!r}"
        )
    if expected_source_revision is not None and not _SOURCE_REVISION_RE.fullmatch(expected_source_revision):
        errors.append("expected source_revision must be a full 40- or 64-hex Git SHA")
    elif expected_source_revision is not None and payload["source_revision"].lower() != expected_source_revision.lower():
        errors.append(
            f"source revision mismatch: expected {expected_source_revision!r}, "
            f"found {payload['source_revision']!r}"
        )

    artifacts = payload["artifacts"]
    declared: dict[str, dict[str, Any]] = {}
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"artifact {index} must be an object")
            continue
        try:
            relpath = _validate_relpath(artifact.get("path"))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if relpath in declared:
            errors.append(f"duplicate artifact path: {relpath}")
            continue
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            c not in "0123456789abcdefABCDEF" for c in digest
        ):
            errors.append(f"artifact {relpath}: invalid sha256")
        if not isinstance(artifact.get("required"), bool):
            errors.append(f"artifact {relpath}: required must be a boolean")
        if not isinstance(artifact.get("size"), int) or artifact["size"] < 0:
            errors.append(f"artifact {relpath}: invalid size")
        if not str(artifact.get("producer_command") or "").strip():
            errors.append(f"artifact {relpath}: producer_command is required")
        declared[relpath] = artifact
    if errors:
        return ReleaseVerification(status="ERROR", errors=tuple(errors))

    ok: list[str] = []
    missing: list[str] = []
    optional_missing: list[str] = []
    mismatched: list[str] = []
    empty: list[str] = []
    for relpath, artifact in sorted(declared.items()):
        path = root / relpath
        try:
            _reject_symlink_components(root, relpath)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            if artifact["required"]:
                missing.append(relpath)
            else:
                optional_missing.append(relpath)
            continue
        size = path.stat().st_size
        if size == 0:
            empty.append(relpath)
        if size != artifact["size"] or _sha256(path).lower() != artifact["sha256"].lower():
            mismatched.append(relpath)
        elif size > 0:
            ok.append(relpath)

    exclusions = list(payload["exclusions"])
    try:
        exclusions.append(manifest_path.relative_to(root).as_posix())
    except ValueError:
        pass
    try:
        actual = {
            path.relative_to(root).as_posix()
            for path in _files(root)
            if not _matches(path.relative_to(root).as_posix(), exclusions)
        }
    except ValueError as exc:
        errors.append(str(exc))
        actual = set()
    unexpected = sorted(actual - set(declared))
    failed = missing or mismatched or empty or unexpected
    return ReleaseVerification(
        status="ERROR" if errors else ("FAIL" if failed else "PASS"),
        ok=tuple(ok),
        missing=tuple(missing),
        mismatched=tuple(mismatched),
        empty=tuple(empty),
        optional_missing=tuple(optional_missing),
        unexpected=tuple(unexpected),
        errors=tuple(errors),
    )


def render_release_description(manifest: dict[str, Any]) -> str:
    artifacts = manifest.get("artifacts") if isinstance(manifest, dict) else []
    if not isinstance(artifacts, list):
        artifacts = []
    lines = [
        "# OSQAr verified release inventory",
        "",
        f"- Manifest schema: `{manifest.get('schema', '')}`",
        f"- Release version: `{manifest.get('release_version', '')}`",
        f"- Source revision: `{manifest.get('source_revision', '')}`",
        f"- Artifact count: {len(artifacts)}",
        "",
        "## Downloadable artifacts",
        "",
    ]
    for artifact in sorted(
        (item for item in artifacts if isinstance(item, dict)),
        key=lambda item: str(item.get("path") or ""),
    ):
        lines.append(
            f"- `{artifact.get('path', '')}` — SHA-256 `{artifact.get('sha256', '')}`"
        )
    lines.extend(
        [
            "",
            "This description is generated from the release manifest. Verification",
            "establishes inventory closure and integrity, not semantic adequacy or safety.",
            "",
        ]
    )
    return "\n".join(lines)
