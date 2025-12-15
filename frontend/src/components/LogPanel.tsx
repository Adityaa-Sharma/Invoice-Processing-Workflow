// Processing log display

import { Card, Badge } from './ui';
import { LogEntry } from '../hooks/useWorkflow';

interface Props {
  logs: LogEntry[];
}

export function LogPanel({ logs }: Props) {
  if (logs.length === 0) {
    return (
      <Card title="Log" icon="📜">
        <p className="text-gray-400 text-center py-4">Submit an invoice to see logs</p>
      </Card>
    );
  }

  return (
    <Card title="Log" icon="📜">
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {logs.map((log, i) => (
          <div key={i} className="flex items-center gap-2 text-sm p-2 bg-gray-50 rounded">
            <Badge variant={log.status === 'success' ? 'success' : log.status === 'error' ? 'error' : 'info'}>
              {log.stage}
            </Badge>
            <span className="flex-1 truncate">{log.message}</span>
            <span className="text-gray-400 text-xs">{log.time}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
