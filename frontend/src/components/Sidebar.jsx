import React from 'react';
import {
  LayoutDashboard,
  FileSpreadsheet,
  Zap,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, metrics }) {
  const navItems = [
    {
      id: 'overview',
      label: 'Overview',
      icon: LayoutDashboard,
    },
    {
      id: 'cases',
      label: 'Recovery Cases',
      icon: FileSpreadsheet,
      badge: metrics?.total_cases || 8,
    },
    {
      id: 'batch',
      label: 'Batch Results',
      icon: Zap,
    },
    {
      id: 'audit',
      label: 'Audit Trail',
      icon: ShieldCheck,
    },
  ];

  const limits = metrics?.policy_limits || {
    max_recovery_amount: 100000,
    high_value_approval_threshold: 25000,
    max_payment_attempts: 3,
  };

  return (
    <aside className="sidebar">
      <div className="brand-section">
        <div className="brand-icon">
          <ShieldAlert size={20} />
        </div>
        <div className="brand-info">
          <h2>Revenue Recovery</h2>
          <span>Autonomous Operations</span>
        </div>
      </div>

      <nav className="nav-menu">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <div className="nav-item-content">
                <Icon size={18} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span className="nav-badge">{item.badge}</span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="policy-mini-box">
          <h5>Bounded Autonomy</h5>
          <div className="policy-mini-item">
            <span>Max Recovery:</span>
            <strong>₹{(limits.max_recovery_amount || 100000).toLocaleString('en-IN')}</strong>
          </div>
          <div className="policy-mini-item">
            <span>Human Threshold:</span>
            <strong>₹{(limits.high_value_approval_threshold || 25000).toLocaleString('en-IN')}</strong>
          </div>
          <div className="policy-mini-item">
            <span>Max Retry Attempts:</span>
            <strong>{limits.max_payment_attempts || 3}</strong>
          </div>
          <div className="policy-mini-item">
            <span>Max Incentive:</span>
            <strong>{limits.max_incentive_percent || 10}%</strong>
          </div>
        </div>
      </div>
    </aside>
  );
}
