import React, { useState } from 'react';
import {
  ShieldCheck,
  Search,
  Code,
  FileDown,
  Filter,
  CheckCircle2,
  Clock,
  RotateCw,
  Ban,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

export default function AuditTrail({ auditLogs = [], onSelectCase }) {
  const [filter, setFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedLogIdx, setExpandedLogIdx] = useState(null);

  const filteredLogs = auditLogs.filter((log) => {
    // Filter by type
    if (filter === 'RECOVERED' && log.status !== 'RECOVERED') return false;
    if (filter === 'APPROVAL' && !log.audit_event?.includes('APPROVAL') && log.policy_evaluation !== 'HUMAN_APPROVAL_REQUIRED') return false;
    if (filter === 'RETRY' && !log.audit_event?.includes('RETRY') && log.decision !== 'RETRY_PAYMENT') return false;
    if (filter === 'BLOCKED' && log.status !== 'BLOCKED' && !log.audit_event?.includes('BLOCKED') && !log.audit_event?.includes('STOPPED')) return false;
    if (filter === 'NO_ACTION' && log.status !== 'NO_ACTION') return false;

    // Search filter
    if (searchTerm.trim() !== '') {
      const term = searchTerm.toLowerCase();
      const matchCase = (log.case_name || '').toLowerCase().includes(term);
      const matchEvent = (log.audit_event || '').toLowerCase().includes(term);
      const matchReason = (log.reason || '').toLowerCase().includes(term);
      const matchDiagnosis = (log.diagnosis || '').toLowerCase().includes(term);
      const matchId = String(log.case_id).includes(term);
      const matchCust = (log.customer_id || '').toLowerCase().includes(term);
      return matchCase || matchEvent || matchReason || matchDiagnosis || matchId || matchCust;
    }

    return true;
  });

  const downloadAuditJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(auditLogs, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `revenue_recovery_audit_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const getStatusBadge = (status, event, stoppingReason) => {
    if (status === 'RECOVERED') {
      return <span className="badge badge-recovered">RECOVERED</span>;
    }
    if (status === 'HUMAN_APPROVAL_REQUIRED' || event?.includes('APPROVAL_REQUIRED')) {
      return <span className="badge badge-approval">APPROVAL REQ</span>;
    }
    if (status === 'RETRY_AVAILABLE' || event?.includes('RETRY_AVAILABLE')) {
      return <span className="badge badge-retry">RETRY AVAIL</span>;
    }
    if (status === 'BLOCKED' || event?.includes('STOPPED') || event?.includes('BLOCKED')) {
      return <span className="badge badge-blocked">{stoppingReason === 'MAX_PAYMENT_ATTEMPTS_REACHED' ? 'STOPPED' : 'BLOCKED'}</span>;
    }
    return <span className="badge badge-noaction">{status}</span>;
  };

  return (
    <div className="page-body">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1>Audit Trail & Compliance</h1>
          <p className="subtitle">
            Immutable audit record of all autonomous and human-supervised payment recovery interventions.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={downloadAuditJSON}>
          <FileDown size={16} />
          <span>Export Audit Log (JSON)</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="tab-group">
          <button
            className={`tab-btn ${filter === 'ALL' ? 'active' : ''}`}
            onClick={() => setFilter('ALL')}
          >
            All Events ({auditLogs.length})
          </button>
          <button
            className={`tab-btn ${filter === 'RECOVERED' ? 'active' : ''}`}
            onClick={() => setFilter('RECOVERED')}
          >
            Recovered
          </button>
          <button
            className={`tab-btn ${filter === 'APPROVAL' ? 'active' : ''}`}
            onClick={() => setFilter('APPROVAL')}
          >
            Human Approval
          </button>
          <button
            className={`tab-btn ${filter === 'RETRY' ? 'active' : ''}`}
            onClick={() => setFilter('RETRY')}
          >
            Retries
          </button>
          <button
            className={`tab-btn ${filter === 'BLOCKED' ? 'active' : ''}`}
            onClick={() => setFilter('BLOCKED')}
          >
            Blocked / Stopped
          </button>
          <button
            className={`tab-btn ${filter === 'NO_ACTION' ? 'active' : ''}`}
            onClick={() => setFilter('NO_ACTION')}
          >
            No Action
          </button>
        </div>

        <div className="search-input-box">
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search audit events, diagnoses, reasons, cases..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="table-container">
        <table className="custom-table">
          <thead>
            <tr>
              <th style={{ width: '36px' }}></th>
              <th>Timestamp</th>
              <th>Case & Customer</th>
              <th>Stage</th>
              <th>Diagnosis</th>
              <th>Decision</th>
              <th>Status</th>
              <th>At Risk</th>
              <th>Recovered</th>
              <th>Audit Event</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((log, index) => {
              const isExpanded = expandedLogIdx === index;
              return (
                <React.Fragment key={index}>
                  <tr
                    onClick={() => setExpandedLogIdx(isExpanded ? null : index)}
                    style={{ background: isExpanded ? '#F8FAFC' : 'inherit' }}
                  >
                    <td>
                      {isExpanded ? (
                        <ChevronDown size={14} color="var(--text-muted)" />
                      ) : (
                        <ChevronRight size={14} color="var(--text-muted)" />
                      )}
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {log.timestamp?.replace('T', ' ')}
                    </td>
                    <td>
                      <strong style={{ color: 'var(--text-primary)', display: 'block' }}>
                        #{log.case_id} {log.case_name}
                      </strong>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {log.customer_id || `cust_${log.case_id}`} • {log.payment_id || `pay_${log.case_id}`}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-noaction" style={{ fontSize: '0.68rem' }}>
                        {log.agent_stage || 'EXECUTE'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.75rem', maxWidth: '140px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{log.diagnosis || 'PAYMENT_FAILED'}</span>
                    </td>
                    <td>
                      <code style={{ fontSize: '0.72rem', background: '#F1F5F9', padding: '2px 5px', borderRadius: '4px' }}>
                        {log.decision}
                      </code>
                    </td>
                    <td>{getStatusBadge(log.status, log.audit_event, log.stopping_reason)}</td>
                    <td style={{ fontWeight: 600 }}>
                      ₹{Number(log.amount_at_risk || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ fontWeight: 600, color: log.recovered_amount > 0 ? '#059669' : 'var(--text-muted)' }}>
                      ₹{Number(log.recovered_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {log.audit_event}
                      </span>
                      {log.stopping_reason && (
                        <div style={{ fontSize: '0.68rem', color: '#DC2626' }}>
                          Reason: {log.stopping_reason}
                        </div>
                      )}
                    </td>
                  </tr>

                  {/* Expanded JSON Details Row */}
                  {isExpanded && (
                    <tr>
                      <td colSpan="10" style={{ padding: '16px 24px', background: '#F8FAFC', borderBottom: '1px solid var(--border-subtle)' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                              Full Audit Event Payload (Decision Reconstruction)
                            </span>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => onSelectCase(log.case_id)}
                            >
                              Inspect Case #{log.case_id}
                            </button>
                          </div>
                          <pre
                            style={{
                              background: '#FFFFFF',
                              padding: '12px',
                              borderRadius: 'var(--radius-md)',
                              border: '1px solid var(--border-subtle)',
                              fontSize: '0.75rem',
                              overflowX: 'auto',
                              color: 'var(--text-primary)'
                            }}
                          >
                            {JSON.stringify(log, null, 2)}
                          </pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
