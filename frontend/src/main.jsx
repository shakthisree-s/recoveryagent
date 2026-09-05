import React, { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Dashboard caught error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px', fontFamily: 'sans-serif', maxWidth: '800px', margin: '40px auto', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
          <h2 style={{ color: '#B91C1C', marginBottom: '12px' }}>Dashboard Error</h2>
          <p style={{ color: '#475569', marginBottom: '16px' }}>{this.state.error?.toString()}</p>
          <pre style={{ background: '#F8FAFC', padding: '16px', borderRadius: '4px', overflowX: 'auto', fontSize: '12px', color: '#64748B' }}>
            {this.state.errorInfo?.componentStack || this.state.error?.stack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: '16px', padding: '8px 16px', background: '#0F172A', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
          >
            Reload Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)

