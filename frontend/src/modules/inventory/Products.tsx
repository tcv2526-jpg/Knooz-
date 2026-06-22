import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { Plus, Trash2, AlertTriangle } from 'lucide-react'

interface Product {
  id: number; name: string; sku: string; description: string
  price: number; cost: number; stock_qty: number; reorder_level: number
  category: string; unit: string
}

const empty = { name: '', sku: '', description: '', price: 0, cost: 0, stock_qty: 0, reorder_level: 10, category: '', unit: 'pcs' }

export default function Products() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(empty)

  const { data: products = [], isLoading } = useQuery<Product[]>({
    queryKey: ['products'],
    queryFn: () => api.get('/inventory/products').then(r => r.data)
  })

  const create = useMutation({
    mutationFn: (data: typeof empty) => api.post('/inventory/products', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['products'] }); setShowForm(false); setForm(empty) }
  })

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/inventory/products/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] })
  })

  const f = (k: string) => (e: any) => setForm(p => ({ ...p, [k]: e.target.type === 'number' ? +e.target.value : e.target.value }))

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Products</h1>
          <p className="text-sm text-gray-500">{products.length} items</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-1.5">
          <Plus className="w-4 h-4" /> Add Product
        </button>
      </div>

      {showForm && (
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-medium mb-4">New Product</h2>
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="Product name" value={form.name} onChange={f('name')} />
            <input className="input" placeholder="SKU" value={form.sku} onChange={f('sku')} />
            <input className="input" placeholder="Category" value={form.category} onChange={f('category')} />
            <input className="input" placeholder="Unit (pcs, kg, etc.)" value={form.unit} onChange={f('unit')} />
            <input className="input" placeholder="Price (SAR)" type="number" value={form.price} onChange={f('price')} />
            <input className="input" placeholder="Cost (SAR)" type="number" value={form.cost} onChange={f('cost')} />
            <input className="input" placeholder="Stock quantity" type="number" value={form.stock_qty} onChange={f('stock_qty')} />
            <input className="input" placeholder="Reorder level" type="number" value={form.reorder_level} onChange={f('reorder_level')} />
            <textarea className="input col-span-2" placeholder="Description" rows={2} value={form.description} onChange={f('description')} />
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={() => create.mutate(form)} disabled={create.isPending} className="btn-primary">Save</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {isLoading ? <p className="text-sm text-gray-500">Loading...</p> : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left py-2.5 px-3 text-xs font-medium text-gray-500">Product</th>
                <th className="text-left py-2.5 px-3 text-xs font-medium text-gray-500">SKU</th>
                <th className="text-right py-2.5 px-3 text-xs font-medium text-gray-500">Price</th>
                <th className="text-right py-2.5 px-3 text-xs font-medium text-gray-500">Stock</th>
                <th className="text-left py-2.5 px-3 text-xs font-medium text-gray-500">Category</th>
                <th className="py-2.5 px-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {products.map(p => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-2.5 px-3">
                    <span className="font-medium text-gray-900">{p.name}</span>
                  </td>
                  <td className="py-2.5 px-3 text-gray-500 font-mono text-xs">{p.sku}</td>
                  <td className="py-2.5 px-3 text-right text-gray-900">SAR {p.price.toFixed(2)}</td>
                  <td className="py-2.5 px-3 text-right">
                    <span className={`flex items-center justify-end gap-1 ${p.stock_qty <= p.reorder_level ? 'text-red-500' : 'text-gray-900'}`}>
                      {p.stock_qty <= p.reorder_level && <AlertTriangle className="w-3 h-3" />}
                      {p.stock_qty} {p.unit}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-gray-500">{p.category || '—'}</td>
                  <td className="py-2.5 px-3">
                    <button onClick={() => remove.mutate(p.id)} className="text-gray-400 hover:text-red-500 transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {products.length === 0 && <p className="text-sm text-gray-400 text-center py-8">No products yet</p>}
        </div>
      )}
    </div>
  )
}
