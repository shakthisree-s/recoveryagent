import json
from datetime import datetime
from agent import RevenueRecoveryAgent


agent = RevenueRecoveryAgent()


# =========================================================
# BATCH DATA
# =========================================================

cases = [

    {
        "name": "Failed Payment - Customer 1",
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
    },

    {
        "name": "Successful Payment - Customer 2",
        "gender": "M",
        "amount": 2500,
        "total_amount": 2500,
        "payment_method": "UPI",
        "payment_status": "Success",
        "device_type": "iOS",
        "home_country": "India",
        "shipment_fee": 40,
        "promo_amount": 100,
        "total_spend": 50000,
        "total_transactions": 15,
        "successful_payments": 15,
        "failed_payments": 0,
        "average_transaction_amount": 3333,
        "transaction_day": 5,
        "transaction_hour": 14,
        "failure_rate": 0.00
    },

    {
        "name": "High Value Failure - Customer 3",
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
    },

    {
        "name": "Failed Payment - Customer 4",
        "gender": "F",
        "amount": 12000,
        "total_amount": 12000,
        "payment_method": "UPI",
        "payment_status": "Failed",
        "device_type": "Android",
        "home_country": "India",
        "shipment_fee": 80,
        "promo_amount": 0,
        "total_spend": 36000,
        "total_transactions": 6,
        "successful_payments": 4,
        "failed_payments": 2,
        "average_transaction_amount": 6000,
        "transaction_day": 12,
        "transaction_hour": 18,
        "failure_rate": 0.33
    },

    {
        "name": "Failed Payment - Customer 5",
        "gender": "M",
        "amount": 8500,
        "total_amount": 8500,
        "payment_method": "Debit Card",
        "payment_status": "Failed",
        "device_type": "Android",
        "home_country": "India",
        "shipment_fee": 60,
        "promo_amount": 50,
        "total_spend": 28000,
        "total_transactions": 8,
        "successful_payments": 6,
        "failed_payments": 2,
        "average_transaction_amount": 3500,
        "transaction_day": 9,
        "transaction_hour": 19,
        "failure_rate": 0.25
    },

    {
        "name": "Successful Payment - Customer 6",
        "gender": "F",
        "amount": 4000,
        "total_amount": 4000,
        "payment_method": "UPI",
        "payment_status": "Success",
        "device_type": "iOS",
        "home_country": "India",
        "shipment_fee": 50,
        "promo_amount": 200,
        "total_spend": 60000,
        "total_transactions": 20,
        "successful_payments": 20,
        "failed_payments": 0,
        "average_transaction_amount": 3000,
        "transaction_day": 10,
        "transaction_hour": 13,
        "failure_rate": 0.00
    },

    {
        "name": "Failed Payment - Customer 7",
        "gender": "M",
        "amount": 15000,
        "total_amount": 15000,
        "payment_method": "Credit Card",
        "payment_status": "Failed",
        "device_type": "Android",
        "home_country": "India",
        "shipment_fee": 100,
        "promo_amount": 0,
        "total_spend": 50000,
        "total_transactions": 10,
        "successful_payments": 7,
        "failed_payments": 3,
        "average_transaction_amount": 5000,
        "transaction_day": 17,
        "transaction_hour": 20,
        "failure_rate": 0.30
    },

    {
        "name": "High Value Failure - Customer 8",
        "gender": "F",
        "amount": 45000,
        "total_amount": 45000,
        "payment_method": "Credit Card",
        "payment_status": "Failed",
        "device_type": "iOS",
        "home_country": "India",
        "shipment_fee": 200,
        "promo_amount": 0,
        "total_spend": 90000,
        "total_transactions": 9,
        "successful_payments": 6,
        "failed_payments": 3,
        "average_transaction_amount": 10000,
        "transaction_day": 25,
        "transaction_hour": 21,
        "failure_rate": 0.33
    }
]


# =========================================================
# RUN BATCH
# =========================================================

batch = agent.run_batch(cases)

print("\n" + "=" * 75)
print("              REVENUE RECOVERY BATCH")
print("=" * 75)

for result in batch["results"]:

    print(f"\n#{result['case_id']} {result['name']}")
    print("-" * 75)

    print(f"Amount:       ₹{result['amount']:.2f}")
    print(
        f"Risk:         {result['risk_level']} "
        f"({result['risk_probability']:.4f})"
    )
    print(f"Action:       {result['action']}")
    print(f"Status:       {result['status']}")
    print(f"Recovered:    ₹{result['recovered_amount']:.2f}")
    print(f"Audit:        {result['audit_event']}")


# =========================================================
# BATCH METRICS
# =========================================================

print("\n" + "=" * 75)
print("                    BATCH METRICS")
print("=" * 75)

print(f"Total Cases:             {batch['total_cases']}")
print(f"At-Risk Cases:           {batch['at_risk_cases']}")
print(f"Recovered Cases:         {batch['recovered_cases']}")
print(f"Failed Cases:            {batch['failed_cases']}")
print(f"Blocked Cases:           {batch['blocked_cases']}")
print(f"Human Approval Cases:    {batch['approval_cases']}")

print(
    f"Revenue at Risk:         "
    f"₹{batch['total_revenue_at_risk']:.2f}"
)

print(
    f"Revenue Recovered:       "
    f"₹{batch['total_revenue_recovered']:.2f}"
)

print(
    f"Recovery Rate:           "
    f"{batch['recovery_rate']:.2f}%"
)


# =========================================================
# PERSIST AUDIT TRAIL
# =========================================================

audit_events = []

batch_id = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

for result in batch["results"]:

    event = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "batch_id": batch_id,
        "case_id": result["case_id"],
        "case_name": result["name"],
        "agent": "RevenueRecoveryAgent",
        "risk_level": result["risk_level"],
        "risk_probability": result["risk_probability"],
        "decision": result["action"],
        "status": result["status"],
        "amount_at_risk": result["amount"],
        "recovered_amount": result["recovered_amount"],
        "reason": result["reason"],
        "audit_event": result["audit_event"]
    }

    audit_events.append(event)


with open("audit_log.json", "w") as f:

    json.dump(
        audit_events,
        f,
        indent=4
    )


print("\n" + "=" * 75)
print("AUDIT TRAIL")
print("=" * 75)

print(
    f"Audit events saved: {len(audit_events)}"
)

print(
    "File: audit_log.json"
)

print("=" * 75)