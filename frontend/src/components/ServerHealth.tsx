// Server health indicator

import { StatusDot } from './ui';

interface Props {
  health: { api: boolean; common: boolean; atlas: boolean };
}

export function ServerHealth({ health }: Props) {
  const all = health.api && health.common && health.atlas;
  
  return (
    <div className={`flex items-center gap-4 px-4 py-2 rounded-lg text-sm ${all ? 'bg-green-50' : 'bg-red-50'}`}>
      <span className="flex items-center gap-1"><StatusDot active={health.api} /> API</span>
      <span className="flex items-center gap-1"><StatusDot active={health.common} /> COMMON</span>
      <span className="flex items-center gap-1"><StatusDot active={health.atlas} /> ATLAS</span>
    </div>
  );
}
