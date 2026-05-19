import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { lazy, Suspense } from 'react'
import useAuthStore from './store/auth.js'
import { Navigate } from 'react-router-dom'

// Public pages
const Landing = lazy(() => import('./pages/Landing.jsx'))
const Login = lazy(() => import('./pages/Login.jsx'))
const Register = lazy(() => import('./pages/Register.jsx'))
const Plans = lazy(() => import('./pages/Plans.jsx'))
const CustomVPN = lazy(() => import('./pages/CustomVPN.jsx'))

// Protected pages
const Account = lazy(() => import('./pages/Account.jsx'))
const Payment = lazy(() => import('./pages/Payment.jsx'))

// Admin pages
const AdminLogin = lazy(() => import('./pages/admin/AdminLogin.jsx'))
const AdminLayout = lazy(() => import('./pages/admin/AdminLayout.jsx'))
const Dashboard = lazy(() => import('./pages/admin/Dashboard.jsx'))
const AdminUsers = lazy(() => import('./pages/admin/Users.jsx'))
const AdminPayments = lazy(() => import('./pages/admin/Payments.jsx'))
const AdminPlans = lazy(() => import('./pages/admin/Plans.jsx'))
const AdminProviders = lazy(() => import('./pages/admin/Providers.jsx'))
const AdminSettings = lazy(() => import('./pages/admin/Settings.jsx'))

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg">
      <div className="spinner" />
    </div>
  )
}

function ProtectedRoute({ children }) {
  const { token } = useAuthStore()
  if (!token) return <Navigate to="/login" replace />
  return children
}

function AdminRoute({ children }) {
  const adminToken = localStorage.getItem('adminToken')
  if (!adminToken) return <Navigate to="/admin/login" replace />
  return children
}

export default function App() {
  const location = useLocation()

  return (
    <Suspense fallback={<Spinner />}>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          {/* Public routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/plans" element={<Plans />} />
          <Route path="/custom-vpn" element={<CustomVPN />} />

          {/* Protected routes */}
          <Route path="/account" element={<ProtectedRoute><Account /></ProtectedRoute>} />
          <Route path="/payment/:id" element={<ProtectedRoute><Payment /></ProtectedRoute>} />

          {/* Admin routes */}
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<AdminRoute><AdminLayout /></AdminRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="payments" element={<AdminPayments />} />
            <Route path="plans" element={<AdminPlans />} />
            <Route path="providers" element={<AdminProviders />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </Suspense>
  )
}
