import React, { useState } from 'react';
import {
  Search,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  Clock,
  RotateCw,
  UserCheck,
  AlertCircle,
  Ban
} from 'lucide-react';

export default function RecoveryCases({
  cases = [],
  onSelectCase,
  onRecover,
  onRetry,
  onApprove
}) {
  const [filterTab, setFilterTab] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredCases = cases.filter((c) => {
    // Filter Tab Match
    if (filterTab === 'AT_RISK' && c.recommended_action === 'NO_ACTION') return false;
    if (filterTab === 'RECOVERED' && c.status !== 'RECOVERED') return false;
    if (filterTab === 'APPROVAL' && c.status !== 'HUMAN_APPROVAL_REQUIRED') return false;
    if (filterTab === 'RETRY' && c.status !== 'RETRY_AVAILABLE') return false;
    if (filterTab === 'BLOCKED' && c.status !== 'BLOCKED') return false;

    // Search Term Match
    if (searchTerm.trim() !== '') {
      const term = searchTerm.toLowerCase();
      const matchCustomer = (c.customer || '').toLowerCase().includes(term);
      const matchDiagnosis = (c.diagnosis || '').toLowerCase().includes(term);
      const matchCause = (c.cause || '').toLowerCase().includes(term);
      const matchId = String(c.case_id).includes(term);
      const matchCustId = (c.customer_id || '').toLowerCase().includes(term);
      return matchCustomer || matchDiagnosis || matchCause || matchId || matchCustId;
    }

    return true;
  });

  const getStatusBadge = (status, stoppingReason) => {
    switch (status) {
      case 'RECOVERED':
        return <span className="badge badge-recovered"><CheckCircle2 size={12} /> Recovered</span>;
      case 'HUMAN_APPROVAL_REQUIRED':
        return <span className="badge badge-approval"><Clock size={12} /> Approval Required</span>;
      case 'RETRY_AVAILABLE':
        return <span className="badge badge-retry"><RotateCw size={12} /> Retry Available</span>;
      case 'BLOCKED':
        return (
          <span className="badge badge-blocked" title={stoppingReason || 'Blocked by Policy'}>
            <Ban size={12} /> {stoppingReason === 'MAX_PAYMENT_ATTEMPTS_REACHED' ? 'Stopped (3 Attempts)' : 'Blocked'}
          </span>
        );
      case 'NO_ACTION':
        return <span className="badge badge-noaction">No Action</span>;
      default:
        return <span className="badge badge-pending">Pending</span>;
    }
  };

  const getRiskBadge = (level, prob) => {
    const pct = prob !== undefined ? ` (${(prob * 100).toFixed(1)}%)` : '';
    switch (level) {
      case 'HIGH':
        return <span className="badge badge-high">HIGH{pct}</span>;
      case 'MEDIUM':
        return <span className="badge badge-medium">MED{pct}</span>;
      default:
        return <span className="badge badge-low">LOW{pct}</span>;
    }
  };

  return (
    <div className="page-body">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1>Recovery Cases</h1>
          <p className="subtitle">
            Inspect revenue-at-risk cases, review AI diagnoses, policy boundaries, and trigger bounded recovery actions.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="tab-group">
          <button
            className={`tab-btn ${filterTab === 'ALL' ? 'active' : ''}`}
            onClick={() => setFilterTab('ALL')}
          >
            All Cases ({cases.length})
          </button>
          <button
            className={`tab-btn ${filterTab === 'AT_RISK' ? 'active' : ''}`}
            onClick={() => setFilterTab('AT_RISK')}
          >
            At Risk
          </button>
          <button
            className={`tab-btn ${filterTab === 'APPROVAL' ? 'active' : ''}`}
            onClick={() => setFilterTab('APPROVAL')}
          >
            Human Approval
          </button>
          <button
            className={`tab-btn ${filterTab === 'RETRY' ? 'active' : ''}`}
            onClick={() => setFilterTab('RETRY')}
          >
            Retry Available
          </button>
          <button
            className={`tab-btn ${filterTab === 'BLOCKED' ? 'active' : ''}`}
            onClick={() => setFilterTab('BLOCKED')}
          >
            Blocked / Stopped
          </button>
          <button
            className={`tab-btn ${filterTab === 'RECOVERED' ? 'active' : ''}`}
            onClick={() => setFilterTab('RECOVERED')}
          >
            Recovered
          </button>
        </div>

        <div className="search-input-box">
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search by customer, case ID, diagnosis..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Cases Data Table */}
      <div className="table-container">
        <table className="custom-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Customer</th>
              <th>Amount</th>
              <th>Risk Signal</th>
              <th>Diagnosis</th>
              <th>Action & Policy</th>
              <th>Status</th>
              <th>Recovered</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredCases.map((caseItem) => (
              <tr key={caseItem.case_id} onClick={() => onSelectCase(caseItem.case_id)}>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  #{caseItem.case_id}
                </td>
                <td>
                  <strong style={{ color: 'var(--text-primary)' }}>{caseItem.customer}</strong>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {caseItem.customer_id || `cust_${caseItem.case_id}`} • {caseItem.payment_status || 'Failed'}
                  </div>
                </td>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  ₹{caseItem.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </td>
                <td>{getRiskBadge(caseItem.risk_level, caseItem.risk_probability || caseItem.risk_score)}</td>
                <td style={{ maxWidth: '220px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block' }}>
                    {caseItem.diagnosis || 'PAYMENT_FAILED'}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {caseItem.diagnosis_label || caseItem.cause || caseItem.reason}
                  </span>
                </td>
                <td>
                  <code style={{ fontSize: '0.75rem', background: '#F1F5F9', padding: '2px 6px', borderRadius: '4px', display: 'inline-block' }}>
                    {caseItem.recommended_action}
                  </code>
                  <div style={{ fontSize: '0.72rem', color: caseItem.policy_evaluation === 'BLOCKED' ? '#DC2626' : (caseItem.policy_evaluation === 'HUMAN_APPROVAL_REQUIRED' ? '#C2410C' : '#059669'), marginTop: '2px', fontWeight: 500 }}>
                    Policy: {caseItem.policy_evaluation || 'ALLOWED'}
                  </div>
                </td>
                <td>{getStatusBadge(caseItem.status, caseItem.stopping_reason)}</td>
                <td style={{ fontWeight: 600, color: caseItem.recovered_amount > 0 ? '#059669' : 'var(--text-muted)' }}>
                  ₹{caseItem.recovered_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </td>
                <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                  {caseItem.status === 'HUMAN_APPROVAL_REQUIRED' ? (
                    <button
                      className="btn btn-warning btn-sm"
                      onClick={() => onApprove(caseItem.case_id)}
                      title="Approve high-value recovery"
                    >
                      <UserCheck size={14} />
                      <span>Approve</span>
                    </button>
                  ) : caseItem.status === 'RETRY_AVAILABLE' ? (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => onRetry(caseItem.case_id)}
                      title="Retry failed payment recovery"
                    >
                      <RotateCw size={14} />
                      <span>Retry</span>
                    </button>
                  ) : caseItem.status === 'RECOVERED' ? (
                    <span style={{ fontSize: '0.78rem', color: '#059669', fontWeight: 600 }}>
                      Settled
                    </span>
                  ) : caseItem.status === 'BLOCKED' ? (
                    <span style={{ fontSize: '0.78rem', color: '#DC2626', fontWeight: 600 }}>
                      Halted
                    </span>
                  ) : caseItem.recommended_action !== 'NO_ACTION' ? (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onRecover(caseItem.case_id)}
                    >
                      <span>Recover</span>
                    </button>
                  ) : (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectCase(caseItem.case_id)}
                    >
                      <span>View</span>
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
