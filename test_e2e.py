import httpx
import json

BASE_URL = "http://127.0.0.1:8001"

def run_comprehensive_e2e_test():
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    print("=" * 75)
    print("RAZORPAY TRACK 03: AI REVENUE RECOVERY AGENT — E2E TEST SUITE")
    print("=" * 75)

    # 1. Reset state
    print("\n[Step 1] Resetting demo state...")
    r = client.post("/api/reset")
    assert r.status_code == 200, f"Reset failed: {r.text}"
    print("  -> Reset successful. Initial benchmark cases loaded.")

    # 2. Health check
    print("\n[Step 2] Testing /api/health...")
    r = client.get("/api/health")
    assert r.status_code == 200
    health = r.json()
    print(f"  -> Health OK: agent={health['agent']}, mode={health['mode']}, model_loaded={health['model_loaded']}")
    assert health["status"] == "ok"
    assert health["agent"] == "RevenueRecoveryAgent"
    assert health["mode"] == "TEST_MODE"

    # 3. Model Metrics
    print("\n[Step 3] Testing /api/model/metrics...")
    r = client.get("/api/model/metrics")
    assert r.status_code == 200
    model_m = r.json()
    print(f"  -> Model: {model_m['model']}")
    print(f"  -> Accuracy:  {(model_m['accuracy'] * 100):.2f}%")
    print(f"  -> Precision: {(model_m['precision'] * 100):.2f}%")
    print(f"  -> Recall:    {(model_m['recall'] * 100):.2f}%")
    print(f"  -> F1-Score:  {(model_m['f1_score'] * 100):.2f}%")
    print(f"  -> ROC-AUC:   {model_m['roc_auc']}")
    assert model_m["model"] == "RandomForestClassifier"
    assert model_m["accuracy"] == 0.9243

    # 4. CASE 1 — AUTONOMOUS SUCCESS (₹8,000)
    print("\n[Step 4] Testing DEMO CASE 1: Autonomous Recovery Success (₹8,000)...")
    r = client.get("/api/cases/1")
    assert r.status_code == 200
    case1 = r.json()["case"]
    print(f"  -> Detected: Amount=₹{case1['amount']}, Diagnosis={case1.get('diagnosis')}, Action={case1.get('recommended_action')}")
    r = client.post("/api/cases/1/recover", json={"simulate_failure": False})
    assert r.status_code == 200
    res1 = r.json()
    print(f"  -> Result: status={res1['status']}, recovered=₹{res1['recovered_amount']}, audit_event={res1['audit_event']}")
    assert res1["status"] == "RECOVERED"
    assert res1["recovered_amount"] == 8000.0

    # 5. CASE 2 — FAILED → RETRY → SUCCESS (₹12,000)
    print("\n[Step 5] Testing DEMO CASE 2: Failed Recovery -> Retry -> Success (₹12,000)...")
    r = client.post("/api/cases/2/recover", json={"simulate_failure": True})
    assert r.status_code == 200
    res2_fail = r.json()
    print(f"  -> Attempt 1: status={res2_fail['status']}, audit_event={res2_fail['audit_event']}")
    assert res2_fail["status"] == "RETRY_AVAILABLE"

    r = client.post("/api/cases/2/retry")
    assert r.status_code == 200
    res2_retry = r.json()
    print(f"  -> Attempt 2: status={res2_retry['status']}, recovered=₹{res2_retry['recovered_amount']}, audit_event={res2_retry['audit_event']}")
    assert res2_retry["status"] == "RECOVERED"
    assert res2_retry["recovered_amount"] == 12000.0

    # 6. CASE 3 — HIGH VALUE HUMAN APPROVAL (₹50,000)
    print("\n[Step 6] Testing DEMO CASE 3: High-Value Human Approval (₹50,000)...")
    r = client.get("/api/cases/3")
    case3 = r.json()["case"]
    print(f"  -> Case 3 Initial Status: {case3['status']} (Threshold ₹25,000 exceeded)")
    assert case3["status"] == "HUMAN_APPROVAL_REQUIRED"

    r = client.post("/api/cases/3/approve", json={"notes": "Approved by merchant ops supervisor"})
    assert r.status_code == 200
    res3 = r.json()
    print(f"  -> Approval Result: status={res3['status']}, recovered=₹{res3['recovered_amount']}, audit_event={res3['audit_event']}")
    assert res3["status"] == "RECOVERED"
    assert res3["recovered_amount"] == 50000.0

    # 7. CASE 4 — POLICY BLOCK (15% Incentive > 10% Limit)
    print("\n[Step 7] Testing DEMO CASE 4: Policy Block Guardrail (15% Incentive Requested)...")
    r = client.get("/api/cases/4")
    case4 = r.json()["case"]
    print(f"  -> Case 4 Policy Evaluation: {case4.get('policy_evaluation')}, Status: {case4['status']}")
    assert case4["status"] == "BLOCKED"
    assert case4["requested_incentive_percent"] == 15.0

    # 8. CASE 5 — STOPPING RULE (3 Failed Attempts)
    print("\n[Step 8] Testing DEMO CASE 5: Stopping Rule (3 Max Attempts Reached)...")
    r = client.get("/api/cases/5")
    case5 = r.json()["case"]
    print(f"  -> Case 5 Status: {case5['status']}, Stopping Reason: {case5.get('stopping_reason')}")
    assert case5["status"] == "BLOCKED"
    assert case5["stopping_reason"] == "MAX_PAYMENT_ATTEMPTS_REACHED"

    # 9. LIVE DASHBOARD METRICS
    print("\n[Step 9] Testing /api/metrics (Dynamic Calculations)...")
    r = client.get("/api/metrics")
    assert r.status_code == 200
    metrics = r.json()
    print(f"  -> Dynamic Live Metrics:")
    print(f"     Total Revenue at Risk:   ₹{metrics['total_revenue_at_risk']}")
    print(f"     Total Revenue Recovered: ₹{metrics['total_revenue_recovered']}")
    print(f"     Recovery Rate:           {metrics['recovery_rate']}%")
    print(f"     Recovered Cases:         {metrics['recovered_cases']}")
    print(f"     Blocked / Stopped Cases: {metrics['blocked_cases']}")
    assert metrics["total_revenue_recovered"] == 70000.0  # 8000 + 12000 + 50000

    # 10. BATCH RECOVERY ENGINE & BATCH GET
    print("\n[Step 10] Testing /api/batch/run & /api/batch/{batch_id}...")
    r = client.post("/api/batch/run")
    assert r.status_code == 200
    batch = r.json()
    batch_id = batch["batch_id"]
    print(f"  -> Batch Run Output ({batch_id}):")
    print(f"     Total Cases:             {batch['total_cases']}")
    print(f"     At-Risk Cases:           {batch['at_risk_cases']}")
    print(f"     Recovered Cases:         {batch['recovered_cases']}")
    print(f"     Approval Cases:          {batch['approval_cases']}")
    print(f"     Blocked Cases:           {batch['blocked_cases']}")
    print(f"     Revenue at Risk:         ₹{batch['total_revenue_at_risk']}")
    print(f"     Revenue Recovered:       ₹{batch['total_revenue_recovered']}")
    print(f"     Recovery Rate:           {batch['recovery_rate']}%")

    r_get_batch = client.get(f"/api/batch/{batch_id}")
    assert r_get_batch.status_code == 200
    assert r_get_batch.json()["batch_id"] == batch_id

    # 11. AUDIT TRAIL & DECISION RECONSTRUCTION
    print("\n[Step 11] Testing /api/audit (Full Compliance Audit Trail)...")
    r = client.get("/api/audit")
    assert r.status_code == 200
    logs = r.json()
    print(f"  -> Total Audit Events: {len(logs)}")
    assert len(logs) > 0
    print(f"  -> Sample Audit Entry:")
    print(f"     Timestamp:   {logs[0]['timestamp']}")
    print(f"     Case:        #{logs[0]['case_id']} {logs[0]['case_name']}")
    print(f"     Stage:       {logs[0].get('agent_stage')}")
    print(f"     Diagnosis:   {logs[0].get('diagnosis')}")
    print(f"     Decision:    {logs[0]['decision']}")
    print(f"     Event:       {logs[0]['audit_event']}")
    print(f"     Status:      {logs[0]['status']}")
    print(f"     Recovered:   ₹{logs[0]['recovered_amount']}")

    print("\n" + "=" * 75)
    print("ALL 11 TRACK 03 CRITICAL WORKFLOW TESTS PASSED 100%!")
    print("=" * 75)

if __name__ == "__main__":
    run_comprehensive_e2e_test()
