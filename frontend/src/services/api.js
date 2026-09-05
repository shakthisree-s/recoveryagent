const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL) 
  ? import.meta.env.VITE_API_URL 
  : '/api';

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
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse(res);
  },

  async getCases() {
    const res = await fetch(`${API_BASE_URL}/cases`);
    return handleResponse(res);
  },

  async getCaseDetail(caseId) {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}`);
    return handleResponse(res);
  },

  async analyzeCase(caseId) {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  },

  async recoverCase(caseId, simulateFailure = false) {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/recover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulate_failure: simulateFailure }),
    });
    return handleResponse(res);
  },

  async retryCase(caseId) {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  },

  async approveCase(caseId, notes = '') {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    return handleResponse(res);
  },

  async rejectCase(caseId) {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  },

  async runBatch() {
    const res = await fetch(`${API_BASE_URL}/batch/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  },

  async getMetrics() {
    const res = await fetch(`${API_BASE_URL}/metrics`);
    return handleResponse(res);
  },

  async getModelMetrics() {
    const res = await fetch(`${API_BASE_URL}/model/metrics`);
    return handleResponse(res);
  },

  async getAuditLogs(status = 'ALL', caseId = null) {
    const params = new URLSearchParams();
    if (status && status !== 'ALL') params.append('status', status);
    if (caseId) params.append('case_id', caseId);

    const url = `${API_BASE_URL}/audit${params.toString() ? `?${params.toString()}` : ''}`;
    const res = await fetch(url);
    return handleResponse(res);
  },

  async getCaseAudit(caseId) {
    const res = await fetch(`${API_BASE_URL}/audit/${caseId}`);
    return handleResponse(res);
  },

  async resetState() {
    const res = await fetch(`${API_BASE_URL}/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(res);
  }
};
