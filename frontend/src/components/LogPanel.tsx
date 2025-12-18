// Processing log display with stage-based grouping

import { useState, useMemo } from 'react';
import { Card } from './ui';
import { LogEntry, ToolCallEntry } from '../hooks/useWorkflow';

interface Props {
  logs: LogEntry[];
  toolCalls?: ToolCallEntry[];
}

// Define the actual workflow stages (as per documentation)
const WORKFLOW_STAGES = [
  'INTAKE',
  'UNDERSTAND', 
  'PREPARE',
  'RETRIEVE',
  'MATCH_TWO_WAY',
  'CHECKPOINT_HITL',
  'HITL_DECISION',
  'RECONCILE',
  'APPROVE',
  'POSTING',
  'NOTIFY',
  'COMPLETE',
  'MANUAL_HANDOFF'
];

const STAGE_INFO: Record<string, { icon: string; name: string }> = {
  'INTAKE': { icon: '📥', name: 'Intake' },
  'UNDERSTAND': { icon: '🧠', name: 'Understand' },
  'PREPARE': { icon: '🛠️', name: 'Prepare' },
  'RETRIEVE': { icon: '📚', name: 'Retrieve' },
  'MATCH_TWO_WAY': { icon: '⚖️', name: 'Match' },
  'CHECKPOINT_HITL': { icon: '⏸️', name: 'Checkpoint' },
  'HITL_DECISION': { icon: '👨‍💼', name: 'HITL Decision' },
  'RECONCILE': { icon: '📘', name: 'Reconcile' },
  'APPROVE': { icon: '🔄', name: 'Approve' },
  'POSTING': { icon: '🏃', name: 'Posting' },
  'NOTIFY': { icon: '✉️', name: 'Notify' },
  'COMPLETE': { icon: '✅', name: 'Complete' },
  'MANUAL_HANDOFF': { icon: '⚠️', name: 'Manual Handoff' },
};

function getStageColor(stage: string): string {
  const colors: Record<string, string> = {
    'INTAKE': 'bg-blue-500',
    'UNDERSTAND': 'bg-indigo-500',
    'PREPARE': 'bg-violet-500',
    'RETRIEVE': 'bg-purple-500',
    'MATCH_TWO_WAY': 'bg-pink-500',
    'CHECKPOINT_HITL': 'bg-orange-500',
    'HITL_DECISION': 'bg-amber-500',
    'RECONCILE': 'bg-teal-500',
    'APPROVE': 'bg-cyan-500',
    'POSTING': 'bg-emerald-500',
    'NOTIFY': 'bg-green-500',
    'COMPLETE': 'bg-green-600',
    'MANUAL_HANDOFF': 'bg-red-500',
  };
  return colors[stage] || 'bg-gray-400';
}

function getLogTypeIcon(logType?: string): string {
  switch (logType) {
    case 'tool_call':
    case 'tool_selection':
      return '🔧';
    case 'tool_result':
      return '📦';
    case 'result':
      return '📋';
    case 'decision':
      return '⚡';
    case 'warning':
      return '⚠️';
    case 'error':
      return '❌';
    case 'hitl':
      return '👨‍💼';
    case 'success':
      return '🎉';
    default:
      return '•';
  }
}

function getLogTypeStyle(logType?: string): string {
  switch (logType) {
    case 'tool_call':
    case 'tool_selection':
    case 'tool_result':
      return 'border-l-2 border-purple-400 pl-2';
    case 'decision':
      return 'border-l-2 border-blue-400 pl-2';
    case 'warning':
      return 'border-l-2 border-amber-400 pl-2';
    case 'error':
      return 'border-l-2 border-red-400 pl-2';
    case 'success':
      return 'border-l-2 border-green-400 pl-2';
    default:
      return 'pl-3';
  }
}

interface StageGroup {
  stage: string;
  logs: LogEntry[];
  status: 'running' | 'completed' | 'failed';
  toolCount: number;
}

export function LogPanel({ logs, toolCalls = [] }: Props) {
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set());
  const [showSystemLogs, setShowSystemLogs] = useState(false);

  // Group logs by stage
  const { stageGroups, systemLogs } = useMemo(() => {
    const groups: Record<string, LogEntry[]> = {};
    const system: LogEntry[] = [];
    
    logs.forEach(log => {
      if (WORKFLOW_STAGES.includes(log.stage)) {
        if (!groups[log.stage]) groups[log.stage] = [];
        groups[log.stage].push(log);
      } else {
        system.push(log);
      }
    });
    
    // Convert to ordered array based on first appearance
    const orderedStages: StageGroup[] = [];
    const seenStages = new Set<string>();
    
    logs.forEach(log => {
      if (WORKFLOW_STAGES.includes(log.stage) && !seenStages.has(log.stage)) {
        seenStages.add(log.stage);
        const stageLogs = groups[log.stage] || [];
        const hasError = stageLogs.some(l => l.logType === 'error' || l.status === 'error');
        const isCompleted = stageLogs.some(l => l.message?.includes('completed'));
        
        orderedStages.push({
          stage: log.stage,
          logs: stageLogs,
          status: hasError ? 'failed' : isCompleted ? 'completed' : 'running',
          toolCount: stageLogs.filter(l => l.logType === 'tool_call').length,
        });
      }
    });
    
    return { stageGroups: orderedStages, systemLogs: system };
  }, [logs]);

  const toggleStage = (stage: string) => {
    const newExpanded = new Set(expandedStages);
    if (newExpanded.has(stage)) {
      newExpanded.delete(stage);
    } else {
      newExpanded.add(stage);
    }
    setExpandedStages(newExpanded);
  };

  const expandAll = () => {
    setExpandedStages(new Set(stageGroups.map(g => g.stage)));
  };

  const collapseAll = () => {
    setExpandedStages(new Set());
  };

  if (logs.length === 0) {
    return (
      <Card title="Processing Log" icon="📜">
        <p className="text-gray-400 text-center py-4">Submit an invoice to see real-time logs</p>
      </Card>
    );
  }

  return (
    <Card title="Processing Log" icon="📜">
      {/* Stats bar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-4 text-sm">
          <span className="text-gray-500">
            <span className="font-medium">{logs.length}</span> logs
          </span>
          <span className="text-purple-600">
            <span className="font-medium">{toolCalls.length}</span> tools
          </span>
          <span className="text-green-600">
            <span className="font-medium">{stageGroups.length}</span> stages
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            Expand All
          </button>
          <span className="text-gray-300">|</span>
          <button
            onClick={collapseAll}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Stage Groups */}
      <div className="space-y-2 max-h-[500px] overflow-y-auto">
        {stageGroups.map((group) => {
          const isExpanded = expandedStages.has(group.stage);
          const stageInfo = STAGE_INFO[group.stage] || { icon: '📋', name: group.stage };
          
          return (
            <div key={group.stage} className="border rounded-lg overflow-hidden">
              {/* Stage Header */}
              <button
                onClick={() => toggleStage(group.stage)}
                className={`w-full flex items-center justify-between p-3 text-left transition-colors ${
                  group.status === 'completed' ? 'bg-green-50 hover:bg-green-100' :
                  group.status === 'failed' ? 'bg-red-50 hover:bg-red-100' :
                  'bg-blue-50 hover:bg-blue-100'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{stageInfo.icon}</span>
                  <div>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium text-white ${getStageColor(group.stage)}`}>
                      {group.stage}
                    </span>
                    <span className="ml-2 text-sm text-gray-600">{stageInfo.name}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {group.toolCount > 0 && (
                    <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded">
                      🔧 {group.toolCount}
                    </span>
                  )}
                  <span className="text-xs text-gray-500">
                    {group.logs.length} events
                  </span>
                  <span className={`text-sm ${group.status === 'completed' ? 'text-green-600' : group.status === 'failed' ? 'text-red-600' : 'text-blue-600'}`}>
                    {group.status === 'completed' ? '✓' : group.status === 'failed' ? '✗' : '⋯'}
                  </span>
                  <span className="text-gray-400 transition-transform" style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                    ▼
                  </span>
                </div>
              </button>
              
              {/* Stage Logs */}
              {isExpanded && (
                <div className="bg-white border-t">
                  {group.logs.map((log, i) => (
                    <div 
                      key={i}
                      className={`flex items-start gap-2 text-sm py-1.5 px-3 hover:bg-gray-50 ${getLogTypeStyle(log.logType)}`}
                    >
                      <span className="text-xs flex-shrink-0 w-4">{getLogTypeIcon(log.logType)}</span>
                      <span className="flex-1 text-gray-700 text-xs break-words">{log.message}</span>
                      <span className="text-gray-400 text-xs whitespace-nowrap">{log.time}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {/* System Logs Toggle */}
        {systemLogs.length > 0 && (
          <div className="border rounded-lg overflow-hidden bg-gray-50">
            <button
              onClick={() => setShowSystemLogs(!showSystemLogs)}
              className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-100"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">⚙️</span>
                <span className="text-sm text-gray-600">System Logs</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">{systemLogs.length} events</span>
                <span className="text-gray-400 transition-transform" style={{ transform: showSystemLogs ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                  ▼
                </span>
              </div>
            </button>
            
            {showSystemLogs && (
              <div className="bg-white border-t">
                {systemLogs.map((log, i) => (
                  <div 
                    key={i}
                    className="flex items-start gap-2 text-sm py-1.5 px-3 hover:bg-gray-50 pl-3"
                  >
                    <span className="text-xs text-gray-400 flex-shrink-0">{log.stage}</span>
                    <span className="flex-1 text-gray-600 text-xs break-words">{log.message}</span>
                    <span className="text-gray-400 text-xs whitespace-nowrap">{log.time}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
