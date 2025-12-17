// Invoice submission form

import { useState, FormEvent, ChangeEvent } from 'react';
import { Card, Button, Input } from './ui';
import { Invoice } from '../hooks/useWorkflow';

interface Props {
  onSubmit: (invoice: Invoice) => void;
  loading: boolean;
  disabled: boolean;
}

// Helper to get today and 30 days from now
const today = () => new Date().toISOString().split('T')[0];
const in30Days = () => {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().split('T')[0];
};

// Demo data for quick testing - includes all required fields
const DEMO: Invoice = {
  invoice_id: `INV-${Date.now()}`,
  vendor_name: 'Acme Technology Solutions',
  vendor_tax_id: 'TAX-ACME-2024',
  invoice_date: today(),
  due_date: in30Days(),
  amount: 15750,
  currency: 'USD',
  line_items: [
    { desc: 'Software License - Enterprise', qty: 5, unit_price: 2000, total: 10000 },
    { desc: 'Annual Support Package', qty: 1, unit_price: 5750, total: 5750 },
  ],
  attachments: [
    'uploads/invoice_scan_001.pdf',
    'uploads/purchase_order_ref.pdf',
    'uploads/delivery_receipt.png'
  ],
  po_number: 'PO-2024-001234',
};

// Create empty invoice template
const emptyInvoice = (): Invoice => ({
  invoice_id: `INV-${Date.now()}`,
  vendor_name: '',
  vendor_tax_id: '',
  invoice_date: today(),
  due_date: in30Days(),
  amount: 0,
  currency: 'USD',
  line_items: [{ desc: '', qty: 1, unit_price: 0, total: 0 }],
  attachments: [],
  po_number: '',
});

export function InvoiceForm({ onSubmit, loading, disabled }: Props) {
  const [form, setForm] = useState<Invoice>(emptyInvoice());
  const [attachmentInput, setAttachmentInput] = useState('');
  
  const update = (field: keyof Invoice, value: string | number) => 
    setForm((f: Invoice) => ({ ...f, [field]: value }));

  // Auto-calculate amount from line items
  const updateLineItem = (idx: number, field: keyof Invoice['line_items'][0], value: string | number) => {
    setForm((f: Invoice) => {
      const items = [...f.line_items];
      items[idx] = { ...items[idx], [field]: value };
      if (field === 'qty' || field === 'unit_price') {
        items[idx].total = items[idx].qty * items[idx].unit_price;
      }
      const amount = items.reduce((sum, item) => sum + item.total, 0);
      return { ...f, line_items: items, amount };
    });
  };

  // Add attachment
  const addAttachment = () => {
    if (attachmentInput.trim()) {
      setForm((f: Invoice) => ({ 
        ...f, 
        attachments: [...(f.attachments || []), attachmentInput.trim()] 
      }));
      setAttachmentInput('');
    }
  };

  // Remove attachment
  const removeAttachment = (idx: number) => {
    setForm((f: Invoice) => ({
      ...f,
      attachments: (f.attachments || []).filter((_, i) => i !== idx)
    }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (form.vendor_name && form.amount > 0) onSubmit(form);
  };

  const fillDemo = () => {
    setForm({ ...DEMO, invoice_id: `INV-${Date.now()}` });
  };

  return (
    <Card title="Submit Invoice" icon="📄">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex justify-end">
          <Button type="button" variant="ghost" onClick={fillDemo}>
            🚀 Demo Data
          </Button>
        </div>
        
        {/* Vendor Info */}
        <div className="grid grid-cols-2 gap-3">
          <Input 
            label="Vendor Name *" 
            value={form.vendor_name} 
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('vendor_name', e.target.value)}
            required
          />
          <Input 
            label="Vendor Tax ID" 
            value={form.vendor_tax_id || ''} 
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('vendor_tax_id', e.target.value)}
            placeholder="TAX-XXXXX"
          />
        </div>

        {/* Dates and PO */}
        <div className="grid grid-cols-3 gap-3">
          <Input 
            label="Invoice Date" 
            type="date"
            value={form.invoice_date} 
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('invoice_date', e.target.value)}
          />
          <Input 
            label="Due Date" 
            type="date"
            value={form.due_date} 
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('due_date', e.target.value)}
          />
          <Input 
            label="PO Number" 
            value={form.po_number || ''} 
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('po_number', e.target.value)}
            placeholder="PO-XXXX"
          />
        </div>
        
        {/* Line Item */}
        <div className="bg-gray-50 p-3 rounded-lg">
          <span className="text-sm font-medium text-gray-700">📋 Line Item</span>
          <div className="grid grid-cols-4 gap-2 mt-2">
            <Input 
              label="Description" 
              value={form.line_items[0]?.desc || ''} 
              onChange={(e: ChangeEvent<HTMLInputElement>) => updateLineItem(0, 'desc', e.target.value)}
            />
            <Input 
              label="Qty" 
              type="number"
              min={1}
              value={form.line_items[0]?.qty || ''} 
              onChange={(e: ChangeEvent<HTMLInputElement>) => updateLineItem(0, 'qty', parseFloat(e.target.value) || 0)}
            />
            <Input 
              label="Unit Price" 
              type="number"
              min={0}
              value={form.line_items[0]?.unit_price || ''} 
              onChange={(e: ChangeEvent<HTMLInputElement>) => updateLineItem(0, 'unit_price', parseFloat(e.target.value) || 0)}
            />
            <Input 
              label="Total" 
              type="number"
              value={form.line_items[0]?.total || ''}
              disabled
            />
          </div>
        </div>

        {/* Attachments */}
        <div className="bg-blue-50 p-3 rounded-lg">
          <span className="text-sm font-medium text-gray-700">📎 Attachments (Invoice scans, receipts)</span>
          <div className="flex gap-2 mt-2">
            <Input 
              value={attachmentInput} 
              onChange={(e: ChangeEvent<HTMLInputElement>) => setAttachmentInput(e.target.value)}
              placeholder="Enter file path or URL..."
              className="flex-1"
            />
            <Button type="button" variant="secondary" onClick={addAttachment}>
              Add
            </Button>
          </div>
          {(form.attachments || []).length > 0 && (
            <div className="mt-2 space-y-1">
              {(form.attachments || []).map((att, idx) => (
                <div key={idx} className="flex items-center justify-between bg-white px-2 py-1 rounded text-sm">
                  <span className="text-gray-600 truncate">📄 {att}</span>
                  <button 
                    type="button" 
                    onClick={() => removeAttachment(idx)}
                    className="text-red-500 hover:text-red-700 ml-2"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-2 border-t">
          <div>
            <span className="font-bold text-lg">Total: ${form.amount.toLocaleString()}</span>
            <span className="text-sm text-gray-500 ml-2">({(form.attachments || []).length} attachments)</span>
          </div>
          <Button type="submit" loading={loading} disabled={disabled || !form.vendor_name || form.amount <= 0}>
            Submit Invoice
          </Button>
        </div>
      </form>
    </Card>
  );
}
