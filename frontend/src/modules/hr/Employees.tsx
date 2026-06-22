import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Plus, Trash2 } from 'lucide-react'

interface Employee {
  id: number; employee_id: string; first_name: string; last_name: string
  email: string; phone: string; department: string; position: string
  employment_type: string; salary: number; hire_date: string; is_active: boolean
}

const empty = {
  first_name: '', last_name: '', email: '', phone: '', department: '',
  position: '', employment_type: 'full_time', salary: 0,
  hire_date: new Date().toISOString().split('T')[0]
}

export default function Employees() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(empty)

  const { data: employees = [], isLoading } = useQuery<Employee[]>({
    queryKey: ['employees'],
    queryFn: () => api.get('/hr/employees').then(r => r.data)
  })

  const create = useMutation({
    mutationFn: (data: typeof empty) => api.post('/hr/employees', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['employees'] }); setShowForm(false); setForm(empty) }
  })

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/hr/employees/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['employees'] })
  })

  const f = (k: string) => (e: any) => setForm(p => ({ ...p, [k]: e.target.type === 'number' ? +e.target.value : e.target.value }))

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Employees</h1>
          <p className="text-sm text-gray-500">{employees.length} active</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-1.5">
          <Plus className="w-4 h-4" /> Add Employee
        </button>
      </div>

      {showForm && (
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-medium mb-4">New Employee</h2>
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="First name" value={form.first_name} onChange={f('first_name')} />
            <input className="input" placeholder="Last name" value={form.last_name} onChange={f('last_name')} />
            <input className="input" placeholder="Email" type="email" value={form.email} onChange={f('email')} />
            <input className="input" placeholder="Phone" value={form.phone} onChange={f('phone')} />
            <input className="input" placeholder="Department" value={form.department} onChange={f('department')} />
            <input className="input" placeholder="Position" value={form.position} onChange={f('position')} />
            <select className="input" value={form.employment_type} onChange={f('employment_type')}>
              <option value="full_time">Full time</option>
              <option value="part_time">Part time</option>
              <option value="contract">Contract</option>
            </select>
            <input className="input" placeholder="Salary (SAR)" type="number" value={form.salary} onChange={f('salary')} />
            <div><label className="text-xs text-gray-500 mb-1 block">Hire date</label>
              <input type="date" className="input" value={form.hire_date} onChange={f('hire_date')} /></div>
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={() => create.mutate(form)} disabled={create.isPending} className="btn-primary">Save</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {isLoading ? <p className="text-sm text-gray-500">Loading...</p> : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">ID</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">Name</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">Department</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">Position</th>
                <th className="text-right py-2.5 px-4 text-xs font-medium text-gray-500">Salary</th>
                <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500">Type</th>
                <th className="py-2.5 px-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {employees.map(e => (
                <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-2.5 px-4 font-mono text-xs text-gray-500">{e.employee_id}</td>
                  <td className="py-2.5 px-4 font-medium text-gray-900">{e.first_name} {e.last_name}</td>
                  <td className="py-2.5 px-4 text-gray-600">{e.department || '—'}</td>
                  <td className="py-2.5 px-4 text-gray-600">{e.position || '—'}</td>
                  <td className="py-2.5 px-4 text-right text-gray-900">SAR {e.salary.toLocaleString()}</td>
                  <td className="py-2.5 px-4 text-gray-500 capitalize">{e.employment_type.replace('_', ' ')}</td>
                  <td className="py-2.5 px-4">
                    <button onClick={() => remove.mutate(e.id)} className="text-gray-400 hover:text-red-500 transition-colors"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {employees.length === 0 && <p className="text-sm text-gray-400 text-center py-8">No employees yet</p>}
        </div>
      )}
    </div>
  )
}
