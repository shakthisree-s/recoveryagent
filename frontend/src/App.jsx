import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Overview from './components/Overview';
import RecoveryCases from './components/RecoveryCases';
import CaseDetailModal from './components/CaseDetailModal';
import BatchResults from './components/BatchResults';
import AuditTrail from './components/AuditTrail';
import { api } from './services/api';
import { CheckCircle2, AlertCircle } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [cases, setCases] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [batchData, setBatchData] = useState(null);

  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [caseDetail, setCaseDetail] = useState(null);

  const [isLoading, setIsLoading] = useState(false);
  const [isRunningBatch, setIsRunningBatch] = useState(false);
  const [toast, setToast] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  const refreshAll = async () => {
    try {
      const [casesData, metricsData, modelData, auditData] = await Promise.all([
        api.getCases(),
        api.getMetrics(),
        api.getModelMetrics(),
        api.getAuditLogs('ALL'),
      ]);
      setCases(casesData);
      setMetrics(metricsData);
      setModelMetrics(modelData);
      setAuditLogs(auditData);
      setLoadError(null);

      if (selectedCaseId) {
        const detail = await api.getCaseDetail(selectedCaseId);
        setCaseDetail(detail);
      }
    } catch (err) {
      console.error('Failed to refresh data:', err);
      // Never silently render zeros: surface the failure to every page.
      setLoadError(err?.message || 'Unable to reach the Revenue Recovery API.');
    }
  };

  useEffect(() => {
    refreshAll();
  }, []);

  const handleSelectCase = async (caseId) => {
    setIsLoading(true);
    setSelectedCaseId(caseId);
    try {
      const detail = await api.getCaseDetail(caseId);
      setCaseDetail(detail);
    } catch (err) {
      showToast(`Error loading case: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedCaseId(null);
    setCaseDetail(null);
  };

  const handleRunBatch = async () => {
    setIsRunningBatch(true);
    try {
      const res = await api.runBatch();
      setBatchData(res);
      await refreshAll();
      showToast(`Recovery batch completed. ₹${res.total_revenue_recovered.toLocaleString('en-IN')} recovered safely!`);
      setActiveTab('batch');
    } catch (err) {
      showToast(`Batch execution failed: ${err.message}`, 'error');
    } finally {
      setIsRunningBatch(false);
    }
  };

  const handleRecoverCase = async (caseId, simulateFailure = false) => {
    setIsLoading(true);
    try {
      const res = await api.recoverCase(caseId, simulateFailure);
      await refreshAll();
      const updatedDetail = await api.getCaseDetail(caseId);
      setCaseDetail(updatedDetail);
      if (res.status === 'RETRY_AVAILABLE') {
        showToast(`Recovery attempt failed (Simulated). Retry is now available for Case #${caseId}.`, 'info');
      } else {
        showToast(`Case #${caseId} recovered successfully! ₹${res.recovered_amount.toLocaleString('en-IN')} settled.`);
      }
    } catch (err) {
      showToast(`Recovery action failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetryCase = async (caseId) => {
    setIsLoading(true);
    try {
      const res = await api.retryCase(caseId);
      await refreshAll();
      const updatedDetail = await api.getCaseDetail(caseId);
      setCaseDetail(updatedDetail);
      showToast(`Retry succeeded! ₹${res.recovered_amount.toLocaleString('en-IN')} recovered on Attempt 2.`);
    } catch (err) {
      showToast(`Retry failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveCase = async (caseId, notes = '') => {
    setIsLoading(true);
    try {
      const res = await api.approveCase(caseId, notes);
      await refreshAll();
      const updatedDetail = await api.getCaseDetail(caseId);
      setCaseDetail(updatedDetail);
      showToast(`Human approval granted for Case #${caseId}! ₹${res.recovered_amount.toLocaleString('en-IN')} recovered.`);
    } catch (err) {
      showToast(`Approval failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRejectCase = async (caseId, notes = '') => {
    setIsLoading(true);
    try {
      await api.rejectCase(caseId, notes);
      await refreshAll();
      const updatedDetail = await api.getCaseDetail(caseId);
      setCaseDetail(updatedDetail);
      showToast(`Case #${caseId} rejected. Transaction recovery blocked.`, 'info');
    } catch (err) {
      showToast(`Rejection failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyzeCase = async (caseId) => {
    setIsLoading(true);
    try {
      await api.analyzeCase(caseId);
      const updatedDetail = await api.getCaseDetail(caseId);
      setCaseDetail(updatedDetail);
      showToast(`Case #${caseId} analyzed by RevenueRecoveryAgent.`);
    } catch (err) {
      showToast(`Analysis failed: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetDemo = async () => {
    try {
      await api.resetState();
      await refreshAll();
      setBatchData(null);
      if (selectedCaseId) handleCloseModal();
      showToast('Demo benchmark cases reset to initial state.');
    } catch (err) {
      showToast(`Reset failed: ${err.message}`, 'error');
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        metrics={metrics}
      />

      <div className="main-content">
        <Header
          onRunBatch={handleRunBatch}
          isRunningBatch={isRunningBatch}
          onResetDemo={handleResetDemo}
        />

        {activeTab === 'overview' && (
          <Overview
            metrics={metrics}
            modelMetrics={modelMetrics}
            cases={cases}
            loadError={loadError}
            onOpenCase={handleSelectCase}
          />
        )}

        {activeTab === 'cases' && (
          <RecoveryCases
            cases={cases}
            onSelectCase={handleSelectCase}
            onRecover={handleRecoverCase}
            onRetry={handleRetryCase}
            onApprove={handleApproveCase}
          />
        )}

        {activeTab === 'batch' && (
          <BatchResults
            batchData={batchData}
            onRunBatch={handleRunBatch}
            isRunningBatch={isRunningBatch}
            onSelectCase={handleSelectCase}
          />
        )}

        {activeTab === 'audit' && (
          <AuditTrail
            auditLogs={auditLogs}
            onSelectCase={handleSelectCase}
          />
        )}
      </div>

      {/* Case Detail Modal / Drawer */}
      {selectedCaseId && (
        <CaseDetailModal
          caseDetail={caseDetail}
          onClose={handleCloseModal}
          onAnalyze={handleAnalyzeCase}
          onRecover={handleRecoverCase}
          onRetry={handleRetryCase}
          onApprove={handleApproveCase}
          onReject={handleRejectCase}
          isLoading={isLoading}
        />
      )}

      {/* Toast notifications */}
      {toast && (
        <div className="toast-container">
          <div className="toast">
            {toast.type === 'error' ? (
              <AlertCircle size={18} color="#EF4444" />
            ) : (
              <CheckCircle2 size={18} color="#10B981" />
            )}
            <span>{toast.message}</span>
          </div>
        </div>
      )}
    </div>
  );
}
