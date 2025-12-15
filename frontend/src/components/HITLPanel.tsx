// Human-in-the-loop review panel

import { Card, Button } from './ui';

interface Props {
  reason: string;
  checkpointId: string;
  onApprove: () => void;
  onReject: () => void;
  loading: boolean;
}

export function HITLPanel({ reason, checkpointId, onApprove, onReject, loading }: Props) {
  return (
    <Card className="border-2 border-amber-400 bg-amber-50">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-3xl">👤</span>
        <div>
          <h3 className="font-bold text-amber-800">Human Review Required</h3>
          <p className="text-sm text-amber-600">ID: {checkpointId}</p>
        </div>
      </div>
      
      <p className="text-gray-700 mb-4 p-3 bg-white rounded-lg">{reason}</p>
      
      <div className="flex gap-3">
        <Button variant="danger" onClick={onReject} loading={loading} className="flex-1">
          ✕ Reject
        </Button>
        <Button variant="primary" onClick={onApprove} loading={loading} className="flex-1 !bg-green-600 hover:!bg-green-700">
          ✓ Approve
        </Button>
      </div>
    </Card>
  );
}
