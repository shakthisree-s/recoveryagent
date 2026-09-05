import React, { useState } from 'react';
import {
  X,
  Play,
  RotateCw,
  UserCheck,
  Ban,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Sparkles,
  ShieldCheck,
  History,
  FileText
} from 'lucide-react';
import DecisionFlow from './DecisionFlow';

export default function CaseDetailModal({
  caseDetail,
  onClose,
  onAnalyze,
  onRecover,
  onRetry,
  onApprove,
  onReject,
  isLoading
}) {
  const [activeTab, setActiveTab] = useState('flow');
  const [simulateFailureToggle, setSimulateFailureToggle] = useState(false);

  if (!caseDetail) return null;

  const { case: caseData, analysis, decision_flow, audit_history } = caseDetail;

  const isHumanApproval = caseData.status === 'HUMAN_APPROVAL_REQUIRED';
  const isRetryAvailable = caseData.status === 'RETRY_AVAILABLE';
  const isRecovered = caseData.status === 'RECOVERED';
  const isBlocked = caseData.status === 'BLOCKED';
  const stoppingReason = caseData.stopping_reason || analysis?.stopping_reason;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="drawer-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                CASE #{caseData.case_id}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                ({caseData.customer_id || `cust_${caseData.case_id}`} • {caseData.payment_id || `pay_${caseData.case_id}`})
              </span>
              {isRecovered && <span className="badge badge-recovered">RECOVERED</span>}
              {isHumanApproval && <span className="badge badge-approval">APPROVAL REQUIRED</span>}
              {isRetryAvailable && <span className="badge badge-retry">RETRY AVAILABLE</span>}
              {isBlocked && <span className="badge badge-blocked">BLOCKED / STOPPED</span>}
              {caseData.status === 'NO_ACTION' && <span className="badge badge-noaction">NO ACTION</span>}
            </div>
            <h2 style={{ marginTop: '4px' }}>{caseData.customer}</h2>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            style={{ borderRadius: '50%', width: '32px', height: '32px', padding: 0 }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation Tabs within Modal */}
        <div style={{ padding: '0 24px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="tab-group" style={{ margin: '12px 0 8px' }}>
            <button
              className={`tab-btn ${activeTab === 'flow' ? 'active' : ''}`}
              onClick={() => setActiveTab('flow')}
            >
              AI Decision Flow
            </button>
            <button
              className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              Transaction Profile
            </button>
            <button
              className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
              onClick={() => setActiveTab('audit')}
            >
              Audit History ({audit_history?.length || 0})
            </button>
          </div>
        </div>

        {/* Body Content */}
        <div className="drawer-body">
          {/* Key Metric Highlights */}
          <div className="meta-grid">
            <div className="meta-item">
              <span className="meta-label">Revenue at Risk</span>
              <span className="meta-value">₹{caseData.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Recovered Amount</span>
              <span className="meta-value" style={{ color: caseData.recovered_amount > 0 ? '#059669' : 'inherit' }}>
                ₹{caseData.recovered_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Risk Probability</span>
              <span className="meta-value">
                {(analysis?.risk_probability ? analysis.risk_probability * 100 : caseData.risk_probability * 100).toFixed(1)}% ({analysis?.risk_level || caseData.risk_level})
              </span>
            </div>
          </div>

          {/* Banner: Human Approval */}
          {isHumanApproval && (
            <div className="alert-box alert-warning">
              <AlertTriangle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Human Approval Required</strong>
                <p style={{ marginTop: '2px', fontSize: '0.8125rem' }}>
                  This transaction of ₹{caseData.amount.toLocaleString('en-IN')} exceeds the autonomous recovery threshold of ₹25,000. The agent has safely escalated for human supervisor sign-off.
                </p>
              </div>
            </div>
          )}

          {/* Banner: Retry Available */}
          {isRetryAvailable && (
            <div className="alert-box alert-info">
              <RotateCw size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Recovery Attempt Failed — Retry Permitted</strong>
                <p style={{ marginTop: '2px', fontSize: '0.8125rem' }}>
                  Attempt 1 was unfulfilled. Bounded policy allows up to 3 payment retries. Click "Retry Recovery" to execute Attempt 2.
                </p>
              </div>
            </div>
          )}

          {/* Banner: Stopping Rule / Blocked */}
          {isBlocked && (
            <div className="alert-box alert-warning" style={{ background: '#FEF2F2', borderColor: '#FECACA', color: '#991B1B' }}>
              <Ban size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Recovery Halted by Policy / Stopping Rules</strong>
                <p style={{ marginTop: '2px', fontSize: '0.8125rem' }}>
                  {stoppingReason === 'MAX_PAYMENT_ATTEMPTS_REACHED'
                    ? 'Maximum payment attempts (3) have been exhausted. Autonomous stopping rules prevent further retries.'
                    : stoppingReason === 'POLICY_GUARDRAIL_VIOLATION'
                    ? `Requested incentive (${caseData.requested_incentive_percent}%) exceeds merchant policy limit (10%). Intervention is blocked.`
                    : stoppingReason === 'HUMAN_OPERATOR_REJECTED'
                    ? 'Human operator rejected high-value recovery execution.'
                    : (caseData.reason || 'Action blocked by safety policies.')}
                </p>
              </div>
            </div>
          )}

          {/* Tab 1: AI Decision Flow */}
          {activeTab === 'flow' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles size={16} color="#0F172A" />
                  <span>Single Agent Autonomous Decision Flow</span>
                </h4>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onAnalyze(caseData.case_id)}
                  disabled={isLoading}
                >
                  <RotateCw size={12} />
                  <span>Re-Analyze</span>
                </button>
              </div>

              <DecisionFlow steps={decision_flow} />

              {/* Execution Attempt History */}
              {caseData.attempts && caseData.attempts.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <h4 style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <History size={16} />
                    <span>Execution Attempts Log ({caseData.attempts.length} / 3 Max)</span>
                  </h4>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {caseData.attempts.map((att, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '12px 16px',
                          background: '#F8FAFC',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-md)',
                          fontSize: '0.8125rem'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <strong>Attempt {att.attempt || idx + 1}: {att.action || 'RETRY_PAYMENT'}</strong>
                          <span style={{ color: att.status === 'RECOVERED' ? '#059669' : (att.status === 'BLOCKED' ? '#DC2626' : '#C2410C'), fontWeight: 600 }}>
                            {att.status}
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                          <span>Event: {att.audit_event}</span>
                          <span>Recovered: ₹{(att.recovered_amount || 0).toLocaleString('en-IN')}</span>
                        </div>
                        {att.reason && (
                          <div style={{ marginTop: '4px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            Note: {att.reason}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Transaction Profile */}
          {activeTab === 'profile' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <span className="meta-label">Customer ID</span>
                  <p className="meta-value">{caseData.customer_id || `cust_${caseData.case_id}`}</p>
                </div>
                <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <span className="meta-label">Transaction / Payment ID</span>
                  <p className="meta-value">{caseData.payment_id || `pay_${caseData.case_id}`}</p>
                </div>
                <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <span className="meta-label">Payment Method</span>
                  <p className="meta-value">{caseData.payment_method}</p>
                </div>
                <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <span className="meta-label">Device Type</span>
                  <p className="meta-value">{caseData.device_type}</p>
                </div>
                <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <span className="meta-label">Historical Failure Rate</span>
                  <p className="meta-value">{((caseData.failure_rate || 0) * 100).toFixed(1)}%</p>
                </div>
                <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <span className="meta-label">Total Transactions</span>
                  <p className="meta-value">{caseData.total_transactions} ({caseData.successful_payments} Success / {caseData.failed_payments} Failed)</p>
                </div>
                <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <span className="meta-label">Customer Total Spend</span>
                  <p className="meta-value">₹{(caseData.total_spend || 0).toLocaleString('en-IN')}</p>
                </div>
                <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <span className="meta-label">Incentive Requested</span>
                  <p className="meta-value">{caseData.requested_incentive_percent || 0}% (Max 10%)</p>
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: Audit History */}
          {activeTab === 'audit' && (
            <div>
              {audit_history && audit_history.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {audit_history.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '12px 16px',
                        background: '#FFFFFF',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        fontSize: '0.8125rem'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{item.audit_event}</span>
                        <span style={{ color: 'var(--text-muted)' }}>{item.timestamp}</span>
                      </div>
                      <p style={{ color: 'var(--text-secondary)', marginBottom: '4px' }}>{item.reason}</p>
                      <div style={{ display: 'flex', gap: '16px', color: 'var(--text-muted)' }}>
                        <span>Status: <strong>{item.status}</strong></span>
                        <span>Recovered: <strong>₹{(item.recovered_amount || 0).toLocaleString('en-IN')}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No audit history recorded yet for this case.</p>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="drawer-footer">
          {isHumanApproval ? (
            <>
              <button
                className="btn btn-danger btn-sm"
                onClick={() => onReject(caseData.case_id)}
                disabled={isLoading}
              >
                <Ban size={14} />
                <span>Reject</span>
              </button>
              <button
                className="btn btn-success"
                onClick={() => onApprove(caseData.case_id)}
                disabled={isLoading}
              >
                <UserCheck size={16} />
                <span>Approve Recovery (₹{caseData.amount.toLocaleString('en-IN')})</span>
              </button>
            </>
          ) : isRetryAvailable ? (
            <button
              className="btn btn-primary"
              onClick={() => onRetry(caseData.case_id)}
              disabled={isLoading}
            >
              <RotateCw size={16} />
              <span>Retry Recovery (Attempt {caseData.attempts?.length + 1 || 2})</span>
            </button>
          ) : isRecovered ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#059669', fontWeight: 600 }}>
              <CheckCircle2 size={18} />
              <span>Fully Recovered in Test Mode (₹{caseData.recovered_amount.toLocaleString('en-IN')})</span>
            </div>
          ) : isBlocked ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#DC2626', fontWeight: 600 }}>
              <Ban size={16} />
              <span>Recovery Halted by Policy Engine</span>
            </div>
          ) : caseData.recommended_action !== 'NO_ACTION' ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={simulateFailureToggle}
                  onChange={(e) => setSimulateFailureToggle(e.target.checked)}
                />
                <span>Simulate Failure (Demo Retry Flow)</span>
              </label>

              <button
                className="btn btn-primary"
                onClick={() => onRecover(caseData.case_id, simulateFailureToggle)}
                disabled={isLoading}
              >
                <Play size={16} fill="currentColor" />
                <span>Execute Recovery</span>
              </button>
            </div>
          ) : (
            <button className="btn btn-secondary" onClick={onClose}>
              <span>Close</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
