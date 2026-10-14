"""Import-layer contracts for the incremental Streamlit-to-API architecture."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_backend_layers_never_import_streamlit():
    offenders = []
    for folder in ("auth", "ai", "core", "database", "services", "security"):
        for path in (ROOT / folder).glob("*.py"):
            if any(name == "streamlit" or name.startswith("streamlit.") for name in _imports(path)):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_views_use_services_instead_of_persistence_or_provider_modules():
    forbidden_roots = {"database", "storage_core", "homework_core", "project_core"}
    offenders = []
    for path in (ROOT / "views").glob("*.py"):
        for name in _imports(path):
            if name.split(".")[0] in forbidden_roots:
                offenders.append(f"{path.name}: {name}")
    assert offenders == []
