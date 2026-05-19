import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CreditCard, Phone, CheckCircle, ArrowLeft, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar.jsx'
import client from '../api/client.js'

const PAGE_TRANSITION = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.3 },
}

function Spinner() {
  return (
    <div className="flex justify-center py-20">
      <div className="w-10 h-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
    </div>
  )
}

export default function Payment() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  const [payment, setPayment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [initiating, setInitiating] = useState(false)
  const [last4, setLast4] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    // If id === 'new', initiate the payment first
    if (id === 'new') {
      const state = location.state
      if (!state || !state.type) {
        navigate('/plans')
        return
      }
      setInitiating(true)
      client.post('/payments/initiate', state)
        .then((r) => {
          setPayment(r.data)
        })
        .catch((err) => {
          toast.error(err.response?.data?.detail || 'Не удалось создать платёж')
          navigate('/plans')
        })
        .finally(() => {
          setInitiating(false)
          setLoading(false)
        })
    } else {
      // Load existing payment
      client.get(`/payments/${id}`)
        .then((r) => {
          setPayment(r.data)
          if (r.data.last4) setConfirmed(true)
        })
        .catch(() => {
          toast.error('Платёж не найден')
          navigate('/account')
        })
        .finally(() => setLoading(false))
    }
  }, [id])

  useEffect(() => {
    if (payment && inputRef.current && !confirmed) {
      setTimeout(() => inputRef.current?.focus(), 200)
    }
  }, [payment, confirmed])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (last4.length !== 4) {
      setError('Введите ровно 4 цифры')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const paymentId = payment.payment_id || payment.id
      await client.post(`/payments/${paymentId}/confirm-last4`, { last4 })
      setConfirmed(true)
      toast.success('Данные приняты!')
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при отправке данных')
    } finally {
      setSubmitting(false)
    }
  }

  const requisite = payment?.requisite
  const isCard = requisite?.type === 'card'

  return (
    <motion.div {...PAGE_TRANSITION}>
      <Navbar />
      <div className="min-h-screen pt-24 pb-20 px-4 sm:px-6">
        <div className="max-w-lg mx-auto">
          <button
            onClick={() => navigate('/account')}
            className="flex items-center gap-2 text-[#94A3B8] hover:text-white transition-colors mb-8 text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Назад в личный кабинет
          </button>

          {loading || initiating ? (
            <Spinner />
          ) : confirmed ? (
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5 }}
              className="vpn-card p-8 text-center"
            >
              <div className="w-20 h-20 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-green-400" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">Данные приняты!</h2>
              <p className="text-[#94A3B8] leading-relaxed mb-8">
                Ожидайте подтверждения администратора. Обычно это занимает до 30 минут. После подтверждения ссылка для подключения появится в личном кабинете.
              </p>
              <button
                onClick={() => navigate('/account')}
                className="btn-primary px-8 py-3 rounded-xl text-white font-semibold"
              >
                В личный кабинет
              </button>
            </motion.div>
          ) : payment ? (
            <div className="vpn-card p-8">
              <h1 className="text-2xl font-bold text-white mb-2">Оплата</h1>
              <p className="text-[#94A3B8] mb-8">Переведите указанную сумму и подтвердите платёж</p>

              {/* Amount */}
              <div className="bg-[#0A0A0F] rounded-2xl p-6 border border-[#1E1E2E] mb-6 text-center">
                <p className="text-[#94A3B8] text-sm mb-2">Сумма к оплате</p>
                <p className="text-5xl font-bold gradient-text">{payment.amount}₽</p>
              </div>

              {/* Requisite */}
              {requisite && (
                <div className="bg-[#0A0A0F] rounded-2xl p-6 border border-[#1E1E2E] mb-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                      {isCard ? <CreditCard className="w-5 h-5 text-primary" /> : <Phone className="w-5 h-5 text-primary" />}
                    </div>
                    <div>
                      <p className="text-white font-medium">{isCard ? 'Перевод на карту' : 'Перевод по телефону (СБП)'}</p>
                      {requisite.holder_name && (
                        <p className="text-[#94A3B8] text-sm">{requisite.holder_name}</p>
                      )}
                    </div>
                  </div>
                  <div className="bg-[#1E1E2E] rounded-xl p-4 text-center">
                    <p className="text-2xl font-bold text-white tracking-widest">{requisite.value}</p>
                  </div>
                </div>
              )}

              {/* Instructions */}
              <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 mb-6">
                <p className="text-purple-300 text-sm font-medium mb-2">Инструкция:</p>
                <ol className="text-[#94A3B8] text-sm space-y-1">
                  <li>1. Переведите <strong className="text-white">{payment.amount}₽</strong> на указанные реквизиты</li>
                  <li>2. Введите последние 4 цифры {isCard ? 'карты, с которой платили' : 'телефона отправителя'}</li>
                  <li>3. Нажмите «Подтвердить оплату»</li>
                </ol>
              </div>

              {/* Last4 input */}
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-[#E2E8F0] mb-2">
                    Последние 4 цифры {isCard ? 'вашей карты' : 'вашего телефона'}
                  </label>
                  <input
                    ref={inputRef}
                    type="text"
                    inputMode="numeric"
                    maxLength={4}
                    pattern="[0-9]{4}"
                    className={`input-field text-center text-2xl font-bold tracking-[0.5em] ${error ? 'border-red-500' : ''}`}
                    placeholder="XXXX"
                    value={last4}
                    onChange={(e) => {
                      const v = e.target.value.replace(/\D/g, '').slice(0, 4)
                      setLast4(v)
                      if (error) setError('')
                    }}
                  />
                  {error && (
                    <div className="flex items-center gap-1 mt-2 text-red-400 text-xs">
                      <AlertCircle className="w-3 h-3" />
                      {error}
                    </div>
                  )}
                </div>

                <motion.button
                  type="submit"
                  disabled={submitting || last4.length !== 4}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className="btn-primary w-full py-4 rounded-xl font-semibold text-white text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }} className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full" />
                      Отправляем...
                    </span>
                  ) : 'Подтвердить оплату'}
                </motion.button>
              </form>
            </div>
          ) : null}
        </div>
      </div>
    </motion.div>
  )
}
