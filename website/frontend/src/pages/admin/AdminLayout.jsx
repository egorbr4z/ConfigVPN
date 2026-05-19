import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard, Users, CreditCard, Package,
  Globe, Settings, LogOut, Shield, Menu, X
} from 'lucide-react'
import { useState } from 'react'

const links = [
  { to: '/admin', label: 'Дашборд', icon: LayoutDashboard, end: true },
  { to: '/admin/users', label: 'Пользователи', icon: Users },
  { to: '/admin/payments', label: 'Платежи', icon: CreditCard },
  { to: '/admin/plans', label: 'Тарифы', icon: Package },
  { to: '/admin/providers', label: 'Провайдеры', icon: Globe },
  { to: '/admin/settings', label: 'Настройки', icon: Settings },
]

export default function AdminLayout() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const logout = () => {
    localStorage.removeItem('adminToken')
    navigate('/admin/login')
  }

  const Sidebar = ({ mobile }) => (
    <aside className={`${mobile ? 'flex' : 'hidden lg:flex'} flex-col w-60 min-h-screen bg-[#12121A] border-r border-[#1E1E2E] p-4`}>
      <div className="flex items-center gap-3 px-2 mb-8">
        <div className="w-9 h-9 rounded-xl btn-primary flex items-center justify-center shrink-0">
          <Shield size={18} />
        </div>
        <span className="font-bold text-base">VPN Admin</span>
      </div>

      <nav className="flex-1 space-y-1">
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'bg-purple-600/20 text-purple-400 border border-purple-600/30'
                  : 'text-[#94A3B8] hover:text-[#E2E8F0] hover:bg-[#1E1E2E]'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={logout}
        className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-[#94A3B8] hover:text-red-400 hover:bg-red-500/10 transition-all mt-4"
      >
        <LogOut size={17} />
        Выйти
      </button>
    </aside>
  )

  return (
    <div className="flex min-h-screen bg-[#0A0A0F]">
      <Sidebar />

      {/* Mobile overlay */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <motion.div
            initial={{ x: -240 }}
            animate={{ x: 0 }}
            exit={{ x: -240 }}
            className="absolute left-0 top-0 h-full w-60"
          >
            <Sidebar mobile />
          </motion.div>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile topbar */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-[#1E1E2E] bg-[#12121A]">
          <button onClick={() => setOpen(true)} className="text-[#94A3B8]">
            <Menu size={22} />
          </button>
          <span className="font-semibold text-sm">VPN Admin</span>
        </div>

        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
