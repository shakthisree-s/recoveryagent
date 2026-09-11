"""Pytest bootstrap: isolate the test database so `pytest -v` never touches the
developer's real revenue_recovery.db / audit_log.json."""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.gettempdir()) / "rra_pytest"
_TMP.mkdir(exist_ok=True)

os.environ.setdefault("REVENUE_DB_PATH", str(_TMP / "test_revenue_recovery.db"))
os.environ.setdefault("REVENUE_AUDIT_LOG_PATH", str(_TMP / "test_audit_log.json"))

# Start every test session from a clean database file.
for _name in ("test_revenue_recovery.db", "test_revenue_recovery.db-wal",
              "test_revenue_recovery.db-shm"):
    try:
        (_TMP / _name).unlink()
    except FileNotFoundError:
        pass
