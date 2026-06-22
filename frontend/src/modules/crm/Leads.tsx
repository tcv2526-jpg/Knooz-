import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Plus, Trash2, Edit2, X } from 'lucide-react'
import clsx from 'clsx'

interface Lead {
  id: number; title: string; contact_id: number | null; status: string
  source: string; estimated_value: number; notes: string
}

const statusColor: Record<string, string> = {
  new: 'bg-blue-100 text-blue-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  qualified: 'bg-green-100 text-green-700',
  lost: 'bg-red-100 text-red-700',
}

const empty = { title: '', contact_id: null as number | null, status: 'new', source: '', estimated_value: 0, notes: '' }

export default function Leads() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Lead | null>(null)
  const [form, setForm] = useState(empty)

  const { data: leads = [], isLoading } = useQuery<Lead[]>({
    queryKey: ['leads'],
    queryFn: () => api.get('/crm/leads').then(r => r.data)
  })

  const create = useMutation({
    mutationFn: (d: typeof empty) => api.post('/crm/leads', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['leads'] }); setShowForm(false); setForm(empty) }
  })

  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: typeof empty }) => api.put(`/crm/leads/${id}`, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['leads'] }); setEditing(null) }
  })

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/crm/leads/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] })
  })

  const f = (k: string) => (e: any) => {
    const v = e.target.type === 'number' ? +e.target.value : e.target.value
    if (editing) setEditing(p => ({ ...p!, [k]: v }))
    else setForm(p => ({ ...p, [k]: v }))
  }

  const FormRow = ({ data, onSave, onCancel, isPending }: any) => (
    <div className="card p-5 mb-4">
      <div className="grid grid-cols-2 gap-3">
        <input className="input col-span-2" placeholder="Lead title" value={data.title} onChange={f('title')} />
        <select className="input" value={data.status} onChange={f('status')}>
          {['new','contacted','qualified','lost'].map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase()+s.slice(1)}</option>)}
        </select>
        <input className="input" placeholder="Source (e.g. Website, Referral)" value={data.source} onChange={f('source')} />
        <input className="input" placeholder="Estimated value (SAR)" type="number" value={data.estimated_value} onChange={f('estimated_value')} />
        <textarea className="input col-span-2" placeholder="Notes" rows={2} value={data.notes} onChange={f('notes')} />
      </div>
      <div className="flex gap-2 mt-3">
        <button onClick={onSave} disabled={isPending} className="btn-primary">Save</button>
        <button onClick={onCancel} className="btn-secondary">Cancel</button>
      </div>
    </div>
  )

  // Group by status for kanban-style view
  const statuses = ['new', 'contacted', 'qualified', 'lost']

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Leads</h1>
          <p className="text-sm text-gray-500">{leads.length} total</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-1.5">
          <Plus className="w-4 h-4" /> Add Lead
        </button>
      </div>

      {showForm && (
        <FormRow
          data={form}
          onSave={() => create.mutate(form)}
          onCancel={() => { setShowForm(false); setForm(empty) }}
          isPending={create.isPending}
        />
      )}

      {editing && (
        <FormRow
          data={editing}
          onSave={() => update.mutate({ id: editing.id, data: editing as any })}
          onCancel={() => setEditing(null)}
          isPending={update.isPending}
        />
      )}

      {isLoading ? <p className="text-sm text-gray-500">Loading...</p> : (
        <div className="grid grid-cols-4 gap-4">
          {statuses.map(status => {
            const group = leads.filter(l => l.status === status)
            return (
              <div key={status}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={clsx('badge', statusColor[status])}>{status.charAt(0).toUpperCase()+status.slice(1)}</span>
                  <span className="text-xs text-gray-400">{group.length}</span>
                </div>
                <div className="space-y-2">
                  {group.map(lead => (
                    <div key={lead.id} className="card p-3">
                      <p className="text-sm font-medium text-gray-900 mb-1">{lead.title}</p>
                      {lead.source && <p className="text-xs text-gray-500 mb-1">via {lead.source}</p>}
                      {lead.estimated_value > 0 && (
                        <p className="text-xs font-medium text-green-600">SAR {lead.estimated_value.toLocaleString()}</p>
                      )}
                      <div className="flex gap-1.5 mt-2">
                        <button onClick={() => { setEditing(lead); setShowForm(false) }} className="text-gray-400 hover:text-blue-500 transition-colors">
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => remove.mutate(lead.id)} className="text-gray-400 hover:text-red-500 transition-colors">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                  {group.length === 0 && (
                    <div className="border-2 border-dashed border-gray-100 rounded-xl h-20 flex items-center justify-center">
                      <span className="text-xs text-gray-300">No leads</span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
