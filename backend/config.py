"""
Centralised, working-directory-independent path + runtime configuration.

Every path is anchored to the project root (the parent of this ``backend``
package) using ``pathlib`` + ``__file__`` so the backend starts identically from:

* the project root          ->  python -m uvicorn backend.main:app ...
* the ``backend`` directory ->  uvicorn main:app ...   (sys.path shim in main)
* Render / any container    ->  uvicorn backend.main:app --host 0.0.0.0 --port $PORT

Environment variables (all optional) override the defaults:

* ``REVENUE_MODEL_PATH``            - path to ``revenue_risk_model.joblib``
* ``REVENUE_MODEL_METADATA_PATH``   - path to ``model_metadata.json``
* ``REVENUE_DB_PATH``               - path to the SQLite database file
* ``REVENUE_AUDIT_LOG_PATH``        - legacy JSON audit mirror
* ``RAZORPAY_MODE``                 - defaults to ``TEST_MODE`` (kept in test mode only)
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root = parent of the "backend" package directory.
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def _from_env_or_root(env_key: str, *relative_candidates: str) -> Path:
    """Resolve a path from an env var, else the first existing candidate under
    the project root, else the first candidate (so callers still get a usable
    absolute path even when the file does not exist yet, e.g. the DB file)."""
    override = os.environ.get(env_key)
    if override:
        return Path(override).expanduser().resolve()

    for candidate in relative_candidates:
        p = Path(candidate)
        if not p.is_absolute():
            p = PROJECT_ROOT / candidate
        if p.exists():
            return p.resolve()

    first = Path(relative_candidates[0])
    if not first.is_absolute():
        first = PROJECT_ROOT / relative_candidates[0]
    return first.resolve()


MODEL_PATH: Path = _from_env_or_root(
    "REVENUE_MODEL_PATH",
    "revenue_risk_model.joblib",
    "backend/revenue_risk_model.joblib",
)

MODEL_METADATA_PATH: Path = _from_env_or_root(
    "REVENUE_MODEL_METADATA_PATH",
    "model_metadata.json",
    "backend/model_metadata.json",
)

DB_PATH: Path = _from_env_or_root(
    "REVENUE_DB_PATH",
    "revenue_recovery.db",
)

# Legacy JSON audit mirror kept for backwards compatibility / easy inspection.
AUDIT_LOG_PATH: Path = _from_env_or_root(
    "REVENUE_AUDIT_LOG_PATH",
    "audit_log.json",
)

RAZORPAY_MODE: str = os.environ.get("RAZORPAY_MODE", "TEST_MODE")

# The single sentence the product must always communicate.
GOVERNANCE_STATEMENT: str = (
    "ML provides the risk signal; merchant policies govern recovery execution."
)
