from agent import RevenueRecoveryAgent


agent = RevenueRecoveryAgent()


# =========================================================
# TEST CASES
# =========================================================

payment_failure = {
    "name": "Payment Failure",
    "gender": "M",
    "amount": 18000,
    "total_amount": 18000,
    "payment_method": "Credit Card",
    "payment_status": "Failed",
    "device_type": "Android",
    "home_country": "India",
    "shipment_fee": 100,
    "promo_amount": 0,
    "total_spend": 45000,
    "total_transactions": 5,
    "successful_payments": 3,
    "failed_payments": 2,
    "average_transaction_amount": 9000,
    "transaction_day": 15,
    "transaction_hour": 20,
    "failure_rate": 0.40
}


high_value_failure = {
    "name": "High Value Failure",
    "gender": "F",
    "amount": 30000,
    "total_amount": 30000,
    "payment_method": "Credit Card",
    "payment_status": "Failed",
    "device_type": "iOS",
    "home_country": "India",
    "shipment_fee": 150,
    "promo_amount": 0,
    "total_spend": 70000,
    "total_transactions": 7,
    "successful_payments": 5,
    "failed_payments": 2,
    "average_transaction_amount": 10000,
    "transaction_day": 22,
    "transaction_hour": 21,
    "failure_rate": 0.29
}


# =========================================================
# SCENARIO 1 — FAILED RECOVERY → RETRY → SUCCESS
# =========================================================

print("\n" + "=" * 65)
print("SCENARIO 1: FAILED RECOVERY → RETRY")
print("=" * 65)

analysis = agent.analyze(payment_failure)

print("\nDETECT")
print(f"Risk Probability: {analysis['risk_probability']}")
print(f"Risk Level:       {analysis['risk_level']}")

print("\nDIAGNOSE")
print(f"Reason:           {analysis['reason']}")

print("\nDECIDE")
print(f"Action:           {analysis['recommended_action']}")

print("\nEXECUTE - ATTEMPT 1")

attempt_1 = agent.execute_recovery(
    payment_failure,
    simulate_failure=True
)

print(f"Status:           {attempt_1['status']}")
print(f"Recovered:        ₹{attempt_1['recovered_amount']:.2f}")
print(f"Audit Event:      {attempt_1['audit_event']}")

print("\nRETRY RECOVERY")

retry = agent.retry_recovery(payment_failure)

print(f"Status:           {retry['status']}")
print(f"Recovered:        ₹{retry['recovered_amount']:.2f}")
print(f"Audit Event:      {retry['audit_event']}")


# =========================================================
# SCENARIO 2 — HUMAN APPROVAL
# =========================================================

print("\n" + "=" * 65)
print("SCENARIO 2: HIGH VALUE → HUMAN APPROVAL")
print("=" * 65)

analysis = agent.analyze(high_value_failure)

print("\nDETECT")
print(f"Risk Probability: {analysis['risk_probability']}")
print(f"Risk Level:       {analysis['risk_level']}")

print("\nDIAGNOSE")
print(f"Reason:           {analysis['reason']}")

print("\nDECIDE")
print(f"Action:           {analysis['recommended_action']}")

print("\nEXECUTE")

approval_required = agent.execute_recovery(
    high_value_failure
)

print(f"Status:           {approval_required['status']}")
print(f"Recovered:        ₹{approval_required['recovered_amount']:.2f}")
print(f"Audit Event:      {approval_required['audit_event']}")

print("\nHUMAN APPROVAL")

approval = agent.approve_recovery(
    high_value_failure
)

print(f"Status:           {approval['status']}")
print(f"Action:           {approval['action']}")
print(f"Recovered:        ₹{approval['recovered_amount']:.2f}")
print(f"Audit Event:      {approval['audit_event']}")


# =========================================================
# FINAL SUMMARY
# =========================================================

total_recovered = (
    retry["recovered_amount"]
    + approval["recovered_amount"]
)

total_at_risk = (
    payment_failure["amount"]
    + high_value_failure["amount"]
)

recovery_rate = (
    total_recovered / total_at_risk
) * 100


print("\n" + "=" * 65)
print("FINAL RECOVERY SUMMARY")
print("=" * 65)

print(f"Revenue at Risk:       ₹{total_at_risk:.2f}")
print(f"Revenue Recovered:     ₹{total_recovered:.2f}")
print(f"Recovery Rate:         {recovery_rate:.2f}%")

print("\nAUDIT TRAIL")
print("-" * 65)

print(
    f"1. {attempt_1['audit_event']}"
    f" → ₹{attempt_1['recovered_amount']:.2f}"
)

print(
    f"2. {retry['audit_event']}"
    f" → ₹{retry['recovered_amount']:.2f}"
)

print(
    f"3. {approval_required['audit_event']}"
    f" → ₹{approval_required['recovered_amount']:.2f}"
)

print(
    f"4. {approval['audit_event']}"
    f" → ₹{approval['recovered_amount']:.2f}"
)

print("=" * 65)