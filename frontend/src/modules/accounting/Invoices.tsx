import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Plus, Trash2 } from 'lucide-react'
import clsx from 'clsx'

interface Invoice {
  id: number; invoice_number: string; client_name: string; status: string
  issue_date: string; due_date: string; total: number; subtotal: number
  tax_rate: number; tax_amount: number; items: any[]
}

const statusColor: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  sent: 'bg-blue-100 text-blue-700',
  paid: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

export default function Invoices() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const today = new Date().toISOString().split('T')[0]
  const [form, setForm] = useState({
    client_name: '', client_email: '', issue_date: today,
    due_date: today, tax_rate: 15, notes: '',
    items: [{ description: '', quantity: 1, unit_price: 0 }]
  })

  const { data: invoices = [], isLoading } = useQuery<Invoice[]>({
    queryKey: ['invoices'],
    queryFn: () => api.get('/accounting/invoices').then(r => r.data)
  })

  const create = useMutation({
    mutationFn: (data: typeof form) => api.post('/accounting/invoices', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoices'] }); setShowForm(false) }
  })

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/accounting/invoices/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] })
  })

  const updateItem = (i: number, k: string, v: any) => {
    setForm(p => {
      const items = [...p.items]
      items[i] = { ...items[i], [k]: k === 'description' ? v : +v }
      return { ...p, items }
    })
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500">{invoices.length} total</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-1.5">
          <Plus className="w-4 h-4" /> New Invoice
        </button>
      </div>

      {showForm && (
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-medium mb-4">New Invoice</h2>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <input className="input" placeholder="Client name" value={form.client_name} onChange={e => setForm(p => ({ ...p, client_name: e.target.value }))} />
            <input className="input" placeholder="Client email" value={form.client_email} onChange={e => setForm(p => ({ ...p, client_email: e.target.value }))} />
            <div><label className="text-xs text-gray-500 mb-1 block">Issue date</label><input type="date" className="input" value={form.issue_date} onChange={e => setForm(p => ({ ...p, issue_date: e.target.value }))} /></div>
            <div><label className="text-xs text-gray-500 mb-1 block">Due date</label><input type="date" className="input" value={form.due_date} onChange={e => setForm(p => ({ ...p, due_date: e.target.value }))} /></div>
            <input className="input" placeholder="Tax rate %" type="number" value={form.tax_rate} onChange={e => setForm(p => ({ ...p, tax_rate: +e.target.value }))} />
          </div>
          <p className="text-xs font-medium text-gray-700 mb-2">Line items</p>
          {form.items.map((item, i) => (
            <div key={i} className="grid grid-cols-5 gap-2 mb-2">
              <input className="input col-span-3" placeholder="Description" value={item.description} onChange={e => updateItem(i, 'description', e.target.value)} />
              <input className="input" placeholder="Qty" type="number" value={item.quantity} onChange={e => updateItem(i, 'quantity', e.target.value)} />
              <input className="input" placeholder="Unit price" type="number" value={item.unit_price} onChange={e => updateItem(i, 'unit_price', e.target.value)} />
            </div>
          ))}
          <button onClick={() => setForm(p => ({ ...p, items: [...p.items, { description: '', quantity: 1, unit_price: 0 }] }))} className="text-xs text-primary-600 hover:underline mb-3">+ Add line</button>
          <div className="flex gap-2 mt-2">
            <button onClick={() => create.mutate(form)} disabled={create.isPending} className="btn-primary">Create Invoice</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {isLoading ? <p className="text-sm text-gray-500">Loading...</p> : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">Invoice</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">Client</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">Status</th>
                <th className="text-right py-2.5 px-4 text-xs font-medium text-gray-500">Total</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">Due</th>
                <th className="py-2.5 px-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {invoices.map(inv => (
                <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-2.5 px-4 font-mono text-xs text-gray-700">{inv.invoice_number}</td>
                  <td className="py-2.5 px-4 font-medium text-gray-900">{inv.client_name}</td>
                  <td className="py-2.5 px-4"><span className={clsx('badge', statusColor[inv.status])}>{inv.status}</span></td>
                  <td className="py-2.5 px-4 text-right font-medium text-gray-900">SAR {inv.total.toFixed(2)}</td>
                  <td className="py-2.5 px-4 text-gray-500">{inv.due_date}</td>
                  <td className="py-2.5 px-4">
                    <button onClick={() => remove.mutate(inv.id)} className="text-gray-400 hover:text-red-500 transition-colors"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {invoices.length === 0 && <p className="text-sm text-gray-400 text-center py-8">No invoices yet</p>}
        </div>
      )}
    </div>
  )
}
