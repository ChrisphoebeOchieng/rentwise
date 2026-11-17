import './App.css'
import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './pages/auth/Login'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminLayout from './layouts/AdminLayout'
import Properties from './pages/properties/Properties'
import AdminSections from './pages/admin/AdminSections'
import AdminReports from './pages/admin/AdminReports'

function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth()

  if (loading) return <div className="app-loading">Loading RentWise...</div>
  if (!user) return <Navigate to="/login" replace />

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />
  }

  return children
}

function Dashboard({ role }) {
  const { user, logout } = useAuth()

  return (
    <main className="dashboard-main">
      <header className="section-heading">
        <div>
          <p className="eyebrow">RENTWISE WORKSPACE</p>
          <h1>Welcome, {user.full_name}</h1>
          <p>{role} dashboard</p>
        </div>
        <button className="gold-button" onClick={logout}>Sign out</button>
      </header>
      <section className="content-panel">
        <h2>{role} workspace</h2>
        <p>Your account is authenticated. We're connecting your dashboard modules next.</p>
      </section>
    </main>
  )
}

function AdminPlaceholder() {
  const { section } = useParams()
  const titles = {
    applications: 'Applications',
    tenancies: 'Tenancies',
    payments: 'Payments',
    maintenance: 'Maintenance',
    notifications: 'Notifications',
    reports: 'Reports',
  }

  return (
    <section className="content-panel">
      <p className="eyebrow">RENTWISE MANAGEMENT</p>
      <h1>{titles[section] || 'Admin workspace'}</h1>
      <p>This section is ready for its management interface.</p>
    </section>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/admin"
        element={
          <ProtectedRoute roles={['Administrator']}>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="properties" element={<Properties />} />
        <Route path="reports" element={<AdminReports />} />
        <Route path=":section" element={<AdminSections />} />
      </Route>

      <Route path="/landlord" element={
        <ProtectedRoute roles={['Landlord']}>
          <Dashboard role="Landlord" />
        </ProtectedRoute>
      } />

      <Route path="/manager" element={
        <ProtectedRoute roles={['Property Manager']}>
          <Dashboard role="Property Manager" />
        </ProtectedRoute>
      } />

      <Route path="/tenant" element={
        <ProtectedRoute roles={['Tenant']}>
          <Dashboard role="Tenant" />
        </ProtectedRoute>
      } />

      <Route path="/unauthorized" element={
        <main className="dashboard-main">
          <h1>Access denied</h1>
          <p>You do not have permission to view this page.</p>
        </main>
      } />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
