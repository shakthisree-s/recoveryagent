# Revenue Recovery Agent

> **Autonomous AI Revenue Recovery Platform for At-Risk Payments**

Revenue Recovery Agent is an AI-powered platform that helps merchants **detect at-risk payments, diagnose payment failures, decide the best recovery action, execute bounded interventions, and measure recovered revenue**.

## 🚀 Live Demo

- **Frontend:** https://recoveryagent-frontend.onrender.com
- **Backend API:** https://recoveryagent-backend.onrender.com
- **Swagger API Docs:** https://recoveryagent-backend.onrender.com/docs

## 🎯 Problem

Merchants lose revenue because of:

- Failed payments
- Checkout abandonment
- High-risk transactions
- Repeated payment failures
- Recovery actions that require manual intervention

The platform automates recovery while keeping merchants in control through policy guardrails and human approval.

## 🔄 Core Workflow

```text
DETECT
   ↓
DIAGNOSE
   ↓
DECIDE
   ↓
POLICY & RISK
   ↓
EXECUTE

Customer / Transaction Data
          ↓
   ML Risk Prediction
          ↓
   Revenue Recovery Agent
          ↓
 ┌─────────────────────────┐
 │ Detect                  │
 │ Diagnose                │
 │ Decide                  │
 │ Policy & Risk           │
 │ Execute                 │
 └────────────┬────────────┘
              ↓
      Razorpay Test Mode
              ↓
       Recovery Result
              ↓
   Metrics + Audit Trail
   ↓
RECOVER REVENUE
   ↓
AUDIT & MEASURE
