from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCS_BASE_URL = "https://bitvortex.github.io/OSQAr/"


@pytest.mark.source_checkout
def test_readme_routes_new_and_power_users_without_overstating_examples() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for required in (
        "## Start here",
        "--template asil_example_c",
        "--template asil_example_rust",
        f"{DOCS_BASE_URL}docs/getting_started.html",
        f"{DOCS_BASE_URL}docs/asil_examples.html",
        f"{DOCS_BASE_URL}docs/cli_reference.html",
        "does not establish ASIL qualification",
    ):
        assert required in readme
    assert "asil-d_c" not in readme


@pytest.mark.source_checkout
def test_readme_documentation_links_target_rendered_github_pages() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)

    assert (
        "[![Docs](https://github.com/bitvortex/OSQAr/actions/workflows/"
        f"pages-deploy.yml/badge.svg?branch=main)]({DOCS_BASE_URL})"
    ) in readme
    source_links = [target for target in targets if target.endswith(".rst")]
    assert source_links == []

    rendered_links = [
        target for target in targets if target.startswith(f"{DOCS_BASE_URL}docs/")
    ]
    assert rendered_links
    for target in rendered_links:
        relative_html = target.removeprefix(DOCS_BASE_URL).split("#", maxsplit=1)[0]
        assert relative_html.endswith(".html")
        source = ROOT / f"{relative_html.removesuffix('.html')}.rst"
        assert source.is_file(), target


@pytest.mark.source_checkout
def test_documentation_home_exposes_progressive_navigation() -> None:
    documentation_home = (ROOT / "index.rst").read_text(encoding="utf-8")
    asil_guide = ROOT / "docs/asil_examples.rst"

    for section in ("Start here", "Task guides", "Power-user reference"):
        assert section in documentation_home
    assert "docs/asil_examples" in documentation_home
    assert asil_guide.is_file()


@pytest.mark.source_checkout
def test_removed_asil_template_name_is_absent_from_current_user_guidance() -> None:
    current_guidance = [
        ROOT / "README.md",
        ROOT / "index.rst",
        *sorted((ROOT / "docs").glob("*.rst")),
    ]

    offenders = [
        str(path.relative_to(ROOT))
        for path in current_guidance
        if "asil-d_c" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


@pytest.mark.source_checkout
def test_asil_examples_state_native_prerequisites_and_target_boundaries() -> None:
    guide = (ROOT / "docs/asil_examples.rst").read_text(encoding="utf-8")
    shared_architecture = (
        ROOT / "osqar_data/templates/asil_example/shared/02_architecture.rst"
    ).read_text(encoding="utf-8")
    c_readme = (
        ROOT / "osqar_data/templates/asil_example/c/README.md"
    ).read_text(encoding="utf-8")
    rust_readme = (
        ROOT / "osqar_data/templates/asil_example/rust/README.md"
    ).read_text(encoding="utf-8")
    catalog = (
        ROOT / "osqar_data/standards/iso26262_reference_catalog.json"
    ).read_text(encoding="utf-8")
    template_root = ROOT / "osqar_data/templates/asil_example"
    template_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(template_root.rglob("*"))
        if path.is_file()
        and path.suffix in {".c", ".h", ".json", ".md", ".py", ".rs", ".rst", ".txt"}
    )

    for command in (
        "cc --version",
        "cmake --version",
        "rustc --version",
        "cargo --version",
    ):
        assert command in guide
    assert "cc --version" in c_readme and "cmake --version" in c_readme
    assert "rustc --version" in rust_readme and "cargo --version" in rust_readme
    assert shared_architecture.startswith(
        "Draft Architecture (ASIL D target SEooC example)"
    )
    for forbidden in (
        "ASIL D safety library",
        "ASIL-D C scaffold",
        "Architecture (ISO 26262-6 §7.4 — ASIL D SEooC)",
    ):
        assert forbidden not in template_text
    assert "ASIL-D C scaffold" not in catalog
    assert "ASIL-target example implementation constraints" in catalog
