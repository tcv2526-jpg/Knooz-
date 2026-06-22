import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { Users, TrendingUp, Package, Receipt, UserCheck, DollarSign, AlertTriangle, Clock } from 'lucide-react'

function StatCard({ title, value, icon: Icon, color, sub }: any) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{value ?? '—'}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4.5 h-4.5" />
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: crm } = useQuery({ queryKey: ['crm-stats'], queryFn: () => api.get('/crm/stats').then(r => r.data) })
  const { data: inv } = useQuery({ queryKey: ['inv-stats'], queryFn: () => api.get('/inventory/stats').then(r => r.data) })
  const { data: acc } = useQuery({ queryKey: ['acc-stats'], queryFn: () => api.get('/accounting/stats').then(r => r.data) })
  const { data: hr } = useQuery({ queryKey: ['hr-stats'], queryFn: () => api.get('/hr/stats').then(r => r.data) })

  const fmt = (n?: number) => n != null ? n.toLocaleString('en-SA', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : '—'

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500">Overview of your business</p>
      </div>

      {/* CRM */}
      <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">CRM</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard title="Contacts" value={crm?.total_contacts} icon={Users} color="bg-blue-50 text-blue-600" />
        <StatCard title="Active Leads" value={crm?.total_leads} icon={TrendingUp} color="bg-purple-50 text-purple-600" />
        <StatCard title="Deals" value={crm?.total_deals} icon={TrendingUp} color="bg-indigo-50 text-indigo-600" />
        <StatCard title="Deal Value" value={`SAR ${fmt(crm?.total_deal_value)}`} icon={DollarSign} color="bg-green-50 text-green-600" />
      </div>

      {/* Accounting */}
      <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">Accounting</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Income" value={`SAR ${fmt(acc?.total_income)}`} icon={DollarSign} color="bg-emerald-50 text-emerald-600" />
        <StatCard title="Total Expenses" value={`SAR ${fmt(acc?.total_expenses)}`} icon={Receipt} color="bg-red-50 text-red-600" />
        <StatCard title="Net Profit" value={`SAR ${fmt(acc?.net_profit)}`} icon={TrendingUp} color="bg-teal-50 text-teal-600" />
        <StatCard title="Outstanding" value={`SAR ${fmt(acc?.outstanding_amount)}`} icon={Clock} color="bg-amber-50 text-amber-600" sub={`${acc?.paid_invoices ?? 0} paid invoices`} />
      </div>

      {/* Inventory */}
      <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">Inventory</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard title="Products" value={inv?.total_products} icon={Package} color="bg-orange-50 text-orange-600" />
        <StatCard title="Orders" value={inv?.total_orders} icon={Package} color="bg-sky-50 text-sky-600" />
        <StatCard title="Low Stock" value={inv?.low_stock_count} icon={AlertTriangle} color="bg-red-50 text-red-600" />
        <StatCard title="Pending Orders" value={inv?.pending_orders} icon={Clock} color="bg-yellow-50 text-yellow-600" />
      </div>

      {/* HR */}
      <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">HR</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Employees" value={hr?.total_employees} icon={UserCheck} color="bg-violet-50 text-violet-600" />
        <StatCard title="Pending Leaves" value={hr?.pending_leaves} icon={Clock} color="bg-pink-50 text-pink-600" />
        <StatCard title="Payroll Total" value={`SAR ${fmt(hr?.total_payroll)}`} icon={DollarSign} color="bg-lime-50 text-lime-600" />
      </div>
    </div>
  )
}
