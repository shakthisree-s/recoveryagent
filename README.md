# Revenue Recovery Agent — Razorpay AI Buildathon Track 03

A single autonomous **RevenueRecoveryAgent** that closes the loop:

```
Revenue at Risk → DETECT → DIAGNOSE → DECIDE → POLICY → EXECUTE → MEASURE → AUDIT
```

- **DATA** → transaction + customer features
- **ML RISK PREDICTION** → trained RandomForest (`revenue_risk_model.joblib`) — *risk signal only*
- **SINGLE AGENT** → six internal stages (not multiple agents)
- **POLICY** → bounded merchant guardrails are the only authority on execution
- **EXECUTE** → Razorpay **Test Mode** simulation
- **MEASURE + AUDIT** → dynamic metrics + chronological, persistent audit trail

> ML provides the risk signal; merchant policies govern recovery execution.

---

## Run locally

```bash
# 1. Backend  (from the project root)
python -m venv .venv && . .venv/Scripts/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001

# 2. Frontend
cd frontend
npm install
npm run dev            # http://localhost:3000  (proxies /api → 127.0.0.1:8001)
```

## Tests

```bash
python -m pytest -v
cd frontend && npm run build
```

## Render deployment

| Service  | Command |
| -------- | ------- |
| Backend  | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Frontend | `cd frontend && npm ci && npm run build` → publish `frontend/dist` |

Frontend build env: `VITE_API_URL=https://recoveryagent-backend.onrender.com`
Backend env: `RAZORPAY_MODE=TEST_MODE`, optional `REVENUE_DB_PATH=/tmp/revenue_recovery.db`.
See [`render.yaml`](render.yaml).

---

## Architecture

### Backend
| File | Responsibility |
| ---- | -------------- |
| `backend/config.py` | Working-directory-independent paths (`pathlib` + `__file__`), env overrides |
| `agent.py` | `RevenueRecoveryAgent` — `detect` → `diagnose` → `decide` → `apply_policy` → `execute` → `run_batch` |
| `backend/db.py` | SQLite persistence: `cases`, `recovery_attempts`, `batch_runs`, `audit_events`, `meta` |
| `backend/state.py` | `StateManager` — durable orchestration, idempotent seeding, dynamic metrics |
| `backend/main.py` | FastAPI routes (unchanged surface) + accurate `/api/health` |

### Persistence design
- SQLite file resolved via `REVENUE_DB_PATH` or `<project_root>/revenue_recovery.db`.
- `self.cases` is an in-memory cache kept **write-through** in sync with SQLite,
  so every mutation survives a restart.
- The 8 benchmark cases are seeded **only when the `cases` table is empty**
  (`meta` + row-count guard) → restarts never duplicate data.
- `POST /api/reset` truncates all tables and re-seeds a clean benchmark state.
- `audit_log.json` is kept as a best-effort human-readable mirror of `audit_events`.

### Policy guardrails (defaults)
| Constant | Value | Rule |
| -------- | ----- | ---- |
| `MAX_INCENTIVE_PERCENT` | 10 | incentive > 10% → **BLOCKED** |
| `MAX_PAYMENT_ATTEMPTS` | 3 | attempts ≥ 3 → **STOP** |
| `MAX_RECOVERY_AMOUNT` | 100000 | amount > ₹1,00,000 → **BLOCKED** |
| `HIGH_VALUE_APPROVAL_THRESHOLD` | 25000 | amount ≥ ₹25,000 → **HUMAN_APPROVAL_REQUIRED** |

`policy_result ∈ {ALLOWED, BLOCKED, HUMAN_APPROVAL_REQUIRED}` plus a structured
`policy_checks[]` of `{rule, result, reason}` visible in each case's detail view.

## API (unchanged surface)

```
GET  /api/health                 GET  /api/cases            GET  /api/cases/{id}
POST /api/cases/{id}/analyze     POST /api/cases/{id}/recover
POST /api/cases/{id}/retry       POST /api/cases/{id}/approve   POST /api/cases/{id}/reject
POST /api/batch/run              GET  /api/batch/{batch_id}
GET  /api/metrics                GET  /api/model/metrics
GET  /api/audit                  GET  /api/audit/{case_id}      POST /api/reset
```

## Security
- Razorpay is **Test Mode only**. No secrets committed; `.env` is git-ignored.
- Server never exposes secrets to the frontend; only `VITE_API_URL` is build-time public.
