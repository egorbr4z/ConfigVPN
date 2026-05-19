import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Lock, User } from 'lucide-react'
import { adminClient } from '../../api/client.js'
import toast from 'react-hot-toast'

export default function AdminLogin() {
  const [form, setForm] = useState({ username: '', password: '' })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await adminClient.post('/auth/admin-login', form)
      localStorage.setItem('adminToken', res.data.access_token)
      toast.success('Добро пожаловать!')
      navigate('/admin')
    } catch {
      toast.error('Неверный логин или пароль')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0F] px-4">
      <div className="absolute inset-0 pointer-events-none">
        <div className="orb-1 absolute top-1/4 left-1/4 w-72 h-72 rounded-full bg-purple-600/10 blur-3xl" />
        <div className="orb-2 absolute bottom-1/4 right-1/4 w-72 h-72 rounded-full bg-blue-600/10 blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="vpn-card p-8 w-full max-w-sm relative"
      >
        <div className="flex justify-center mb-6">
          <div className="w-14 h-14 rounded-2xl btn-primary flex items-center justify-center">
            <Lock size={24} />
          </div>
        </div>

        <h1 className="text-xl font-bold text-center mb-1">Панель управления</h1>
        <p className="text-[#94A3B8] text-sm text-center mb-6">Введите данные администратора</p>

        <form onSubmit={submit} className="space-y-4">
          <div className="relative">
            <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
            <input
              className="input-field pl-9"
              placeholder="Логин"
              value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              required
            />
          </div>
          <div className="relative">
            <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
            <input
              type="password"
              className="input-field pl-9"
              placeholder="Пароль"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 rounded-xl font-semibold text-sm"
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </motion.div>
    </div>
  )
}
