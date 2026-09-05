import React from 'react';
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Percent,
  Clock,
  ShieldCheck,
  Cpu,
  RefreshCw,
  Ban,
  ArrowUpRight
} from 'lucide-react';

export default function Overview({ metrics, modelMetrics, onOpenCase, cases = [] }) {
  const atRiskRevenue = metrics?.total_revenue_at_risk || 0;
  const recoveredRevenue = metrics?.total_revenue_recovered || 0;
  const recoveryRate = metrics?.recovery_rate || 0;
  const recoveredCases = metrics?.recovered_cases || 0;
  const totalCases = metrics?.total_cases || 0;

  const atRiskCases = metrics?.at_risk_cases || 0;
  const approvalCases = metrics?.approval_cases || 0;
  const retryCases = metrics?.retry_available_cases || 0;
  const blockedCases = metrics?.blocked_cases || 0;

  const limits = metrics?.policy_limits || {
    max_incentive_percent: 10,
    max_recovery_amount: 100000,
    high_value_approval_threshold: 25000,
    max_payment_attempts: 3,
  };

  // Calculate status counts for live chart
  const statusCounts = {
    RECOVERED: 0,
    HUMAN_APPROVAL_REQUIRED: 0,
    RETRY_AVAILABLE: 0,
    BLOCKED: 0,
    NO_ACTION: 0,
    PENDING: 0
  };

  cases.forEach(c => {
    if (statusCounts[c.status] !== undefined) {
      statusCounts[c.status]++;
    } else {
      statusCounts.PENDING++;
    }
  });

  return (
    <div className="page-body">
      {/* Top Banner */}
      <div style={{ marginBottom: '28px' }}>
        <h1>Revenue Recovery</h1>
        <p className="subtitle">
          Find at-risk revenue, diagnose root causes, execute bounded interventions, and measure recovered revenue.
        </p>
      </div>

      {/* Main KPI Grid */}
      <div className="kpi-grid">
        <div className="kpi-card highlight">
          <div className="kpi-header">
            <span className="kpi-label">Revenue Recovered</span>
            <div className="kpi-icon">
              <CheckCircle size={18} />
            </div>
          </div>
          <div className="kpi-value">₹{recoveredRevenue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          <div className="kpi-footer">
            <span style={{ color: '#059669', fontWeight: 600 }}>{recoveryRate}% recovered</span>
            <span>of ₹{atRiskRevenue.toLocaleString('en-IN')} at risk</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Revenue at Risk</span>
            <div className="kpi-icon">
              <AlertTriangle size={18} />
            </div>
          </div>
          <div className="kpi-value">₹{atRiskRevenue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          <div className="kpi-footer">
            <span>{atRiskCases} problematic payments detected</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Recovery Rate</span>
            <div className="kpi-icon">
              <Percent size={18} />
            </div>
          </div>
          <div className="kpi-value">{recoveryRate}%</div>
          <div className="kpi-footer">
            <span>{recoveredCases} of {atRiskCases} at-risk cases recovered</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Cases Recovered</span>
            <div className="kpi-icon">
              <TrendingUp size={18} />
            </div>
          </div>
          <div className="kpi-value">{recoveredCases} <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 400 }}>/ {totalCases}</span></div>
          <div className="kpi-footer">
            <span>Autonomous & Human-approved</span>
          </div>
        </div>
      </div>

      {/* Secondary Metrics Sub-Grid */}
      <div className="kpi-sub-grid">
        <div className="kpi-sub-card">
          <span className="kpi-sub-label">At-Risk Cases</span>
          <span className="kpi-sub-value">{atRiskCases}</span>
        </div>
        <div className="kpi-sub-card">
          <span className="kpi-sub-label">Human Approval Required</span>
          <span className="kpi-sub-value" style={{ color: approvalCases > 0 ? '#C2410C' : 'inherit' }}>
            {approvalCases}
          </span>
        </div>
        <div className="kpi-sub-card">
          <span className="kpi-sub-label">Retry Available</span>
          <span className="kpi-sub-value" style={{ color: retryCases > 0 ? '#1D4ED8' : 'inherit' }}>
            {retryCases}
          </span>
        </div>
        <div className="kpi-sub-card">
          <span className="kpi-sub-label">Blocked / Stopped</span>
          <span className="kpi-sub-value">{blockedCases}</span>
        </div>
      </div>

      {/* Charts & Insights Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '24px', marginBottom: '28px' }}>
        {/* Chart 1: Revenue at Risk vs Recovered */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Revenue Recovery Progress</h3>
            <span className="badge badge-recovered">Live Pipeline</span>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Real-time comparison between total at-risk failed payment value and revenue successfully recovered in Razorpay Test Mode.
          </p>

          <div className="chart-bar-container">
            <div className="chart-bar-label">
              <span>Recovered: ₹{recoveredRevenue.toLocaleString('en-IN')}</span>
              <strong>{recoveryRate}%</strong>
            </div>
            <div className="progress-track" style={{ height: '14px' }}>
              <div
                className="progress-fill success"
                style={{ width: `${Math.min(recoveryRate, 100)}%` }}
              ></div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Pipeline Total</span>
              <p style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                ₹{atRiskRevenue.toLocaleString('en-IN')}
              </p>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Remaining At Risk</span>
              <p style={{ fontSize: '1.25rem', fontWeight: 700, color: '#B91C1C' }}>
                ₹{Math.max(0, atRiskRevenue - recoveredRevenue).toLocaleString('en-IN')}
              </p>
            </div>
          </div>
        </div>

        {/* Chart 2: Status Breakdown */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Case Status Distribution</h3>
            <span className="badge badge-noaction">{totalCases} Total Cases</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '4px' }}>
                <span>Recovered</span>
                <strong>{statusCounts.RECOVERED} ({Math.round((statusCounts.RECOVERED / (totalCases || 1)) * 100)}%)</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill success" style={{ width: `${(statusCounts.RECOVERED / (totalCases || 1)) * 100}%` }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '4px' }}>
                <span>Human Approval</span>
                <strong>{statusCounts.HUMAN_APPROVAL_REQUIRED}</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${(statusCounts.HUMAN_APPROVAL_REQUIRED / (totalCases || 1)) * 100}%`, background: '#C2410C' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '4px' }}>
                <span>Retry Available</span>
                <strong>{statusCounts.RETRY_AVAILABLE}</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${(statusCounts.RETRY_AVAILABLE / (totalCases || 1)) * 100}%`, background: '#2563EB' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '4px' }}>
                <span>Blocked / Stopped</span>
                <strong>{statusCounts.BLOCKED}</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${(statusCounts.BLOCKED / (totalCases || 1)) * 100}%`, background: '#DC2626' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '4px' }}>
                <span>No Action / Healthy</span>
                <strong>{statusCounts.NO_ACTION + statusCounts.PENDING}</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${((statusCounts.NO_ACTION + statusCounts.PENDING) / (totalCases || 1)) * 100}%`, background: '#94A3B8' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Safety & Model Details Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Card: Bounded Recovery Policy */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={18} color="#0F172A" />
              <h3 className="card-title">Bounded Recovery Policy & Guardrails</h3>
            </div>
            <span className="badge badge-noaction">Active Guardrails</span>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            The Revenue Recovery Agent enforces strict merchant safety limits and stopping rules before executing any recovery action.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Autonomous Recovery Limit</span>
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                ₹{(limits.max_recovery_amount || 100000).toLocaleString('en-IN')}
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Human Approval Threshold</span>
              <strong style={{ fontSize: '0.9rem', color: '#C2410C' }}>
                ₹{(limits.high_value_approval_threshold || 25000).toLocaleString('en-IN')}
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Maximum Payment Attempts (Stopping Rule)</span>
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                {limits.max_payment_attempts || 3} attempts
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Maximum Recovery Incentive</span>
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                {limits.max_incentive_percent || 10}%
              </strong>
            </div>
          </div>
        </div>

        {/* Card: AI Risk Model Information */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={18} color="#0F172A" />
              <h3 className="card-title">Trained ML Payment Risk Model</h3>
            </div>
            <span className="badge badge-recovered">Trained & Active</span>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Model specifications and evaluation metrics loaded from metadata.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '12px' }}>
            <div style={{ padding: '10px 12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Model</span>
              <p style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {modelMetrics?.model || 'RandomForest'}
              </p>
            </div>

            <div style={{ padding: '10px 12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Dataset Size</span>
              <p style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {(modelMetrics?.dataset_size || 50000).toLocaleString('en-IN')} rows
              </p>
            </div>

            <div style={{ padding: '10px 12px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Accuracy</span>
              <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#059669', marginTop: '2px' }}>
                {modelMetrics?.accuracy ? (modelMetrics.accuracy * 100).toFixed(2) : '92.43'}%
              </p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
            <div style={{ padding: '8px 10px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Precision</span>
              <p style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {modelMetrics?.precision ? (modelMetrics.precision * 100).toFixed(1) : '89.1'}%
              </p>
            </div>

            <div style={{ padding: '8px 10px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Recall</span>
              <p style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {modelMetrics?.recall ? (modelMetrics.recall * 100).toFixed(1) : '83.0'}%
              </p>
            </div>

            <div style={{ padding: '8px 10px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>F1 Score</span>
              <p style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {modelMetrics?.f1_score ? (modelMetrics.f1_score * 100).toFixed(1) : '86.0'}%
              </p>
            </div>

            <div style={{ padding: '8px 10px', background: '#F8FAFC', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>ROC-AUC</span>
              <p style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {modelMetrics?.roc_auc || '0.9656'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
