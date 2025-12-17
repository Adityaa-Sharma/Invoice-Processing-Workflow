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
  status: 'success' | 'error' | 'info' | 'warning';
  time: string;
  details?: Record<string, unknown>;
}

export interface WorkflowState {
  workflowId: string | null;
  currentStage: string;
  status: 'idle' | 'running' | 'hitl' | 'done' | 'error';
  logs: LogEntry[];
  hitlData: { reason: string; checkpoint_id: string } | null;
  stageData: Record<string, unknown>;
}

// SSE Event types
interface SSEEvent {
  type: 'stage_update' | 'log' | 'connected' | 'heartbeat';
  thread_id: string;
  stage?: string;
  status?: string;
  data?: Record<string, unknown>;
  level?: string;
  message?: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

// Workflow hook with SSE support
export function useWorkflow() {
  const [state, setState] = useState<WorkflowState>({
    workflowId: null,
    currentStage: '',
    status: 'idle',
    logs: [],
    hitlData: null,
    stageData: {},
  });
  const [loading, setLoading] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const addLog = useCallback((stage: string, message: string, status: LogEntry['status'] = 'info', details?: Record<string, unknown>) => {
    setState((s: WorkflowState) => ({
      ...s,
      logs: [...s.logs, { stage, message, status, time: new Date().toLocaleTimeString(), details }],
    }));
  }, []);

  // Connect to SSE for real-time updates
  const connectSSE = useCallback((threadId: string) => {
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    console.log(`🔌 Connecting to SSE for thread: ${threadId}`);
    const eventSource = new EventSource(`${API}/events/workflow/${threadId}`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('✅ SSE connection opened');
    };

    eventSource.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);
        console.log('📡 SSE Event:', data);

        if (data.type === 'connected') {
          addLog('SSE', 'Connected to real-time updates', 'info');
          return;
        }

        if (data.type === 'heartbeat') {
          // Ignore heartbeats
          return;
        }

        if (data.type === 'log') {
          const logStatus = data.level === 'error' ? 'error' : 
                           data.level === 'warning' ? 'warning' : 'info';
          addLog(data.stage || 'SYSTEM', data.message || '', logStatus, data.details);
          return;
        }

        if (data.type === 'stage_update') {
          const stage = data.stage || '';
          const stageStatus = data.status || '';

          setState((s: WorkflowState) => {
            const newState = { ...s };

            // Update current stage
            if (stageStatus === 'started') {
              newState.currentStage = stage;
              newState.status = 'running';
            }

            // Store stage data
            if (stageStatus === 'completed' && data.data) {
              newState.stageData = { ...s.stageData, [stage]: data.data };
            }

            // Handle workflow completion
            if (stageStatus === 'workflow_complete') {
              const finalStatus = data.data?.final_status;
              if (finalStatus === 'COMPLETED') {
                newState.status = 'done';
              } else if (finalStatus === 'REQUIRES_MANUAL_HANDLING') {
                newState.status = 'error';
              }
              // Close SSE connection
              eventSource.close();
            }

            // Handle paused for HITL
            if (stage === 'CHECKPOINT_HITL' && stageStatus === 'completed') {
              newState.status = 'hitl';
              newState.hitlData = {
                reason: 'Match failed - manual review required',
                checkpoint_id: (data.data?.checkpoint_id as string) || '',
              };
            }

            return newState;
          });

          // Add log for stage events
          if (stageStatus === 'started') {
            addLog(stage, `▶️ Starting ${stage}...`, 'info');
          } else if (stageStatus === 'completed') {
            addLog(stage, `✅ ${stage} completed`, 'success', data.data);
          } else if (stageStatus === 'failed') {
            addLog(stage, `❌ ${stage} failed: ${data.data?.error}`, 'error');
          }
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      // Don't add error log for normal closure
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('SSE connection closed');
      } else {
        addLog('SSE', 'Connection error - falling back to polling', 'warning');
        eventSource.close();
        // Fallback to polling
        pollStatus(threadId);
      }
    };

    return eventSource;
  }, [addLog]);

  const submit = useCallback(async (invoice: Invoice) => {
    setLoading(true);
    setState((s: WorkflowState) => ({ 
      ...s, 
      logs: [], 
      status: 'running', 
      hitlData: null,
      stageData: {},
      currentStage: '',
    }));
    addLog('SUBMIT', `🚀 Submitting invoice for ${invoice.vendor_name}`, 'info');

    try {
      const res = await fetch(`${API}/invoice/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invoice),
      });
      const data = await res.json();
      
      if (data.thread_id) {
        setState((s: WorkflowState) => ({ ...s, workflowId: data.thread_id }));
        addLog('SUBMIT', `✅ Workflow started: ${data.thread_id}`, 'success');
        
        // Connect to SSE for real-time updates
        connectSSE(data.thread_id);
      } else {
        throw new Error(data.detail || data.message || 'Failed to start workflow');
      }
    } catch (err) {
      addLog('ERROR', String(err), 'error');
      setState((s: WorkflowState) => ({ ...s, status: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [addLog, connectSSE]);

  // Fallback polling (used if SSE fails)
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
          addLog('COMPLETE', '🎉 Workflow completed successfully!', 'success');
          return;
        }

        // Continue polling
        setTimeout(() => poll(), 1000);
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
        addLog('HITL', approved ? '✅ Approved by reviewer' : '❌ Rejected by reviewer', approved ? 'success' : 'error');
        setState((s: WorkflowState) => ({ ...s, status: 'running', hitlData: null }));
        // Reconnect SSE for continued updates
        if (state.workflowId) connectSSE(state.workflowId);
      }
    } catch (err) {
      addLog('ERROR', String(err), 'error');
    } finally {
      setLoading(false);
    }
  }, [state.hitlData, state.workflowId, addLog, connectSSE]);

  const reset = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setState({ workflowId: null, currentStage: '', status: 'idle', logs: [], hitlData: null, stageData: {} });
  }, []);

  useEffect(() => {
    return () => { 
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
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
