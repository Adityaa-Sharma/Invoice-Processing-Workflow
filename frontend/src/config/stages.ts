// Workflow stage configuration and types

export const STAGES = [
  { id: 'INTAKE', name: 'Intake', icon: '📥' },
  { id: 'UNDERSTAND', name: 'Understand', icon: '🔍' },
  { id: 'PREPARE', name: 'Prepare', icon: '📋' },
  { id: 'RETRIEVE', name: 'Retrieve', icon: '🔗' },
  { id: 'MATCH_TWO_WAY', name: '2-Way Match', icon: '🔀' },
  { id: 'MATCH_THREE_WAY', name: '3-Way Match', icon: '🔄' },
  { id: 'HITL_REVIEW', name: 'Human Review', icon: '👤' },
  { id: 'RECONCILE', name: 'Reconcile', icon: '📊' },
  { id: 'APPROVE', name: 'Approve', icon: '✅' },
  { id: 'POSTING', name: 'Post to ERP', icon: '📤' },
  { id: 'NOTIFY', name: 'Notify', icon: '📧' },
  { id: 'COMPLETE', name: 'Complete', icon: '🎉' },
] as const;

export type StageId = typeof STAGES[number]['id'];
export type StageStatus = 'pending' | 'active' | 'done' | 'error' | 'hitl';

export const getStageIndex = (id: string) => STAGES.findIndex(s => s.id === id);
export const getProgress = (currentId: string) => ((getStageIndex(currentId) + 1) / STAGES.length) * 100;
