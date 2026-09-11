const RAW_API_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL) 
  ? import.meta.env.VITE_API_URL 
  : "http://127.0.0.1:8001";

// Normalizes base URL (handles with or without trailing slash/api)
const API_BASE_URL = RAW_API_URL.replace(/\/+$/, '').replace(/\/api$/, '');

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = 'Network response was not ok';
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // keep fallback error
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    return handleResponse(res);
  },

  async getCases() {
    const res = await fetch(`${API_BASE_URL}/api/cases`);
    const data = await handleResponse(res);
    return Array.isArray(data) ? data : (data?.cases || []);
  },

  async getCaseDetail(caseId) {
    const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}`);
    return handleResponse(res);
  },

  async analyzeCase(caseId) {
    const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  },

  async recoverCase(caseId, simulateFailure = false) {
    const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/recover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate_failure: simulateFailure }),
    });
    return handleResponse(res);
  },

  async retryCase(caseId) {
    const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  },

  async approveCase(caseId, notes = '') {
    const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    return handleResponse(res);
  },

  async rejectCase(caseId, notes = '') {
    const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    return handleResponse(res);
  },

  async runBatch() {
    const res = await fetch(`${API_BASE_URL}/api/batch/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  },

  async getMetrics() {
    const res = await fetch(`${API_BASE_URL}/api/metrics`);
    return handleResponse(res);
  },

  async getModelMetrics() {
    const res = await fetch(`${API_BASE_URL}/api/model/metrics`);
    return handleResponse(res);
  },

  async getAuditLogs(status = 'ALL', caseId = null) {
    const params = new URLSearchParams();
    if (status && status !== 'ALL') params.append('status', status);
    if (caseId) params.append('case_id', caseId);

    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE_URL}/api/audit${query}`);
    const data = await handleResponse(res);
    return Array.isArray(data) ? data : (data?.audit_logs || []);
  },

  async getCaseAudit(caseId) {
    const res = await fetch(`${API_BASE_URL}/api/audit/${caseId}`);
    const data = await handleResponse(res);
    return Array.isArray(data) ? data : (data?.audit_logs || []);
  },

  async resetState() {
    const res = await fetch(`${API_BASE_URL}/api/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  }
};
