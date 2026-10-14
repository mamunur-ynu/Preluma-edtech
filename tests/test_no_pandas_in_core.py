"""Architecture guard: the lightweight logic layers must stay free of pandas/numpy (and of Streamlit)."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_CORE_FILES = ["teacher.py", "analytics_core.py", "algorithms_core.py", "storage_core.py", "engine.py"]
BACKEND_FOLDERS = ["core", "services", "database", "auth", "ai"]
HEAVY = ("import pandas", "import numpy", "from pandas", "from numpy")


def _backend_files():
    for folder in BACKEND_FOLDERS:
        yield from sorted((ROOT / folder).glob("*.py"))
    yield ROOT / "config.py"


def test_no_pandas_or_numpy_in_core_files():
    for filename in LEGACY_CORE_FILES:
        text = (ROOT / filename).read_text(encoding="utf-8").lower()
        for needle in HEAVY:
            assert needle not in text, f"{filename} imports {needle}"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def test_core_package_is_stdlib_only():
    """core/ is the portable heart of the app: it may import only the standard library and itself."""
    for path in (ROOT / "core").glob("*.py"):
        foreign = {m for m in _imported_modules(path) if m != "core" and m not in sys.stdlib_module_names}
        assert not foreign, f"{path.name} imports third-party modules: {sorted(foreign)}"


def test_backend_never_imports_streamlit_or_pandas():
    """Business logic must not depend on the UI framework (so FastAPI/React can reuse it)."""
    banned = {"streamlit", "pandas", "plotly"}
    for path in _backend_files():
        used = _imported_modules(path) & banned
        # config.py reads st.secrets lazily inside one function, on purpose (see load_streamlit_secrets_into_env).
        if path.name == "config.py":
            used -= {"streamlit"}
        assert not used, f"{path.relative_to(ROOT)} must not import {sorted(used)}"
