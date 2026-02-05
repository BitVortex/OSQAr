def test_cli_imports() -> None:
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    import tools.osqar_cli  # noqa: F401
