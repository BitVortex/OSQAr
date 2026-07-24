from __future__ import annotations

from importlib import resources


def test_packaged_templates_are_available_through_importlib_resources() -> None:
    root = resources.files("osqar_data")
    assert root.joinpath("templates/basic/shared/01_requirements.rst").is_file()
    assert root.joinpath("templates/asil_example/c/conf.py").is_file()
    assert root.joinpath("templates/asil_example/rust/conf.py").is_file()
    assert not root.joinpath("templates/asil-d_c").is_dir()
    assert root.joinpath("static/custom.css").is_file()
    assert root.joinpath("schemas/release-manifest-v1.schema.json").is_file()
