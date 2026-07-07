import React from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./index.css";
import App from "./App";

interface ErrorBoundaryState {
  error: Error | null;
}

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, maxWidth: 720, margin: "0 auto" }}>
          <h2>Algo deu errado ao exibir a aplicação.</h2>
          <p className="muted">
            Recarregue a página. Se o problema persistir, verifique se a API está no ar.
          </p>
          <details style={{ marginTop: 12 }}>
            <summary>{this.state.error.message || String(this.state.error)}</summary>
            <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, opacity: 0.8 }}>
              {this.state.error.stack}
            </pre>
          </details>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
