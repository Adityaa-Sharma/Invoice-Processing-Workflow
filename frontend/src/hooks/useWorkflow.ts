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
  logType?: 'info' | 'tool_call' | 'tool_selection' | 'tool_result' | 'result' | 'decision' | 'warning' | 'error' | 'hitl' | 'success';
  eventId?: string; // Unique ID for deduplication
}

export interface ToolCallEntry {
  stage: string;
  toolName: string;
  server: string;
  status: 'started' | 'completed' | 'failed';
  params?: Record<string, unknown>;
  result?: Record<string, unknown>;
  time: string;
  eventId?: string; // Unique ID for deduplication
}

export interface WorkflowState {
  workflowId: string | null;
  currentStage: string;
  status: 'idle' | 'running' | 'hitl' | 'done' | 'error';
  logs: LogEntry[];
  toolCalls: ToolCallEntry[];
  hitlData: { reason: string; checkpoint_id: string } | null;
  hitlResolved: boolean; // Track if HITL was already resolved (to prevent replay)
  stageData: Record<string, unknown>;
}

// SSE Event types
interface SSEEvent {
  type: 'stage_update' | 'log' | 'tool_call' | 'connected' | 'heartbeat';
  thread_id: string;
  stage?: string;
  status?: string;
  data?: Record<string, unknown>;
  level?: string;
  message?: string;
  details?: Record<string, unknown>;
  log_type?: string;
  tool_name?: string;
  server?: string;
  params?: Record<string, unknown>;
  result?: Record<string, unknown>;
  timestamp: string;
}

// Workflow hook with SSE support
export function useWorkflow() {
  const [state, setState] = useState<WorkflowState>({
    workflowId: null,
    currentStage: '',
    status: 'idle',
    logs: [],
    toolCalls: [],
    hitlData: null,
    hitlResolved: false,
    stageData: {},
  });
  const [loading, setLoading] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const seenEventIds = useRef<Set<string>>(new Set()); // Track seen events for deduplication

  // Helper to format timestamp from ISO string
  const formatTime = (isoTimestamp?: string): string => {
    if (!isoTimestamp) return new Date().toLocaleTimeString();
    try {
      return new Date(isoTimestamp).toLocaleTimeString();
    } catch {
      return new Date().toLocaleTimeString();
    }
  };

  // Generate event ID from event data for deduplication
  const getEventId = (data: SSEEvent): string => {
    // Use original timestamp + type + stage + message/tool as unique key
    return `${data.timestamp}-${data.type}-${data.stage || ''}-${data.message || data.tool_name || data.status || ''}`;
  };

  const addLog = useCallback((stage: string, message: string, status: LogEntry['status'] = 'info', details?: Record<string, unknown>, logType?: LogEntry['logType'], eventId?: string, time?: string) => {
    setState((s: WorkflowState) => {
      // Check for duplicate by eventId
      if (eventId && s.logs.some(log => log.eventId === eventId)) {
        return s; // Skip duplicate
      }
      return {
        ...s,
        logs: [...s.logs, { stage, message, status, time: time || new Date().toLocaleTimeString(), details, logType, eventId }],
      };
    });
  }, []);

  const addToolCall = useCallback((toolCall: ToolCallEntry) => {
    setState((s: WorkflowState) => {
      // Check for duplicate by eventId
      if (toolCall.eventId && s.toolCalls.some(tc => tc.eventId === toolCall.eventId)) {
        return s; // Skip duplicate
      }
      return {
        ...s,
        toolCalls: [...s.toolCalls, toolCall],
      };
    });
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

        // Generate unique event ID for deduplication
        const eventId = getEventId(data);
        
        // Skip if we've already processed this event
        if (seenEventIds.current.has(eventId)) {
          console.log('⏭️ Skipping duplicate event:', eventId);
          return;
        }
        seenEventIds.current.add(eventId);

        if (data.type === 'connected') {
          addLog('SSE', 'Connected to real-time updates', 'info', undefined, 'info', eventId, formatTime(data.timestamp));
          return;
        }

        if (data.type === 'heartbeat') {
          // Ignore heartbeats
          return;
        }

        if (data.type === 'tool_call') {
          // Handle tool call events
          const toolCall: ToolCallEntry = {
            stage: data.stage || 'SYSTEM',
            toolName: data.tool_name || 'unknown',
            server: data.server || 'UNKNOWN',
            status: data.status as 'started' | 'completed' | 'failed',
            params: data.params,
            result: data.result,
            time: formatTime(data.timestamp),
            eventId,
          };
          addToolCall(toolCall);
          
          // Also add as log entry for visibility
          const emoji = data.status === 'started' ? '🔧' : data.status === 'completed' ? '✅' : '❌';
          const logStatus = data.status === 'failed' ? 'error' : 'info';
          addLog(
            data.stage || 'SYSTEM',
            `${emoji} Tool: ${data.tool_name}@${data.server} → ${data.status}`,
            logStatus as LogEntry['status'],
            { params: data.params, result: data.result },
            'tool_call',
            `${eventId}-log`,
            formatTime(data.timestamp)
          );
          return;
        }

        if (data.type === 'log') {
          const logStatus = data.level === 'error' ? 'error' : 
                           data.level === 'warning' ? 'warning' : 'info';
          addLog(data.stage || 'SYSTEM', data.message || '', logStatus, data.details, data.log_type as LogEntry['logType'], eventId, formatTime(data.timestamp));
          return;
        }

        if (data.type === 'stage_update') {
          const stage = data.stage || '';
          const stageStatus = data.status || '';
          
          // Debug logging
          console.log(`📊 Stage update: ${stage} → ${stageStatus}`);

          // Add log entry for stage start/complete
          if (stageStatus === 'started') {
            addLog(stage, `▶️ Starting ${stage}...`, 'info', data.data as Record<string, unknown>, 'info', eventId, formatTime(data.timestamp));
          } else if (stageStatus === 'completed') {
            addLog(stage, `✅ ${stage} completed`, 'success', data.data as Record<string, unknown>, 'result', eventId, formatTime(data.timestamp));
          } else if (stageStatus === 'failed') {
            addLog(stage, `❌ ${stage} failed`, 'error', data.data as Record<string, unknown>, 'error', eventId, formatTime(data.timestamp));
          }

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

            // Handle workflow completion - check workflow_complete, COMPLETE stage, or MANUAL_HANDOFF
            if (stageStatus === 'workflow_complete' || 
                (stage === 'COMPLETE' && stageStatus === 'completed') ||
                (stage === 'MANUAL_HANDOFF' && stageStatus === 'completed')) {
              const finalStatus = data.data?.final_status || data.data?.status || 'COMPLETED';
              if (finalStatus === 'COMPLETED') {
                newState.status = 'done';
                newState.currentStage = 'COMPLETE';
              } else if (finalStatus === 'REQUIRES_MANUAL_HANDLING') {
                newState.status = 'error';
                newState.currentStage = 'MANUAL_HANDOFF';
              }
              // Close SSE connection
              eventSource.close();
            }

            // Handle paused for HITL - but skip if already resolved
            if (stage === 'CHECKPOINT_HITL' && stageStatus === 'completed' && !s.hitlResolved) {
              newState.status = 'hitl';
              newState.hitlData = {
                reason: 'Match failed - manual review required',
                checkpoint_id: (data.data?.checkpoint_id as string) || '',
              };
            }
            
            // If HITL_DECISION stage starts or completes, mark as resolved
            if (stage === 'HITL_DECISION' && (stageStatus === 'started' || stageStatus === 'completed')) {
              newState.hitlResolved = true;
              newState.status = 'running';
              newState.hitlData = null;
            }

            return newState;
          });
          // Note: Stage logs are added above with proper eventId deduplication
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
  }, [addLog, addToolCall]);

  const submit = useCallback(async (invoice: Invoice) => {
    setLoading(true);
    // Reset seen events for new workflow
    seenEventIds.current.clear();
    setState((s: WorkflowState) => ({ 
      ...s, 
      logs: [], 
      toolCalls: [],
      status: 'running', 
      hitlData: null,
      hitlResolved: false, // Reset for new workflow
      stageData: {},
      currentStage: '',
    }));
    addLog('SUBMIT', `🚀 Submitting invoice for ${invoice.vendor_name}`, 'info', undefined, 'info');

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
        // Mark HITL as resolved to prevent replay showing HITL UI again
        setState((s: WorkflowState) => ({ ...s, status: 'running', hitlData: null, hitlResolved: true }));
        // Wait a moment for backend to start resumed workflow, then reconnect SSE
        if (state.workflowId) {
          addLog('HITL_DECISION', '🔄 Resuming workflow...', 'info');
          setTimeout(() => connectSSE(state.workflowId!), 600);
        }
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
    setState({ workflowId: null, currentStage: '', status: 'idle', logs: [], toolCalls: [], hitlData: null, hitlResolved: false, stageData: {} });
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
