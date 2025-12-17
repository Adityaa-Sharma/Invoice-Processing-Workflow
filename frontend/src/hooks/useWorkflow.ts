// Custom hooks for workflow state management

import { useState, useCallback, useEffect, useRef } from 'react';

const API = 'http://localhost:8000';

// Types
export interface LineItem {
  desc: string;
  qty: number;
  unit_price: number;
  total: number;
}

export interface Invoice {
  invoice_id: string;
  vendor_name: string;
  vendor_tax_id?: string;
  invoice_date: string;
  due_date: string;
  amount: number;
  currency: string;
  line_items: LineItem[];
  attachments?: string[];
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
      const res = await fetch(`${API}/invoice/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invoice),
      });
      const data = await res.json();
      
      if (data.thread_id) {
        setState((s: WorkflowState) => ({ ...s, workflowId: data.thread_id }));
        addLog('SUBMIT', `Workflow started: ${data.thread_id}`, 'success');
        pollStatus(data.thread_id);
      } else {
        throw new Error(data.detail || data.message || 'Failed to start workflow');
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
        const res = await fetch(`${API}/workflow/status/${wfId}`);
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

        // Check for HITL (using backend response format)
        if (data.requires_human_review || data.status === 'PAUSED') {
          setState((s: WorkflowState) => ({
            ...s,
            status: 'hitl',
            hitlData: { 
              reason: data.match_result || 'Manual review required', 
              checkpoint_id: data.checkpoint_id 
            },
          }));
          return;
        }

        // Check completion
        if (data.status === 'COMPLETED' || data.current_stage === 'COMPLETE') {
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
    if (!state.hitlData?.checkpoint_id || !state.workflowId) return;
    setLoading(true);
    
    try {
      const res = await fetch(`${API}/human-review/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          thread_id: state.workflowId,
          checkpoint_id: state.hitlData.checkpoint_id,
          decision: approved ? 'ACCEPT' : 'REJECT',
          notes: approved ? 'Approved via UI' : 'Rejected via UI',
          reviewer_id: 'frontend-user'
        }),
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
