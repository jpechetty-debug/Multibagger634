import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database

@pytest.fixture(autouse=True)
def setup_database_schema():
    """Ensure the database schema is created before running any tests.
    This prevents 'no such table' errors on a fresh checkout where 
    database.init_db() hasn't been called by the screener yet.
    """
    database.init_db()
