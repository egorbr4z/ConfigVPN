import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, Zap, X, Check } from 'lucide-react'
import toast from 'react-hot-toast'
import client from '../api/client.js'
import useAuthStore from '../store/auth.js'
import PlanCard from '../components/PlanCard.jsx'
import AnimatedBackground from '../components/AnimatedBackground.jsx'

function BuyModal({ plan, onClose, onSuccess }) {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleBuy = async () => {
    setLoading(true)
    try {
      const res = await client.post('/payments/initiate', {
        type: 'subscription',
        plan_id: plan.id,
      })
      onSuccess(res.data.payment_id)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка создания платежа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/60 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        className="vpn-card p-8 max-w-md w-full"
      >
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-white">{plan.name}</h2>
            <p className="text-[#94A3B8] text-sm mt-1">{plan.description}</p>
          </div>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-white transition-colors ml-4">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-[#0A0A0F]/50 rounded-xl p-4 mb-6 border border-[#1E1E2E]">
          <div className="flex justify-between items-center">
            <span className="text-[#94A3B8]">Стоимость</span>
            <span className="text-2xl font-bold gradient-text">{plan.price}₽</span>
          </div>
          <div className="flex justify-between items-center mt-2">
            <span className="text-[#94A3B8] text-sm">Срок</span>
            <span className="text-sm text-[#E2E8F0]">{plan.duration_days} дней</span>
          </div>
          <div className="flex justify-between items-center mt-2">
            <span className="text-[#94A3B8] text-sm">Трафик</span>
            <span className="text-sm text-[#E2E8F0]">{plan.traffic_gb > 0 ? `${plan.traffic_gb} ГБ` : 'Безлимит'}</span>
          </div>
        </div>

        <ul className="space-y-2 mb-6">
          {[
            'Оплата переводом на карту/СБП',
            'Подтверждение в течение 30 минут',
            'Ссылка для подключения сразу после подтверждения',
          ].map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-[#94A3B8]">
              <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
              {item}
            </li>
          ))}
        </ul>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 btn-outline py-3 rounded-xl text-sm font-medium">
            Отмена
          </button>
          <motion.button
            onClick={handleBuy}
            disabled={loading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex-1 btn-primary py-3 rounded-xl text-sm font-semibold text-white disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                />
                Оформляем...
              </span>
            ) : 'Перейти к оплате'}
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default function Plans() {
  const [plans, setPlans] = useState([])
  const [activeTab, setActiveTab] = useState('whitelist')
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    client.get('/plans').then(r => {
      setPlans(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  // Auto-open modal if ?buy=planId
  useEffect(() => {
    const buyId = searchParams.get('buy')
    if (buyId && plans.length > 0) {
      const plan = plans.find(p => p.id === buyId)
      if (plan) setSelectedPlan(plan)
    }
  }, [searchParams, plans])

  const handleBuyClick = (plan) => {
    if (!isAuthenticated) {
      navigate('/register')
      return
    }
    setSelectedPlan(plan)
  }

  const filteredPlans = plans.filter(p => p.type === activeTab)

  return (
    <div className="relative min-h-screen pt-24 pb-16">
      <AnimatedBackground />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl font-extrabold text-white mb-4">
            Выберите <span className="gradient-text">тариф</span>
          </h1>
          <p className="text-[#94A3B8] text-lg max-w-2xl mx-auto">
            Гибкие планы для любых потребностей. Подключение сразу после оплаты.
          </p>
        </motion.div>

        {/* Tabs */}
        <div className="flex justify-center mb-10">
          <div className="inline-flex rounded-xl border border-[#1E1E2E] bg-[#12121A] p-1">
            {[
              { value: 'whitelist', label: 'С белыми списками', icon: <Shield className="w-4 h-4" /> },
              { value: 'regular', label: 'Обычный VPN', icon: <Zap className="w-4 h-4" /> },
            ].map(tab => (
              <button
                key={tab.value}
                onClick={() => setActiveTab(tab.value)}
                className={`flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.value
                    ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-lg shadow-primary/20'
                    : 'text-[#94A3B8] hover:text-white'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
              className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full"
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {filteredPlans.map((plan, i) => (
              <div key={plan.id} onClick={() => handleBuyClick(plan)} className="cursor-pointer">
                <PlanCard plan={plan} index={i} featured={i === 0} />
              </div>
            ))}
            {filteredPlans.length === 0 && (
              <div className="col-span-2 text-center text-[#94A3B8] py-16">
                <Shield className="w-16 h-16 text-[#1E1E2E] mx-auto mb-4" />
                <p>Нет доступных тарифов</p>
              </div>
            )}
          </div>
        )}
      </div>

      <AnimatePresence>
        {selectedPlan && (
          <BuyModal
            plan={selectedPlan}
            onClose={() => setSelectedPlan(null)}
            onSuccess={(paymentId) => {
              setSelectedPlan(null)
              navigate(`/payment/${paymentId}`)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
