// Invoice submission form

import { useState, FormEvent, ChangeEvent } from 'react';
import { Card, Button, Input } from './ui';
import { Invoice } from '../hooks/useWorkflow';

interface Props {
  onSubmit: (invoice: Invoice) => void;
  loading: boolean;
  disabled: boolean;
}

// Demo data for quick testing
const DEMO: Invoice = {
  vendor_name: 'Acme Technology Solutions',
  amount: 15750,
  currency: 'USD',
  po_number: 'PO-2024-001234',
};

export function InvoiceForm({ onSubmit, loading, disabled }: Props) {
  const [form, setForm] = useState<Invoice>({ vendor_name: '', amount: 0, currency: 'USD', po_number: '' });
  
  const update = (field: keyof Invoice, value: string | number) => 
    setForm((f: Invoice) => ({ ...f, [field]: value }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (form.vendor_name && form.amount > 0) onSubmit(form);
  };

  return (
    <Card title="Submit Invoice" icon="📄">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex justify-end">
          <Button type="button" variant="ghost" onClick={() => setForm(DEMO)}>
            🚀 Demo Data
          </Button>
        </div>
        
        <Input 
          label="Vendor Name *" 
          value={form.vendor_name} 
          onChange={(e: ChangeEvent<HTMLInputElement>) => update('vendor_name', e.target.value)}
          placeholder="Enter vendor name"
          required
        />
        
        <div className="grid grid-cols-2 gap-4">
          <Input 
            label="Amount *" 
            type="number" 
            min={0}
            step={0.01}
            value={form.amount || ''} 
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('amount', parseFloat(e.target.value) || 0)}
            required
          />
          <Input 
            label="PO Number" 
            value={form.po_number || ''} 
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('po_number', e.target.value)}
            placeholder="PO-XXXX"
          />
        </div>

        <Button type="submit" loading={loading} disabled={disabled || !form.vendor_name || form.amount <= 0} className="w-full">
          Submit Invoice
        </Button>
      </form>
    </Card>
  );
}
