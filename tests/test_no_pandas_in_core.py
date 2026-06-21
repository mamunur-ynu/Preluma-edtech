from pathlib import Path
CORE_FILES=['teacher.py','analytics_core.py','algorithms_core.py','storage_core.py','engine.py']
def test_no_pandas_or_numpy_in_core_files():
    for filename in CORE_FILES:
        text=Path(filename).read_text(encoding='utf-8').lower()
        assert 'import pandas' not in text
        assert 'import numpy' not in text
        assert 'from pandas' not in text
        assert 'from numpy' not in text
