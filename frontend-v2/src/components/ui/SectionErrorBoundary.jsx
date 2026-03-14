import { Component } from 'react';

class SectionErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error(`[${this.props.name || 'Section'}] Error:`, error, errorInfo);
    // Report to backend if available
    try {
      fetch('/api/v1/system/frontend-errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          component: this.props.name || 'unknown',
          error: error.message,
          stack: error.stack?.slice(0, 500),
          timestamp: new Date().toISOString(),
        }),
      }).catch(() => {});
    } catch {}
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 text-center">
          <p className="text-red-400 font-medium text-sm">
            {this.props.name || 'Section'} encountered an error
          </p>
          <p className="text-gray-500 text-xs mt-1 font-mono">
            {this.state.error?.message?.slice(0, 100)}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-2 px-3 py-1 text-xs bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded transition-colors"
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default SectionErrorBoundary;
