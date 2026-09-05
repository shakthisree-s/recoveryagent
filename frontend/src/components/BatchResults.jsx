import React from 'react';
import {
  Play,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Clock,
  Ban,
  Activity
} from 'lucide-react';

export default function BatchResults({
  batchData,
  onRunBatch,
  isRunningBatch,
  onSelectCase
}) {
  const hasResults = batchData && batchData.results && batchData.results.length > 0;

  return (
    <div className="page-body">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1>Batch Recovery Engine</h1>
          <p className="subtitle">
            Autonomous multi-transaction evaluation and bounded batch execution.
          </p>
        </div>

        <button
          className="btn btn-primary"
          onClick={onRunBatch}
          disabled={isRunningBatch}
        >
          {isRunningBatch ? (
            <>
              <Activity size={16} className="animate-spin" />
              <span>Processing Batch...</span>
            </>
          ) : (
            <>
              <Play size={16} fill="currentColor" />
              <span>Execute Batch Run</span>
            </>
          )}
        </button>
      </div>

      {hasResults ? (
        <>
          {/* Summary KPI Grid */}
          <div className="kpi-grid" style={{ marginBottom: '20px' }}>
            <div className="kpi-card highlight">
              <span className="kpi-label">Revenue Recovered</span>
              <div className="kpi-value">
                ₹{batchData.total_revenue_recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="kpi-footer">
                <span style={{ color: '#059669', fontWeight: 600 }}>{batchData.recovery_rate}% Recovery Rate</span>
              </div>
            </div>

            <div className="kpi-card">
              <span className="kpi-label">Revenue at Risk</span>
              <div className="kpi-value">
                ₹{batchData.total_revenue_at_risk.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="kpi-footer">
                <span>{batchData.at_risk_cases} problematic cases</span>
              </div>
            </div>

            <div className="kpi-card">
              <span className="kpi-label">Cases Recovered</span>
              <div className="kpi-value">
                {batchData.recovered_cases} <span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>/ {batchData.total_cases}</span>
              </div>
              <div className="kpi-footer">
                <span>Direct test-mode settlements</span>
              </div>
            </div>

            <div className="kpi-card">
              <span className="kpi-label">Human Approvals</span>
              <div className="kpi-value" style={{ color: batchData.approval_cases > 0 ? '#C2410C' : 'inherit' }}>
                {batchData.approval_cases}
              </div>
              <div className="kpi-footer">
                <span>High-value bounded thresholds</span>
              </div>
            </div>
          </div>

          {/* Sub-counts row */}
          <div className="kpi-sub-grid" style={{ marginBottom: '24px' }}>
            <div className="kpi-sub-card">
              <span className="kpi-sub-label">Total Cases Processed</span>
              <span className="kpi-sub-value">{batchData.total_cases}</span>
            </div>
            <div className="kpi-sub-card">
              <span className="kpi-sub-label">At-Risk Cases</span>
              <span className="kpi-sub-value">{batchData.at_risk_cases}</span>
            </div>
            <div className="kpi-sub-card">
              <span className="kpi-sub-label">Failed / Retry Available</span>
              <span className="kpi-sub-value">{batchData.failed_cases || 0}</span>
            </div>
            <div className="kpi-sub-card">
              <span className="kpi-sub-label">Blocked Cases</span>
              <span className="kpi-sub-value">{batchData.blocked_cases || 0}</span>
            </div>
          </div>

          {/* Case-by-case Results Table */}
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Amount</th>
                  <th>Risk Signal</th>
                  <th>Action</th>
                  <th>Batch Status</th>
                  <th>Audit Event</th>
                  <th>Recovered</th>
                  <th style={{ textAlign: 'right' }}>Inspect</th>
                </tr>
              </thead>
              <tbody>
                {batchData.results.map((item) => (
                  <tr key={item.case_id} onClick={() => onSelectCase(item.case_id)}>
                    <td>
                      <strong>#{item.case_id} {item.name}</strong>
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      ₹{item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td>
                      <span className={`badge badge-${item.risk_level.toLowerCase()}`}>
                        {item.risk_level} ({(item.risk_probability * 100).toFixed(1)}%)
                      </span>
                    </td>
                    <td>
                      <code style={{ fontSize: '0.75rem', background: '#F1F5F9', padding: '2px 6px', borderRadius: '4px' }}>
                        {item.action}
                      </code>
                    </td>
                    <td>
                      {item.status === 'RECOVERED' && (
                        <span className="badge badge-recovered">Recovered</span>
                      )}
                      {item.status === 'HUMAN_APPROVAL_REQUIRED' && (
                        <span className="badge badge-approval">Human Approval</span>
                      )}
                      {item.status === 'NO_ACTION' && (
                        <span className="badge badge-noaction">No Action</span>
                      )}
                      {item.status === 'RETRY_AVAILABLE' && (
                        <span className="badge badge-retry">Retry Available</span>
                      )}
                      {item.status === 'BLOCKED' && (
                        <span className="badge badge-blocked">Blocked</span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {item.audit_event}
                    </td>
                    <td style={{ fontWeight: 600, color: item.recovered_amount > 0 ? '#059669' : 'var(--text-muted)' }}>
                      ₹{item.recovered_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => onSelectCase(item.case_id)}>
                        <span>View</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <Activity size={40} color="var(--text-muted)" style={{ margin: '0 auto 16px' }} />
          <h3>No Batch Execution Record Yet</h3>
          <p style={{ marginTop: '8px', color: 'var(--text-muted)' }}>
            Click "Execute Batch Run" to run the RevenueRecoveryAgent across all merchant transactions.
          </p>
          <button className="btn btn-primary" style={{ marginTop: '20px' }} onClick={onRunBatch}>
            <span>Run Batch Engine Now</span>
          </button>
        </div>
      )}
    </div>
  );
}
