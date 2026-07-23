"""Generate the maintainer-only ISO 26262 repository citation inventory."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.iso26262_reference_catalog import (
    load_catalog,
    render_maintainer_inventory,
    scan_repository_references,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tests/data/iso26262_reference_inventory.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the checked-in maintainer inventory has drifted",
    )
    args = parser.parse_args(argv)

    expected = render_maintainer_inventory(
        load_catalog(), scan_repository_references(ROOT)
    )
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            parser.error(f"{OUTPUT.relative_to(ROOT)} is stale; regenerate without --check")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
