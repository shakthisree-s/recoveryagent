from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_backend_endpoints():
    print("Testing /api/health...")
    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    data = r.json()
    print("Health:", data)
    assert data["status"] == "ok"
    assert data["agent"] == "RevenueRecoveryAgent"
    assert data["mode"] == "TEST_MODE"

    print("\nTesting /api/cases...")
    r = client.get("/api/cases")
    assert r.status_code == 200, r.text
    cases = r.json()
    print(f"Loaded {len(cases)} cases")
    assert len(cases) == 8

    print("\nTesting /api/cases/1 detail...")
    r = client.get("/api/cases/1")
    assert r.status_code == 200, r.text
    case_1 = r.json()
    print("Case 1 Decision Flow Steps:", len(case_1["decision_flow"]))

    print("\nTesting /api/cases/1/analyze...")
    r = client.post("/api/cases/1/analyze")
    assert r.status_code == 200, r.text
    analysis = r.json()
    print("Analysis:", analysis["risk_level"], analysis["recommended_action"], analysis["risk_probability"])

    print("\nTesting /api/cases/1/recover (simulating failure for retry test)...")
    r = client.post("/api/cases/1/recover", json={"simulate_failure": True})
    assert r.status_code == 200, r.text
    rec = r.json()
    print("Recovery 1 result:", rec["status"], rec["audit_event"])
    assert rec["status"] == "RETRY_AVAILABLE"

    print("\nTesting /api/cases/1/retry...")
    r = client.post("/api/cases/1/retry")
    assert r.status_code == 200, r.text
    ret = r.json()
    print("Retry result:", ret["status"], "Recovered:", ret["recovered_amount"])
    assert ret["status"] == "RECOVERED"
    assert ret["recovered_amount"] == 18000.0

    print("\nTesting /api/cases/3/approve (High value case)...")
    r = client.post("/api/cases/3/approve")
    assert r.status_code == 200, r.text
    appr = r.json()
    print("Approval result:", appr["status"], "Recovered:", appr["recovered_amount"])
    assert appr["status"] == "RECOVERED"
    assert appr["recovered_amount"] == 30000.0

    print("\nTesting /api/batch/run...")
    r = client.post("/api/batch/run")
    assert r.status_code == 200, r.text
    batch = r.json()
    print("Batch Metrics:", "At-Risk:", batch["at_risk_cases"], "Recovered:", batch["recovered_cases"], "Rate:", batch["recovery_rate"])

    print("\nTesting /api/metrics...")
    r = client.get("/api/metrics")
    assert r.status_code == 200, r.text
    metrics = r.json()
    print("Dashboard Metrics:", metrics)

    print("\nTesting /api/model/metrics...")
    r = client.get("/api/model/metrics")
    assert r.status_code == 200, r.text
    model_m = r.json()
    print("Model Metrics:", model_m["model"], "Accuracy:", model_m["accuracy"])

    print("\nTesting /api/audit...")
    r = client.get("/api/audit")
    assert r.status_code == 200, r.text
    audits = r.json()
    print(f"Audit log returned {len(audits)} events")

    print("\nALL BACKEND API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_backend_endpoints()
