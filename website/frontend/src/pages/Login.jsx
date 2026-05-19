import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Eye, EyeOff, Phone, Lock } from 'lucide-react'
import toast from 'react-hot-toast'
import client from '../api/client.js'
import useAuthStore from '../store/auth.js'
import AnimatedBackground from '../components/AnimatedBackground.jsx'
import Navbar from '../components/Navbar.jsx'

export default function Login() {
  const [form, setForm] = useState({ phone: '', password: '' })
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handlePhoneChange = (e) => {
    let val = e.target.value.replace(/[^\d+]/g, '')
    if (val.startsWith('8')) val = '+7' + val.slice(1)
    if (val && !val.startsWith('+')) val = '+7' + val
    if (val.length > 12) val = val.slice(0, 12)
    setForm({ ...form, phone: val })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.phone || !form.password) {
      toast.error('Заполните все поля')
      return
    }
    setLoading(true)
    try {
      const res = await client.post('/auth/login', form)
      login(res.data.access_token, res.data.user)
      toast.success('Добро пожаловать!')
      navigate('/account')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center px-4 pt-16">
      <Navbar />
      <AnimatedBackground />
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md relative z-10"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">Вход</h1>
          <p className="text-[#94A3B8] mt-2">Войдите в свой аккаунт ConfigVPN</p>
        </div>

        <div className="vpn-card p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[#E2E8F0] mb-2">Номер телефона</label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                <input
                  type="tel"
                  className="input-field pl-10"
                  placeholder="+7 999 000 00 00"
                  value={form.phone}
                  onChange={handlePhoneChange}
                  maxLength={12}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#E2E8F0] mb-2">Пароль</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                <input
                  type={showPw ? 'text' : 'password'}
                  className="input-field pl-10 pr-10"
                  placeholder="Введите пароль"
                  value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-white"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="btn-primary w-full py-3 rounded-xl font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                    className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                  />
                  Входим...
                </span>
              ) : 'Войти'}
            </motion.button>
          </form>

          <p className="text-center text-[#94A3B8] text-sm mt-6">
            Нет аккаунта?{' '}
            <Link to="/register" className="text-primary hover:text-purple-300 transition-colors font-medium">
              Зарегистрироваться
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
