// Workflow Pipeline - Visual representation of invoice processing stages
// Based on LangGraph Invoice Processing workflow documentation

import { STAGES, getStageIndex } from '../config/stages';
import { Badge, ProgressBar } from './ui';

interface Props {
  currentStage: string;
  status: 'idle' | 'running' | 'hitl' | 'done' | 'error';
}

export function Pipeline({ currentStage, status }: Props) {
  const currentIdx = getStageIndex(currentStage);
  
  const getVariant = (idx: number, stageId: string): 'success' | 'error' | 'warning' | 'info' | 'pending' => {
    // MANUAL_HANDOFF is always error when current
    if (stageId === 'MANUAL_HANDOFF' && currentStage === 'MANUAL_HANDOFF') return 'error';
    if (status === 'error' && idx === currentIdx) return 'error';
    if (status === 'hitl' && (stageId === 'CHECKPOINT_HITL' || stageId === 'HITL_DECISION')) return 'warning';
    if (idx < currentIdx) return 'success';
    if (idx === currentIdx && status === 'running') return 'info';
    if (idx === currentIdx && status === 'done') return 'success';
    return 'pending';
  };

  const getStageStatus = (idx: number, stageId: string): string => {
    if (stageId === 'MANUAL_HANDOFF' && currentStage === 'MANUAL_HANDOFF') return '✗';
    if (status === 'error' && idx === currentIdx) return '✗';
    if (status === 'hitl' && (stageId === 'CHECKPOINT_HITL' || stageId === 'HITL_DECISION')) return '⏸';
    if (idx < currentIdx) return '✓';
    if (idx === currentIdx && status === 'running') return '▶';
    if (idx === currentIdx && status === 'done') return '✓';
    return '○';
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between text-sm text-gray-600">
        <span>Progress</span>
        <span className="font-medium">
          {status === 'done' ? '100%' : currentIdx >= 0 ? Math.round(((currentIdx + 1) / STAGES.length) * 100) : 0}%
        </span>
      </div>
      <ProgressBar value={status === 'done' ? STAGES.length : currentIdx + 1} max={STAGES.length} />
      
      <div className="grid grid-cols-4 md:grid-cols-6 gap-2 mt-4">
        {STAGES.map((stage, idx) => (
          <div
            key={stage.id}
            title={stage.desc}
            className={`p-2 rounded-lg text-center transition-all cursor-help ${
              (status === 'error' && idx === currentIdx) || (stage.id === 'MANUAL_HANDOFF' && currentStage === 'MANUAL_HANDOFF') ? 'ring-2 ring-red-400 bg-red-50' :
              status === 'hitl' && (stage.id === 'CHECKPOINT_HITL' || stage.id === 'HITL_DECISION') ? 'ring-2 ring-amber-400 bg-amber-50' :
              idx === currentIdx && status === 'running' ? 'ring-2 ring-blue-400 bg-blue-50 animate-pulse' : 
              idx < currentIdx || (idx === currentIdx && status === 'done') ? 'bg-green-50' : 
              'bg-gray-50 opacity-60'
            }`}
          >
            <div className="text-xl">{stage.icon}</div>
            <div className="text-xs font-medium truncate" title={stage.name}>{stage.name}</div>
            <Badge variant={getVariant(idx, stage.id)}>
              {getStageStatus(idx, stage.id)}
            </Badge>
          </div>
        ))}
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-4 justify-center text-xs text-gray-500 mt-2">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500"></span> Completed
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span> Running
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-500"></span> HITL Paused
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-gray-300"></span> Pending
        </span>
      </div>
    </div>
  );
}
