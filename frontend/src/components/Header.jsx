import React from 'react';
import { Play, RotateCcw, Activity } from 'lucide-react';

export default function Header({ onRunBatch, isRunningBatch, onResetDemo }) {
  return (
    <header className="top-header">
      <div className="header-left">
        <div>
          <h2>Revenue Recovery</h2>
          <p className="subtitle">AI-powered recovery operations for at-risk payments</p>
        </div>
      </div>

      <div className="header-right">
        <div className="test-mode-badge" title="Simulated environment - no real money movement">
          <span className="status-dot"></span>
          <span>RAZORPAY TEST MODE</span>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onResetDemo}
          title="Reset benchmark cases to initial demo state"
        >
          <RotateCcw size={14} />
          <span>Reset Demo</span>
        </button>

        <button
          className="btn btn-primary"
          onClick={onRunBatch}
          disabled={isRunningBatch}
        >
          {isRunningBatch ? (
            <>
              <Activity size={16} className="animate-spin" />
              <span>Running Batch...</span>
            </>
          ) : (
            <>
              <Play size={16} fill="currentColor" />
              <span>Run Recovery Batch</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}
