// Workflow stage configuration and types
// Based on the LangGraph Invoice Processing workflow documentation

export const STAGES = [
  { id: 'INTAKE', name: 'Intake', icon: '📥', desc: 'Accept & validate invoice payload' },
  { id: 'UNDERSTAND', name: 'Understand', icon: '🧠', desc: 'OCR extraction & line item parsing' },
  { id: 'PREPARE', name: 'Prepare', icon: '🛠️', desc: 'Normalize vendor & compute flags' },
  { id: 'RETRIEVE', name: 'Retrieve', icon: '📚', desc: 'Fetch PO, GRN & history from ERP' },
  { id: 'MATCH_TWO_WAY', name: '2-Way Match', icon: '⚖️', desc: 'Match Invoice vs PO' },
  { id: 'CHECKPOINT_HITL', name: 'HITL Check', icon: '⏸️', desc: 'Checkpoint for human review' },
  { id: 'HITL_DECISION', name: 'Human Review', icon: '👨‍💼', desc: 'Human accept/reject decision' },
  { id: 'RECONCILE', name: 'Reconcile', icon: '📘', desc: 'Build accounting entries' },
  { id: 'APPROVE', name: 'Approve', icon: '🔄', desc: 'Apply approval policy' },
  { id: 'POSTING', name: 'Post to ERP', icon: '🏃', desc: 'Post to ERP & schedule payment' },
  { id: 'NOTIFY', name: 'Notify', icon: '✉️', desc: 'Notify vendor & finance team' },
  { id: 'COMPLETE', name: 'Complete', icon: '✅', desc: 'Output final payload' },
] as const;

export type StageId = typeof STAGES[number]['id'];
export type StageStatus = 'pending' | 'active' | 'done' | 'error' | 'hitl';

export const getStageIndex = (id: string) => STAGES.findIndex(s => s.id === id);
export const getProgress = (currentId: string) => ((getStageIndex(currentId) + 1) / STAGES.length) * 100;
export const getStageById = (id: string) => STAGES.find(s => s.id === id);
