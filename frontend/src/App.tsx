import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './hooks/useAuth'
import Layout from './components/layout/Layout'
import LoginPage from './pages/LoginPage'
import Dashboard from './pages/Dashboard'
import Contacts from './modules/crm/Contacts'
import Products from './modules/inventory/Products'
import Invoices from './modules/accounting/Invoices'
import Employees from './modules/hr/Employees'

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30000 } } })

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

// Simple placeholder pages for routes not yet built out
const Placeholder = ({ title }: { title: string }) => (
  <div className="p-6"><h1 className="text-lg font-semibold text-gray-900 mb-2">{title}</h1>
    <p className="text-sm text-gray-500">Coming soon — backend API ready, connect your UI here.</p></div>
)

function App() {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
              <Route index element={<Dashboard />} />
              <Route path="crm/contacts" element={<Contacts />} />
              <Route path="crm/leads" element={<Placeholder title="Leads" />} />
              <Route path="crm/deals" element={<Placeholder title="Deals" />} />
              <Route path="inventory/products" element={<Products />} />
              <Route path="inventory/orders" element={<Placeholder title="Orders" />} />
              <Route path="accounting/invoices" element={<Invoices />} />
              <Route path="accounting/transactions" element={<Placeholder title="Transactions" />} />
              <Route path="hr/employees" element={<Employees />} />
              <Route path="hr/leaves" element={<Placeholder title="Leave Requests" />} />
              <Route path="hr/payroll" element={<Placeholder title="Payroll" />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
