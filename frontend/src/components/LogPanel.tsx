// Processing log display

import { Card, Badge } from './ui';
import { LogEntry } from '../hooks/useWorkflow';

interface Props {
  logs: LogEntry[];
}

function getStatusVariant(status: string): 'success' | 'error' | 'warning' | 'info' {
  switch (status) {
    case 'success':
    case 'completed':
      return 'success';
    case 'error':
    case 'failed':
      return 'error';
    case 'warning':
    case 'pending':
      return 'warning';
    default:
      return 'info';
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'success':
    case 'completed':
      return '✅';
    case 'error':
    case 'failed':
      return '❌';
    case 'warning':
    case 'pending':
      return '⚠️';
    case 'started':
      return '🚀';
    default:
      return '🔄';
  }
}

export function LogPanel({ logs }: Props) {
  if (logs.length === 0) {
    return (
      <Card title="Processing Log" icon="📜">
        <p className="text-gray-400 text-center py-4">Submit an invoice to see real-time logs</p>
      </Card>
    );
  }

  return (
    <Card title="Processing Log" icon="📜">
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {logs.map((log, i) => (
          <div key={i} className="flex items-center gap-2 text-sm p-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors">
            <span className="text-base">{getStatusIcon(log.status)}</span>
            <Badge variant={getStatusVariant(log.status)}>
              {log.stage}
            </Badge>
            <span className="flex-1 text-gray-700">{log.message}</span>
            <span className="text-gray-400 text-xs whitespace-nowrap">{log.time}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
