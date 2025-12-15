// Custom hooks for workflow state management

import { useState, useCallback, useEffect, useRef } from 'react';

const API = 'http://localhost:8000';

// Types
export interface Invoice {
  vendor_name: string;
  amount: number;
  currency: string;
  po_number?: string;
}

export interface LogEntry {
  stage: string;
  message: string;
  status: 'success' | 'error' | 'info';
  time: string;
}

export interface WorkflowState {
  workflowId: string | null;
  currentStage: string;
  status: 'idle' | 'running' | 'hitl' | 'done' | 'error';
  logs: LogEntry[];
  hitlData: { reason: string; checkpoint_id: string } | null;
}

// Workflow hook
export function useWorkflow() {
  const [state, setState] = useState<WorkflowState>({
    workflowId: null,
    currentStage: '',
    status: 'idle',
    logs: [],
    hitlData: null,
  });
  const [loading, setLoading] = useState(false);
  const pollRef = useRef<number>();

  const addLog = useCallback((stage: string, message: string, status: LogEntry['status'] = 'info') => {
    setState((s: WorkflowState) => ({
      ...s,
      logs: [...s.logs, { stage, message, status, time: new Date().toLocaleTimeString() }],
    }));
  }, []);

  const submit = useCallback(async (invoice: Invoice) => {
    setLoading(true);
    setState((s: WorkflowState) => ({ ...s, logs: [], status: 'running', hitlData: null }));
    addLog('SUBMIT', `Submitting invoice for ${invoice.vendor_name}`, 'info');

    try {
      const res = await fetch(`${API}/api/v1/invoices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invoice),
      });
      const data = await res.json();
      
      if (data.workflow_id) {
        setState((s: WorkflowState) => ({ ...s, workflowId: data.workflow_id }));
        addLog('SUBMIT', `Workflow started: ${data.workflow_id}`, 'success');
        pollStatus(data.workflow_id);
      } else {
        throw new Error(data.detail || 'Failed to start workflow');
      }
    } catch (err) {
      addLog('ERROR', String(err), 'error');
      setState((s: WorkflowState) => ({ ...s, status: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [addLog]);

  const pollStatus = useCallback(async (wfId: string) => {
    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/v1/workflow/${wfId}/status`);
        const data = await res.json();
        
        setState((s: WorkflowState) => {
          // Add log if stage changed
          if (data.current_stage && data.current_stage !== s.currentStage) {
            const newLogs = [...s.logs, {
              stage: data.current_stage,
              message: `Processing ${data.current_stage}`,
              status: 'success' as const,
              time: new Date().toLocaleTimeString(),
            }];
            return { ...s, currentStage: data.current_stage, logs: newLogs };
          }
          return { ...s, currentStage: data.current_stage || s.currentStage };
        });

        // Check for HITL
        if (data.hitl_required || data.status === 'interrupted') {
          setState((s: WorkflowState) => ({
            ...s,
            status: 'hitl',
            hitlData: { reason: data.hitl_reason || 'Manual review required', checkpoint_id: data.hitl_checkpoint_id },
          }));
          return;
        }

        // Check completion
        if (data.status === 'completed' || data.current_stage === 'COMPLETE') {
          setState((s: WorkflowState) => ({ ...s, status: 'done' }));
          addLog('COMPLETE', 'Workflow completed successfully!', 'success');
          return;
        }

        // Continue polling
        pollRef.current = window.setTimeout(() => poll(), 1000);
      } catch (err) {
        addLog('ERROR', `Poll error: ${err}`, 'error');
      }
    };
    poll();
  }, [addLog]);

  const resolveHitl = useCallback(async (approved: boolean) => {
    if (!state.hitlData?.checkpoint_id) return;
    setLoading(true);
    
    try {
      const res = await fetch(`${API}/api/v1/human-review/${state.hitlData.checkpoint_id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved, decision: approved ? 'approve' : 'reject' }),
      });
      
      if (res.ok) {
        addLog('HITL', approved ? 'Approved by reviewer' : 'Rejected by reviewer', approved ? 'success' : 'error');
        setState((s: WorkflowState) => ({ ...s, status: 'running', hitlData: null }));
        if (state.workflowId) pollStatus(state.workflowId);
      }
    } catch (err) {
      addLog('ERROR', String(err), 'error');
    } finally {
      setLoading(false);
    }
  }, [state.hitlData, state.workflowId, addLog, pollStatus]);

  const reset = useCallback(() => {
    if (pollRef.current) clearTimeout(pollRef.current);
    setState({ workflowId: null, currentStage: '', status: 'idle', logs: [], hitlData: null });
  }, []);

  useEffect(() => {
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, []);

  return { state, loading, submit, resolveHitl, reset };
}

// Server health hook
export function useServerHealth() {
  const [health, setHealth] = useState({ api: false, common: false, atlas: false });

  useEffect(() => {
    const check = async () => {
      const checkServer = async (url: string) => {
        try {
          const res = await fetch(url, { method: 'GET' });
          return res.ok;
        } catch { return false; }
      };

      setHealth({
        api: await checkServer(`${API}/health`),
        common: await checkServer('http://localhost:8001/health'),
        atlas: await checkServer('http://localhost:8002/health'),
      });
    };
    
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  return health;
}
