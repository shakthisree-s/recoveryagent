# Revenue Recovery Agent

Find revenue that's slipping away and win it back — an autonomous agent for Razorpay AI Buildathon Track 03.

## Live Demo

| | |
|---|---|
| 🖥️ **Frontend** | [recoveryagent-frontend.onrender.com](https://recoveryagent-frontend.onrender.com/) |
| ⚙️ **Backend API** | [recoveryagent-backend.onrender.com](https://recoveryagent-backend.onrender.com) |
| 📄 **Swagger Docs** | [recoveryagent-backend.onrender.com/docs](https://recoveryagent-backend.onrender.com/docs) |

## Real-World Example

**Customer:** Aarav · **Transaction:** ₹8,000 · **Payment:** Failed

```
₹8,000 Payment Failed
        ↓
  ML Risk Prediction
        ↓
RevenueRecoveryAgent Detects Risk
        ↓
  Diagnoses PAYMENT_FAILED
        ↓
  Chooses SEND_RECOVERY_LINK
        ↓
     Policy → ALLOWED
        ↓
  Recovery Attempt
        ↓
 Failure → RETRY_AVAILABLE
        ↓
       Retry
        ↓
  Payment Successful
        ↓
   ₹8,000 Recovered
        ↓
  Audit Trail Updated
```

The agent does not stop at identifying the problem; it takes a bounded recovery action, measures the financial result, and records every decision.

## Example Demo Outcome

*Benchmark / demo results from the 8 seeded cases — not production claims.*

| Metric | Value |
|---|---|
| Cases processed | 8 |
| At-risk cases | 7 |
| Recovered cases | 3 |
| Revenue at risk | ₹1,44,000 |
| Revenue recovered | ₹24,000 |
| Recovery rate | 16.67% |
| Human approval cases | 2 |
| Blocked / stopped cases | 2 |

## Architecture

```
DATA
  ↓
ML RISK PREDICTION
  ↓
SINGLE REVENUE RECOVERY AGENT
  ↓
DETECT
  ↓
DIAGNOSE
  ↓
DECIDE
  ↓
POLICY & GUARDRAILS
  ↓
EXECUTE
  ↓
PAYMENT RESULT
  ↓
REVENUE RECOVERED
  ↓
AUDIT + METRICS
```

## How the Single RevenueRecoveryAgent Works

There is **one** autonomous `RevenueRecoveryAgent` — not multiple agents. It runs six internal stages per case:

1. **Detect** — ML model scores payment-failure risk from transaction + customer features.
2. **Diagnose** — root cause: `PAYMENT_FAILED`, `CHECKOUT_ABANDONED`, `HIGH_VALUE_PAYMENT_FAILURE`, `MAX_ATTEMPTS_EXHAUSTED`, `INCENTIVE_EXCEEDS_POLICY`, `PAYMENT_SUCCESSFUL`, etc., with evidence drawn only from real case data.
3. **Decide** — recommends a bounded action (retry, recovery link, reminder, incentive, escalate, stop).
4. **Policy & Guardrails** — deterministic rules approve, block, or route to a human.
5. **Execute** — runs the action in Razorpay Test Mode and records the outcome.
6. **Measure + Audit** — updates dashboard metrics and writes an immutable audit event.

**ML provides the risk signal; deterministic merchant policies control execution.**

## ML Risk Model

A trained `RandomForestClassifier` (`revenue_risk_model.joblib`) predicts payment-failure probability from transaction, customer, and behavioural features. Its output is a risk signal only — it never decides whether a recovery action is allowed to run.

## Policy & Guardrails

| Constant | Default | Effect |
|---|---|---|
| `MAX_INCENTIVE_PERCENT` | 10% | Requested incentive over the limit → **BLOCKED** |
| `MAX_PAYMENT_ATTEMPTS` | 3 | Attempts reached → **STOP** |
| `MAX_RECOVERY_AMOUNT` | ₹1,00,000 | Amount over the limit → **BLOCKED** |
| `HIGH_VALUE_APPROVAL_THRESHOLD` | ₹25,000 | Amount at/above threshold → **HUMAN_APPROVAL_REQUIRED** |

A successful payment always resolves to **NO_ACTION**. Every case exposes the individual guardrail checks that produced its verdict.

## Recovery Actions

`RETRY_PAYMENT` · `SEND_RECOVERY_LINK` · `SEND_PAYMENT_REMINDER` · `OFFER_BOUNDED_INCENTIVE` · `ESCALATE_TO_HUMAN` · `STOP` · `NO_ACTION`

## Batch Recovery

`POST /api/batch/run` runs Detect → Diagnose → Decide → Policy → Execute → Measure across every case and returns dynamically calculated totals — revenue at risk, revenue recovered, recovery rate, and per-status counts. Nothing is hardcoded.

## Human Approval

High-value cases (≥ ₹25,000) are escalated instead of auto-executed. A human approver can **approve** (with optional notes, recorded in the audit trail) or **reject** (which stops recovery).

## Audit Trail

Every detection, diagnosis, decision, policy verdict, execution, and approval is written as a chronological audit event — persisted in SQLite and queryable per case or across the whole portfolio.

## Razorpay Test Mode

All payment recovery is simulated in Razorpay **Test Mode**. No live transactions are made.

## Technology Stack

- **Backend:** FastAPI, scikit-learn, SQLite
- **Frontend:** React + Vite
- **ML:** RandomForestClassifier

## Project Structure

```
backend/
  main.py       API routes
  state.py      StateManager — orchestration, metrics
  db.py         SQLite persistence
  config.py     Path + environment configuration
  data.py       8 benchmark cases
  schemas.py    Pydantic response models
agent.py        RevenueRecoveryAgent (Detect → Diagnose → Decide → Policy → Execute)
frontend/       React + Vite dashboard
```

## Local Setup

```bash
# Backend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001

# Frontend
cd frontend
npm install
npm run dev
```

Production frontend build uses:

```
VITE_API_URL=https://recoveryagent-backend.onrender.com
```

## API Endpoints

```
GET  /api/health                 GET  /api/cases            GET  /api/cases/{id}
POST /api/cases/{id}/analyze     POST /api/cases/{id}/recover
POST /api/cases/{id}/retry       POST /api/cases/{id}/approve   POST /api/cases/{id}/reject
POST /api/batch/run              GET  /api/batch/{batch_id}
GET  /api/metrics                GET  /api/model/metrics
GET  /api/audit                  GET  /api/audit/{case_id}      POST /api/reset
```

Full interactive reference: [Swagger docs](https://recoveryagent-backend.onrender.com/docs).

## Render Deployment

| Service | Command |
|---|---|
| Backend | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Frontend | `cd frontend && npm ci && npm run build` → publish `frontend/dist` |

The 8 benchmark cases are seeded idempotently into SQLite on first boot; restarts never duplicate data. See [`render.yaml`](render.yaml).

## Testing

```bash
python -m pytest -v
cd frontend && npm run build
```

## Final Goal

Revenue is slipping away silently through failed payments and abandoned checkouts. The RevenueRecoveryAgent finds it, explains why it's at risk, takes a bounded recovery action, and proves — with an auditable trail — exactly how much was won back.
