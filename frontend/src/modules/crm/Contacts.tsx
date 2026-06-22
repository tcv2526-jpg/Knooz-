import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Plus, Trash2, Mail, Phone, Building } from 'lucide-react'

interface Contact {
  id: number; first_name: string; last_name: string; email: string
  phone: string; company: string; position: string; notes: string
}

const empty = { first_name: '', last_name: '', email: '', phone: '', company: '', position: '', notes: '' }

export default function Contacts() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(empty)

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ['contacts'],
    queryFn: () => api.get('/crm/contacts').then(r => r.data)
  })

  const create = useMutation({
    mutationFn: (data: typeof empty) => api.post('/crm/contacts', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['contacts'] }); setShowForm(false); setForm(empty) }
  })

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/crm/contacts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contacts'] })
  })

  const f = (k: string) => (e: any) => setForm(p => ({ ...p, [k]: e.target.value }))

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Contacts</h1>
          <p className="text-sm text-gray-500">{contacts.length} total</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-1.5">
          <Plus className="w-4 h-4" /> Add Contact
        </button>
      </div>

      {showForm && (
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-medium text-gray-900 mb-4">New Contact</h2>
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="First name" value={form.first_name} onChange={f('first_name')} />
            <input className="input" placeholder="Last name" value={form.last_name} onChange={f('last_name')} />
            <input className="input" placeholder="Email" type="email" value={form.email} onChange={f('email')} />
            <input className="input" placeholder="Phone" value={form.phone} onChange={f('phone')} />
            <input className="input" placeholder="Company" value={form.company} onChange={f('company')} />
            <input className="input" placeholder="Position" value={form.position} onChange={f('position')} />
            <textarea className="input col-span-2" placeholder="Notes" rows={2} value={form.notes} onChange={f('notes')} />
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={() => create.mutate(form)} disabled={create.isPending} className="btn-primary">Save</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {isLoading ? <p className="text-sm text-gray-500">Loading...</p> : (
        <div className="grid gap-3">
          {contacts.map(c => (
            <div key={c.id} className="card p-4 flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">{c.first_name} {c.last_name}</p>
                <div className="flex flex-wrap gap-3 mt-1">
                  {c.email && <span className="flex items-center gap-1 text-xs text-gray-500"><Mail className="w-3 h-3" />{c.email}</span>}
                  {c.phone && <span className="flex items-center gap-1 text-xs text-gray-500"><Phone className="w-3 h-3" />{c.phone}</span>}
                  {c.company && <span className="flex items-center gap-1 text-xs text-gray-500"><Building className="w-3 h-3" />{c.company}</span>}
                </div>
              </div>
              <button onClick={() => remove.mutate(c.id)} className="text-gray-400 hover:text-red-500 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
          {contacts.length === 0 && <p className="text-sm text-gray-400 text-center py-8">No contacts yet</p>}
        </div>
      )}
    </div>
  )
}
