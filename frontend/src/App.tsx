// Main App - Invoice Processing Workflow Demo

import { useWorkflow, useServerHealth } from './hooks/useWorkflow';
import { Pipeline, InvoiceForm, HITLPanel, LogPanel, ServerHealth, Card, Button } from './components';

export default function App() {
  const { state, loading, submit, resolveHitl, reset } = useWorkflow();
  const health = useServerHealth();
  
  const isRunning = state.status === 'running';
  const isHitl = state.status === 'hitl';
  const isDone = state.status === 'done';

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">📄 Invoice Processing Workflow</h1>
            <p className="text-gray-500">LangGraph + MCP Demo</p>
          </div>
          <ServerHealth health={health} />
        </header>

        {/* Pipeline Visualization */}
        <Card title="Workflow Pipeline" icon="🔄">
          <Pipeline currentStage={state.currentStage} status={state.status} />
        </Card>

        {/* Main Content */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Left: Form or Status */}
          <div>
            {isDone ? (
              <Card className="bg-green-50 border-2 border-green-400">
                <div className="text-center py-8">
                  <span className="text-5xl">🎉</span>
                  <h3 className="text-xl font-bold text-green-700 mt-4">Workflow Complete!</h3>
                  <p className="text-green-600 mb-4">Invoice processed successfully</p>
                  <Button onClick={reset}>Process Another</Button>
                </div>
              </Card>
            ) : isHitl && state.hitlData ? (
              <HITLPanel
                reason={state.hitlData.reason}
                checkpointId={state.hitlData.checkpoint_id}
                onApprove={() => resolveHitl(true)}
                onReject={() => resolveHitl(false)}
                loading={loading}
              />
            ) : (
              <InvoiceForm onSubmit={submit} loading={loading} disabled={isRunning} />
            )}
          </div>

          {/* Right: Log */}
          <LogPanel logs={state.logs} />
        </div>

        {/* Footer */}
        <footer className="text-center text-sm text-gray-400">
          Servers: API (8000) • COMMON MCP (8001) • ATLAS MCP (8002)
        </footer>
      </div>
    </div>
  );
}
