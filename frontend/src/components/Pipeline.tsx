// Workflow Pipeline - Visual representation of stages

import { STAGES, getStageIndex } from '../config/stages';
import { Badge, ProgressBar } from './ui';

interface Props {
  currentStage: string;
  status: 'idle' | 'running' | 'hitl' | 'done' | 'error';
}

export function Pipeline({ currentStage, status }: Props) {
  const currentIdx = getStageIndex(currentStage);
  
  const getVariant = (idx: number, stageId: string) => {
    if (status === 'hitl' && stageId === 'HITL_REVIEW') return 'warning';
    if (idx < currentIdx) return 'success';
    if (idx === currentIdx && status === 'running') return 'info';
    return 'pending';
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between text-sm text-gray-600">
        <span>Progress</span>
        <span>{currentIdx >= 0 ? Math.round(((currentIdx + 1) / STAGES.length) * 100) : 0}%</span>
      </div>
      <ProgressBar value={currentIdx + 1} max={STAGES.length} />
      
      <div className="grid grid-cols-4 md:grid-cols-6 gap-2 mt-4">
        {STAGES.map((stage, idx) => (
          <div
            key={stage.id}
            className={`p-2 rounded-lg text-center transition-all ${
              idx === currentIdx && status === 'running' ? 'ring-2 ring-blue-400 bg-blue-50' : 
              idx < currentIdx ? 'bg-green-50' : 'bg-gray-50'
            }`}
          >
            <div className="text-xl">{stage.icon}</div>
            <div className="text-xs font-medium truncate">{stage.name}</div>
            <Badge variant={getVariant(idx, stage.id)}>
              {idx < currentIdx ? '✓' : idx === currentIdx ? '●' : '○'}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
