import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import {
  LayoutDashboard, Users, TrendingUp, Package,
  Receipt, UserCheck, LogOut, Building2, ChevronRight
} from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/crm/contacts', icon: Users, label: 'Contacts' },
  { to: '/crm/leads', icon: TrendingUp, label: 'Leads' },
  { to: '/crm/deals', icon: TrendingUp, label: 'Deals' },
  { to: '/inventory/products', icon: Package, label: 'Products' },
  { to: '/inventory/orders', icon: Package, label: 'Orders' },
  { to: '/accounting/invoices', icon: Receipt, label: 'Invoices' },
  { to: '/accounting/transactions', icon: Receipt, label: 'Transactions' },
  { to: '/hr/employees', icon: UserCheck, label: 'Employees' },
  { to: '/hr/leaves', icon: UserCheck, label: 'Leave Requests' },
  { to: '/hr/payroll', icon: UserCheck, label: 'Payroll' },
]

const sections = [
  { label: 'Overview', items: nav.slice(0, 1) },
  { label: 'CRM', items: nav.slice(1, 4) },
  { label: 'Inventory', items: nav.slice(4, 6) },
  { label: 'Accounting', items: nav.slice(6, 8) },
  { label: 'HR & Payroll', items: nav.slice(8, 11) },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-gray-100 flex flex-col">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-4 border-b border-gray-100">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <Building2 className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-gray-900 text-sm">Knooz ERP</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4 px-3">
          {sections.map((section) => (
            <div key={section.label} className="mb-5">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider px-2 mb-1.5">
                {section.label}
              </p>
              {section.items.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) => clsx(
                    'flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-sm transition-colors mb-0.5',
                    isActive
                      ? 'bg-primary-50 text-primary-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-gray-100 p-3">
          <div className="flex items-center gap-2.5 px-2 py-1.5">
            <div className="w-7 h-7 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-medium text-primary-700">
                {user?.full_name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
            </div>
            <button onClick={handleLogout} className="text-gray-400 hover:text-gray-600 transition-colors">
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
