import React from 'react';
import {
  Radar,
  Stethoscope,
  Compass,
  Scale,
  PlayCircle,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

const STEP_ICONS = {
  DETECT: Radar,
  DIAGNOSE: Stethoscope,
  DECIDE: Compass,
  POLICY: Scale,
  EXECUTE: PlayCircle,
  RESULT: CheckCircle2,
};

export default function DecisionFlow({ steps = [] }) {
  if (!steps || steps.length === 0) {
    return (
      <div className="alert-box alert-info">
        <AlertCircle size={16} />
        <span>No decision flow steps available. Run analysis to inspect agent reasoning.</span>
      </div>
    );
  }

  return (
    <div className="decision-flow-container">
      {steps.map((stepItem, index) => {
        const Icon = STEP_ICONS[stepItem.step] || AlertCircle;
        const isDone = stepItem.status === 'COMPLETED';
        const isCurrent = stepItem.status === 'IN_PROGRESS' || stepItem.status === 'PENDING';

        return (
          <div key={index} className="decision-flow-step">
            <div className={`step-indicator ${isDone ? 'completed' : isCurrent ? 'active' : ''}`}>
              <Icon size={16} />
            </div>

            <div className="step-card">
              <div className="step-header">
                <span className="step-name">{index + 1}. {stepItem.step} — {stepItem.title}</span>
                {stepItem.badge && (
                  <span className="badge badge-noaction">
                    {stepItem.badge}
                  </span>
                )}
              </div>
              <p className="step-desc">{stepItem.content}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
