import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database

@pytest.fixture(autouse=True)
def setup_database_schema(tmp_path):
    """Ensure the database schema is created before running any tests.
    Uses a temporary test database to avoid mutating the real stocks.db.
    """
    test_db = tmp_path / "test_stocks.db"
    database.set_db_path(str(test_db))
    database.init_db()
