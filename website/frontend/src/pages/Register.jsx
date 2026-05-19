import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Eye, EyeOff, Phone, Lock, User } from 'lucide-react'
import toast from 'react-hot-toast'
import client from '../api/client.js'
import useAuthStore from '../store/auth.js'
import AnimatedBackground from '../components/AnimatedBackground.jsx'

const PAGE_TRANSITION = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.3 },
}

export default function Register() {
  const [form, setForm] = useState({ phone: '', full_name: '', password: '', confirm_password: '', referral_code: '' })
  const [showPw, setShowPw] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})
  const { login } = useAuthStore()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const ref = searchParams.get('ref')
    if (ref) setForm(f => ({ ...f, referral_code: ref }))
  }, [searchParams])

  const validate = () => {
    const errs = {}
    if (!form.phone) errs.phone = 'Введите номер телефона'
    else if (!/^\+?[78]\d{10}$/.test(form.phone.replace(/\s/g, ''))) errs.phone = 'Введите корректный номер (+7XXXXXXXXXX)'
    if (!form.full_name) errs.full_name = 'Введите имя'
    if (!form.password) errs.password = 'Введите пароль'
    else if (form.password.length < 6) errs.password = 'Пароль минимум 6 символов'
    if (form.password !== form.confirm_password) errs.confirm_password = 'Пароли не совпадают'
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setLoading(true)
    try {
      const body = {
        phone: form.phone.replace(/\s/g, ''),
        full_name: form.full_name,
        password: form.password,
      }
      if (form.referral_code) body.referral_code = form.referral_code
      const res = await client.post('/auth/register', body)
      login(res.data.access_token, res.data.user)
      toast.success('Аккаунт создан!')
      navigate('/account')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка регистрации')
    } finally {
      setLoading(false)
    }
  }

  const field = (name) => ({
    value: form[name],
    onChange: (e) => {
      setForm({ ...form, [name]: e.target.value })
      if (errors[name]) setErrors({ ...errors, [name]: '' })
    },
  })

  return (
    <motion.div {...PAGE_TRANSITION} className="relative min-h-screen flex items-center justify-center px-4 py-20">
      <AnimatedBackground />
      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">Регистрация</h1>
          <p className="text-[#94A3B8] mt-2">Создайте аккаунт ConfigVPN</p>
        </div>

        <div className="vpn-card p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Phone */}
            <div>
              <label className="block text-sm font-medium text-[#E2E8F0] mb-1.5">Номер телефона</label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                <input
                  type="tel"
                  className={`input-field pl-10 ${errors.phone ? 'border-red-500 focus:border-red-500' : ''}`}
                  placeholder="+79991234567"
                  {...field('phone')}
                />
              </div>
              {errors.phone && <p className="text-red-400 text-xs mt-1">{errors.phone}</p>}
            </div>

            {/* Full name */}
            <div>
              <label className="block text-sm font-medium text-[#E2E8F0] mb-1.5">Имя</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                <input
                  type="text"
                  className={`input-field pl-10 ${errors.full_name ? 'border-red-500 focus:border-red-500' : ''}`}
                  placeholder="Иван Иванов"
                  {...field('full_name')}
                />
              </div>
              {errors.full_name && <p className="text-red-400 text-xs mt-1">{errors.full_name}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-[#E2E8F0] mb-1.5">Пароль</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                <input
                  type={showPw ? 'text' : 'password'}
                  className={`input-field pl-10 pr-10 ${errors.password ? 'border-red-500 focus:border-red-500' : ''}`}
                  placeholder="Минимум 6 символов"
                  {...field('password')}
                />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-white">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password}</p>}
            </div>

            {/* Confirm password */}
            <div>
              <label className="block text-sm font-medium text-[#E2E8F0] mb-1.5">Подтвердите пароль</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94A3B8]" />
                <input
                  type={showConfirm ? 'text' : 'password'}
                  className={`input-field pl-10 pr-10 ${errors.confirm_password ? 'border-red-500 focus:border-red-500' : ''}`}
                  placeholder="Повторите пароль"
                  {...field('confirm_password')}
                />
                <button type="button" onClick={() => setShowConfirm(!showConfirm)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-white">
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.confirm_password && <p className="text-red-400 text-xs mt-1">{errors.confirm_password}</p>}
            </div>

            {/* Referral */}
            <div>
              <label className="block text-sm font-medium text-[#E2E8F0] mb-1.5">
                Реферальный код <span className="text-[#94A3B8] font-normal">(необязательно)</span>
              </label>
              <input
                type="text"
                className="input-field uppercase tracking-widest"
                placeholder="ABCD1234"
                value={form.referral_code}
                onChange={(e) => setForm({ ...form, referral_code: e.target.value.toUpperCase() })}
              />
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="btn-primary w-full py-3 rounded-xl font-semibold text-white mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }} className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
                  Создаём аккаунт...
                </span>
              ) : 'Создать аккаунт'}
            </motion.button>
          </form>

          <p className="text-center text-[#94A3B8] text-sm mt-6">
            Уже есть аккаунт?{' '}
            <Link to="/login" className="text-primary hover:text-purple-300 transition-colors font-medium">
              Войти
            </Link>
          </p>
        </div>
      </div>
    </motion.div>
  )
}
