"""Generate human-readable ISO 26262 reference documentation from the catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.iso26262_reference_catalog import load_catalog, render_catalog_rst, validate_catalog

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/iso26262_reference_catalog.rst"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated documentation has drifted")
    args = parser.parse_args(argv)

    catalog = load_catalog()
    validate_catalog(catalog)
    expected = render_catalog_rst(catalog)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            parser.error(f"{OUTPUT.relative_to(ROOT)} is stale; regenerate without --check")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
