"""Load, mechanically validate, and render OSQAr's ISO 26262 example catalog.

The packaged catalog is an illustrative, incomplete set of project-authored
mappings and project-policy boundaries. Mechanical validation checks its
syntax and declared internal relationships; it does not establish semantic
validity, completeness, applicability, compliance, qualification, or safety.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

CATALOG_RESOURCE = "standards/iso26262_reference_catalog.json"
REFERENCE_KINDS = {
    "normative_requirement",
    "normative_recommendation",
    "guidance",
    "project_policy",
}
REQUIRED_FIELDS = (
    "reference_id",
    "edition",
    "part",
    "clause",
    "topic",
    "reference_kind",
    "project_paraphrase",
    "applicability",
)
TOP_LEVEL_FIELDS = {"catalog_version", "standard", "evidence_basis", "entries"}
ENTRY_FIELDS = set(REQUIRED_FIELDS) | {"table"}
_CLAUSE_RE = re.compile(r"^[1-9][0-9]*(?:\.[1-9][0-9]*)*$")
SUPPORTED_EDITION = "2018"
KNOWN_TABLE_CLAUSES = {
    (6, 1): "5.4.3",
    (6, 3): "7.4.3",
    (6, 4): "7.4.14",
    (6, 5): "8.4.3",
    (6, 6): "8.4.5",
    (6, 7): "9.4.2",
    (6, 8): "9.4.3",
    (6, 9): "9.4.4",
    (6, 10): "10.4.2",
    (6, 11): "10.4.3",
    (6, 12): "10.4.5",
    (6, 13): "11.4.1",
    (6, 14): "11.4.2",
    (6, 15): "11.4.3",
}
KNOWN_TABLE_TOPICS = {
    (6, 1): "topics covered by modelling and coding guidelines",
    (6, 3): "principles for software architectural design",
    (6, 4): "methods for verification of software architectural design",
    (6, 5): "notations for software unit design",
    (6, 6): "design principles for software unit design and implementation",
    (6, 7): "methods for software unit verification",
    (6, 8): "methods for deriving software unit test cases",
    (6, 9): "structural coverage metrics at software unit level",
    (6, 10): "methods for verification of software integration",
    (6, 11): "methods for deriving software integration test cases",
    (6, 12): "structural coverage metrics at software architecture level",
    (6, 13): "test environments for embedded-software testing",
    (6, 14): "methods for tests of embedded software",
    (6, 15): "methods for deriving embedded-software test cases",
}
SHIPPED_SURFACE_GLOBS = (
    "CHANGELOG.md",
    "README.md",
    "index.rst",
    "docs/**/*.md",
    "docs/**/*.rst",
    "examples/**/*.c",
    "examples/**/*.h",
    "examples/**/*.json",
    "examples/**/*.md",
    "examples/**/*.py",
    "examples/**/*.rst",
    "examples/**/*.toml",
    "examples/**/*.yaml",
    "examples/**/*.yml",
    "osqar_data/templates/**/*.c",
    "osqar_data/templates/**/*.h",
    "osqar_data/templates/**/*.json",
    "osqar_data/templates/**/CMakeLists.txt",
    "osqar_data/templates/**/*.md",
    "osqar_data/templates/**/*.py",
    "osqar_data/templates/**/*.rst",
    "osqar_data/templates/**/*.toml",
    "osqar_data/templates/**/*.yaml",
    "osqar_data/templates/**/*.yml",
    "skills/**/*.md",
    "templates/**/*.json",
    "templates/**/*.md",
    "templates/**/*.py",
    "templates/**/*.rst",
    "templates/**/*.toml",
    "templates/**/*.yaml",
    "templates/**/*.yml",
    "tools/*.py",
)
_INVENTORY_EXCLUDED_PATHS = {
    "docs/iso26262_reference_catalog.rst",
    "tools/generate_iso26262_reference_docs.py",
    "tools/iso26262_reference_catalog.py",
}
_ISO_PART_SEPARATOR = r"[-‐‑‒–—−﹣－]"
_ISO_SPACE = r"[^\S\r\n]+"
_ANCHOR_RE = re.compile(
    rf"(?<![\w])ISO{_ISO_SPACE}26262(?:{_ISO_PART_SEPARATOR}(?P<iso_part>[0-9]+))?"
    r"(?::(?P<edition>[0-9]{4}))?"
)
_CLAUSE_ATOM = r"[0-9]+(?:\.[0-9]+)*"
_CLAUSE_LIST_RE = re.compile(
    rf"(?:§{{1,2}}\s*|Clauses?\s+)(?P<items>{_CLAUSE_ATOM}"
    rf"(?:\s*(?:-|–|/|,)\s*(?:§{{1,2}}\s*)?{_CLAUSE_ATOM}"
    rf"|\s+and\s+(?:§{{1,2}}\s*)?{_CLAUSE_ATOM})*)(?![\w-]|\.\S)"
)
_TABLE_LIST_RE = re.compile(
    r"Tables?\s+(?P<items>[0-9]+"
    r"(?:\s*(?:-|–|/)\s*[0-9]+|\s*,\s*[0-9]+|\s+and\s+[0-9]+)*)"
    r"(?![\w-]|\.\S)"
)
_LOCATOR_MARKER_RE = re.compile(r"(?:§{1,2}|Clauses?|Tables?)")


def _has_malformed_locator_tail(tail: str, *, followed_by_anchor: bool) -> bool:
    """Reject unsupported list syntax without rejecting ordinary prose punctuation."""

    if tail:
        adjacent = tail[0]
        category = unicodedata.category(adjacent)
        name = unicodedata.name(adjacent, "")
        if (
            category in {"Zl", "Zp"}
            or category == "Pd"
            or (category.startswith("C") and adjacent not in "\t\r\n")
            or category.startswith("M")
            or any(token in name for token in ("HYPHEN", "DASH", "MINUS"))
        ):
            return True
    stripped = tail.strip()
    if not stripped:
        return False
    if stripped == "," and followed_by_anchor:
        return False
    if stripped.startswith(","):
        remainder = stripped[1:].lstrip()
        return not bool(_LOCATOR_MARKER_RE.match(remainder))
    and_match = re.match(r"and\b", stripped)
    if and_match:
        remainder = stripped[and_match.end() :].lstrip()
        return not bool(_LOCATOR_MARKER_RE.match(remainder))
    if stripped[0] in "-–":
        return True
    if stripped.startswith("/"):
        remainder = stripped[1:].lstrip()
        return not bool(_LOCATOR_MARKER_RE.match(remainder))
    return False


def _has_malformed_anchor_tail(segment: str) -> bool:
    """Require a lexical delimiter after an ISO part/edition anchor."""

    if not segment:
        return False
    adjacent = segment[0]
    category = unicodedata.category(adjacent)
    if category in {"Zl", "Zp"} or (
        category.startswith(("C", "M")) and adjacent not in "\t\r\n"
    ):
        return True
    if adjacent.isspace():
        return False
    if adjacent in ",;:)]}§":
        return False
    if adjacent == ".":
        return len(segment) > 1 and not segment[1].isspace()
    return True


def _has_hidden_iso_anchor(line: str) -> bool:
    """Detect ISO anchors made invisible by embedded Unicode controls or marks."""

    cleaned: list[str] = []
    source_indexes: list[int] = []
    for index, character in enumerate(line):
        category = unicodedata.category(character)
        forbidden = category in {"Zl", "Zp"} or category.startswith(("C", "M"))
        if forbidden:
            continue
        cleaned.append(character)
        source_indexes.append(index)
    if len(cleaned) == len(line):
        return False

    normalized = "".join(cleaned)
    anchors = list(_ANCHOR_RE.finditer(normalized))
    for anchor_index, anchor in enumerate(anchors):
        if anchor.group("iso_part") is None:
            continue
        segment_end = (
            anchors[anchor_index + 1].start()
            if anchor_index + 1 < len(anchors)
            else len(normalized)
        )
        if not _LOCATOR_MARKER_RE.search(normalized[anchor.end() : segment_end]):
            continue
        source_start = source_indexes[anchor.start()]
        source_end = source_indexes[anchor.end() - 1] + 1
        if source_end - source_start != anchor.end() - anchor.start():
            return True
    return False


@dataclass(frozen=True, order=True)
class InventoryReference:
    """One normalized ISO 26262 locator found on a shipped surface."""

    source_path: str
    line: int
    column: int
    raw: str
    edition: str
    part: int
    clause: str | None
    table: int | None


class CatalogValidationError(ValueError):
    """Raised when the reference catalog violates its mechanical contract."""


def _expand_numeric_items(items: str, *, clauses: bool) -> list[str]:
    tokens = list(re.finditer(_CLAUSE_ATOM if clauses else r"[0-9]+", items))
    values: list[str] = []
    for index, token in enumerate(tokens):
        value = token.group(0)
        pattern = _CLAUSE_RE if clauses else re.compile(r"^[1-9][0-9]*$")
        if not pattern.fullmatch(value):
            raise CatalogValidationError(f"malformed ISO 26262 locator item {value!r}")
        if index == 0:
            values.append(value)
            continue
        separator = items[tokens[index - 1].end() : token.start()]
        if "-" not in separator and "–" not in separator:
            values.append(value)
            continue

        start_parts = values[-1].split(".")
        end_parts = value.split(".")
        if len(start_parts) != len(end_parts) or start_parts[:-1] != end_parts[:-1]:
            raise CatalogValidationError(
                f"malformed ISO 26262 range {values[-1]}-{value}"
            )
        start = int(start_parts[-1])
        end = int(end_parts[-1])
        if end < start or end - start > 100:
            raise CatalogValidationError(
                f"malformed ISO 26262 range {values[-1]}-{value}"
            )
        prefix = ".".join(start_parts[:-1])
        values.extend(
            f"{prefix + '.' if prefix else ''}{number}"
            for number in range(start + 1, end + 1)
        )
    return values


def scan_text_references(text: str, *, source_path: str) -> list[InventoryReference]:
    """Extract normalized ISO 26262 clause/table locators from one text surface."""

    references: list[InventoryReference] = []
    # Split only on the actual newline delimiter. ``str.splitlines()`` also
    # treats control separators U+001C..U+001F as line boundaries, which can
    # hide a malformed suffix by discarding it from the citation line.
    lines = text.split("\n")
    for line_index, line in enumerate(lines):
        line_number = line_index + 1
        if _has_hidden_iso_anchor(line):
            raise CatalogValidationError(
                f"{source_path}:{line_number}:1: malformed ISO 26262 anchor"
            )
        anchors = list(_ANCHOR_RE.finditer(line))
        for anchor_index, anchor in enumerate(anchors):
            part_text = anchor.group("iso_part")
            if part_text is None:
                bare_segment_end = (
                    anchors[anchor_index + 1].start()
                    if anchor_index + 1 < len(anchors)
                    else len(line)
                )
                if _LOCATOR_MARKER_RE.search(line[anchor.end() : bare_segment_end]):
                    raise CatalogValidationError(
                        f"{source_path}:{line_number}:{anchor.start() + 1}: "
                        "malformed ISO 26262 anchor"
                    )
                continue
            part = int(part_text)
            if not 1 <= part <= 12:
                raise CatalogValidationError(
                    f"{source_path}:{line_number}:{anchor.start() + 1}: "
                    "ISO 26262 part must be from 1 through 12"
                )
            edition = anchor.group("edition") or SUPPORTED_EDITION
            if edition != SUPPORTED_EDITION:
                raise CatalogValidationError(
                    f"{source_path}:{line_number}:{anchor.start() + 1}: "
                    f"obsolete or unsupported edition {edition}"
                )

            segment_end = (
                anchors[anchor_index + 1].start()
                if anchor_index + 1 < len(anchors)
                else len(line)
            )
            scan_line = line
            if (
                anchor_index + 1 == len(anchors)
                and line_index + 1 < len(lines)
                and _LOCATOR_MARKER_RE.match(lines[line_index + 1].lstrip())
            ):
                scan_line = f"{line}\n{lines[line_index + 1]}"
                segment_end = len(scan_line)
            segment = scan_line[anchor.end() : segment_end]
            if _has_malformed_anchor_tail(segment) and _LOCATOR_MARKER_RE.search(segment):
                raise CatalogValidationError(
                    f"{source_path}:{line_number}:{anchor.start() + 1}: "
                    "malformed ISO 26262 anchor"
                )
            locators: list[tuple[int, int, str | None, int | None]] = []
            malformed_continuation = False
            for match in _CLAUSE_LIST_RE.finditer(segment):
                tail = segment[match.end() :]
                malformed_continuation |= _has_malformed_locator_tail(
                    tail, followed_by_anchor=anchor_index + 1 < len(anchors)
                )
                for clause in _expand_numeric_items(match.group("items"), clauses=True):
                    locators.append((match.start(), match.end(), clause, None))
            for match in _TABLE_LIST_RE.finditer(segment):
                tail = segment[match.end() :]
                malformed_continuation |= _has_malformed_locator_tail(
                    tail, followed_by_anchor=anchor_index + 1 < len(anchors)
                )
                for table_text in _expand_numeric_items(match.group("items"), clauses=False):
                    locators.append((match.start(), match.end(), None, int(table_text)))

            markers = list(_LOCATOR_MARKER_RE.finditer(segment))
            uncovered_markers = [
                marker
                for marker in markers
                if not any(
                    start <= marker.start() < end for start, end, _, _ in locators
                )
            ]
            malformed_uncovered_marker = any(
                not (remaining := segment[marker.end() :].lstrip())
                or remaining[0] not in "\"'`,;:)]}"
                for marker in uncovered_markers
            )
            if malformed_continuation or malformed_uncovered_marker:
                raise CatalogValidationError(
                    f"{source_path}:{line_number}:{anchor.start() + 1}: "
                    "malformed ISO 26262 locator"
                )

            cited_clauses = [clause for _, _, clause, _ in locators if clause]
            for _, _, _, table in locators:
                if table is None or not cited_clauses:
                    continue
                expected_clause = KNOWN_TABLE_CLAUSES.get((part, table))
                if expected_clause is not None and not any(
                    expected_clause == clause or expected_clause.startswith(f"{clause}.")
                    for clause in cited_clauses
                ):
                    raise CatalogValidationError(
                        f"{source_path}:{line_number}:{anchor.start() + 1}: "
                        f"Table {table} belongs to Clause {expected_clause}"
                    )

            for locator_start, locator_end, clause, table in sorted(
                locators, key=lambda item: item[0]
            ):
                raw_end = anchor.end() + locator_end
                references.append(
                    InventoryReference(
                        source_path=source_path,
                        line=line_number,
                        column=anchor.start() + 1,
                        raw=scan_line[anchor.start() : raw_end],
                        edition=edition,
                        part=part,
                        clause=clause,
                        table=table,
                    )
                )
    return references


def scan_repository_references(repository_root: Path) -> list[InventoryReference]:
    """Inventory locators on the explicit shipped-surface allowlist."""

    paths: set[Path] = set()
    for pattern in SHIPPED_SURFACE_GLOBS:
        paths.update(path for path in repository_root.glob(pattern) if path.is_file())
    references: list[InventoryReference] = []
    for path in sorted(paths):
        source_path = path.relative_to(repository_root).as_posix()
        if source_path in _INVENTORY_EXCLUDED_PATHS:
            continue
        references.extend(
            scan_text_references(
                path.read_text(encoding="utf-8"), source_path=source_path
            )
        )
    return references


def _inventory_key(reference: InventoryReference) -> tuple[str, int, str | None, int | None]:
    return (reference.edition, reference.part, reference.clause, reference.table)


def _entry_key(entry: dict[str, Any]) -> tuple[str, int, str | None, int | None]:
    table = entry.get("table")
    clause = None if table is not None else entry["clause"]
    return (entry["edition"], entry["part"], clause, table)


def _format_key(key: tuple[str, int, str | None, int | None]) -> str:
    edition, part, clause, table = key
    suffix = f"Clause {clause}" if clause is not None else f"Table {table}"
    return f"ISO 26262-{part}:{edition} {suffix}"


def build_maintainer_inventory(
    catalog: dict[str, Any], inventory: list[InventoryReference]
) -> dict[str, Any]:
    """Build the deterministic, repository-only reverse citation inventory."""

    validate_catalog(catalog)
    entries = [
        entry
        for entry in catalog["entries"]
        if entry["reference_kind"] != "project_policy"
    ]
    by_key: dict[tuple[str, int, str | None, int | None], dict[str, Any]] = {}
    for entry in entries:
        key = _entry_key(entry)
        if key in by_key:
            raise CatalogValidationError(f"duplicate catalog locator: {_format_key(key)}")
        by_key[key] = entry

    inventory_paths: dict[tuple[str, int, str | None, int | None], set[str]] = {}
    for reference in inventory:
        key = _inventory_key(reference)
        if key not in by_key:
            raise CatalogValidationError(
                f"uncatalogued {_format_key(key)} at "
                f"{reference.source_path}:{reference.line}:{reference.column}"
            )
        inventory_paths.setdefault(key, set()).add(reference.source_path)

    generated_entries = []
    for entry in entries:
        key = _entry_key(entry)
        paths = sorted(inventory_paths.get(key, set()))
        if not paths:
            raise CatalogValidationError(
                f"{entry['reference_id']} has no shipped repository citation"
            )
        generated_entries.append(
            {"reference_id": entry["reference_id"], "source_paths": paths}
        )
    return {
        "inventory_version": 1,
        "catalog_version": catalog["catalog_version"],
        "entries": generated_entries,
    }


def validate_inventory_coverage(
    catalog: dict[str, Any],
    inventory: list[InventoryReference],
    declared_inventory: dict[str, Any],
) -> None:
    """Require exact closure against the maintainer-only reverse inventory."""

    expected = build_maintainer_inventory(catalog, inventory)
    if declared_inventory != expected:
        raise CatalogValidationError(
            "maintainer inventory source_paths do not exactly match scanned repository citations"
        )


def load_maintainer_inventory(path: Path) -> dict[str, Any]:
    """Load the repository-only reverse citation inventory."""

    return json.loads(path.read_text(encoding="utf-8"))


def render_maintainer_inventory(
    catalog: dict[str, Any], inventory: list[InventoryReference]
) -> str:
    """Render the repository-only reverse citation inventory deterministically."""

    return json.dumps(build_maintainer_inventory(catalog, inventory), indent=2) + "\n"


def load_catalog() -> dict[str, Any]:
    """Load the packaged example catalog from installed package resources."""

    resource = resources.files("osqar_data").joinpath(CATALOG_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def _error(index: int, field: str, message: str) -> CatalogValidationError:
    return CatalogValidationError(f"entries[{index}].{field}: {message}")


def validate_catalog(catalog: dict[str, Any]) -> None:
    """Validate catalog structure and conservative classification mechanically.

    This validator checks the catalog's structural and controlled-mapping
    contract. It does not establish the correctness of an ISO interpretation.
    """

    if not isinstance(catalog, dict):
        raise CatalogValidationError("catalog must be an object")
    extra_top_level = set(catalog) - TOP_LEVEL_FIELDS
    if extra_top_level:
        raise CatalogValidationError(
            f"catalog contains unexpected fields: {sorted(extra_top_level)}"
        )
    if type(catalog.get("catalog_version")) is not int or catalog["catalog_version"] != 1:
        raise CatalogValidationError("catalog_version must be 1")
    if catalog.get("standard") != "ISO 26262":
        raise CatalogValidationError("standard must be 'ISO 26262'")
    evidence_basis = catalog.get("evidence_basis")
    if not isinstance(evidence_basis, str) or not evidence_basis.strip():
        raise CatalogValidationError("evidence_basis must be a non-empty string")
    entries = catalog.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogValidationError("entries must be a non-empty array")

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CatalogValidationError(f"entries[{index}] must be an object")
        for field in REQUIRED_FIELDS:
            if field not in entry:
                raise _error(index, field, "missing required field")
        extra_entry_fields = set(entry) - ENTRY_FIELDS
        if extra_entry_fields:
            raise CatalogValidationError(
                f"entries[{index}] contains unexpected fields: {sorted(extra_entry_fields)}"
            )

        reference_id = entry["reference_id"]
        if not isinstance(reference_id, str) or not reference_id.strip():
            raise _error(index, "reference_id", "must be a non-empty string")
        if reference_id in seen:
            raise CatalogValidationError(f"duplicate reference_id: {reference_id}")
        seen.add(reference_id)

        edition = entry["edition"]
        if not isinstance(edition, str) or not re.fullmatch(r"[0-9]{4}", edition):
            raise _error(index, "edition", "must be a four-digit string")
        if edition != SUPPORTED_EDITION:
            raise _error(index, "edition", f"must be supported edition {SUPPORTED_EDITION}")

        part = entry["part"]
        if isinstance(part, bool) or not isinstance(part, int) or not 1 <= part <= 12:
            raise _error(index, "part", "must be an integer from 1 through 12")

        clause = entry["clause"]
        if not isinstance(clause, str) or not _CLAUSE_RE.fullmatch(clause):
            raise _error(index, "clause", "must be a numeric clause such as '9' or '11.4'")

        table = entry.get("table")
        if table is not None and (
            isinstance(table, bool) or not isinstance(table, int) or table < 1
        ):
            raise _error(index, "table", "must be a positive integer when present")
        if table is not None:
            mapping_key = (part, table)
            expected_clause = KNOWN_TABLE_CLAUSES.get(mapping_key)
            if entry["reference_kind"] != "project_policy" and expected_clause is None:
                raise _error(
                    index,
                    "table",
                    f"no controlled table mapping for Part {part} Table {table}",
                )
            if expected_clause is not None and clause != expected_clause:
                raise _error(
                    index,
                    "clause",
                    f"Table {table} belongs to Clause {expected_clause}",
                )
            expected_topic = KNOWN_TABLE_TOPICS.get(mapping_key)
            if expected_topic is not None and entry["topic"] != expected_topic:
                raise _error(
                    index,
                    "topic",
                    f"must equal controlled topic {expected_topic!r}",
                )

        if entry["reference_kind"] != "project_policy":
            locator = f"T{table}" if table is not None else f"C{clause}"
            expected_id = f"ISO26262-{part}:{edition}-{locator}"
            if reference_id != expected_id:
                raise CatalogValidationError(
                    f"entries[{index}].reference_id does not match locator; "
                    f"expected {expected_id}"
                )

        reference_kind = entry["reference_kind"]
        if not isinstance(reference_kind, str) or reference_kind not in REFERENCE_KINDS:
            raise _error(
                index,
                "reference_kind",
                f"must be one of {sorted(REFERENCE_KINDS)}",
            )
        if reference_kind != "project_policy":
            expected_kinds = (
                {"guidance"}
                if part in {10, 11}
                else {"normative_requirement", "normative_recommendation"}
            )
            if reference_kind not in expected_kinds:
                raise _error(
                    index,
                    "reference_kind",
                    f"Part {part} entries must be one of {sorted(expected_kinds)}",
                )
            if table is not None and reference_kind != "normative_recommendation":
                raise _error(
                    index,
                    "reference_kind",
                    "table entries must be normative recommendations",
                )

        for field in ("topic", "project_paraphrase", "applicability"):
            if not isinstance(entry[field], str) or not entry[field].strip():
                raise _error(index, field, "must be a non-empty string")


def render_catalog_rst(catalog: dict[str, Any]) -> str:
    """Render deterministic catalog documentation."""

    validate_catalog(catalog)
    lines = [
        "ISO 26262 Example Reference Catalog",
        "===================================",
        "",
        ".. warning::",
        "",
        "   This page is generated from an illustrative, incomplete example catalog.",
        "   OSQAr's mechanical checks do not establish the semantic validity,",
        "   completeness, or applicability of its project-authored mappings.",
        "   The example does not establish compliance, qualification, certification,",
        "   or safety. OSQAr policy is not an ISO 26262 requirement. Repository citation",
        "   occurrences are maintained separately and do not require use of OSQAr",
        "   skills or templates.",
        "",
        "Example data source",
        "-------------------",
        "",
        "``osqar_data/standards/iso26262_reference_catalog.json`` is the machine-data",
        "source for this example page; it is not an authoritative ISO 26262 source.",
        "This page must be regenerated with",
        "``python -m tools.generate_iso26262_reference_docs``; tests reject drift.",
        "Repository occurrence closure is maintained separately in",
        "``tests/data/iso26262_reference_inventory.json``. It is generated maintenance",
        "evidence, not a packaged catalog field or a required user-project layout.",
        "",
    ]
    for entry in catalog["entries"]:
        title = f"{entry['reference_id']} — {entry['topic']}"
        lines.extend([title, "~" * len(title), ""])
        location = f"ISO 26262-{entry['part']}:{entry['edition']}, Clause {entry['clause']}"
        if "table" in entry:
            location += f", Table {entry['table']}"
        lines.extend(
            [
                f":Location: {location}",
                f":Classification: {entry['reference_kind'].replace('_', ' ')}",
                f":Applicability: {entry['applicability']}",
                f":OSQAr paraphrase: {entry['project_paraphrase']}",
                "",
            ]
        )
    return "\n".join(lines)
