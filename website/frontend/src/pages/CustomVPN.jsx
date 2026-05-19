import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, Zap, Server, ChevronRight, ChevronLeft, Check, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import client from '../api/client.js'
import useAuthStore from '../store/auth.js'
import ProviderBadge from '../components/ProviderBadge.jsx'
import AnimatedBackground from '../components/AnimatedBackground.jsx'

const STEPS = ['Тип VPN', 'Провайдеры', 'Конфигурация', 'Итог']

function StepIndicator({ current }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-10 overflow-x-auto py-2">
      {STEPS.map((label, i) => (
        <React.Fragment key={i}>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
              i < current
                ? 'bg-gradient-to-br from-primary to-secondary text-white'
                : i === current
                ? 'bg-primary/20 border-2 border-primary text-primary'
                : 'bg-[#1E1E2E] text-[#94A3B8]'
            }`}>
              {i < current ? <Check className="w-4 h-4" /> : i + 1}
            </div>
            <span className={`text-sm font-medium hidden sm:block ${
              i === current ? 'text-white' : i < current ? 'text-[#94A3B8]' : 'text-[#94A3B8]/50'
            }`}>
              {label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-8 h-px transition-all flex-shrink-0 ${i < current ? 'bg-primary' : 'bg-[#1E1E2E]'}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  )
}

export default function CustomVPN() {
  const [step, setStep] = useState(0)
  const [vpnType, setVpnType] = useState(null)
  const [selectedProviders, setSelectedProviders] = useState([])
  const [selectedPreset, setSelectedPreset] = useState(null)
  const [providers, setProviders] = useState([])
  const [presets, setPresets] = useState([])
  const [loading, setLoading] = useState(false)
  const { isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/register')
      return
    }
    client.get('/providers').then(r => setProviders(r.data)).catch(() => {})
    client.get('/providers/presets').then(r => setPresets(r.data)).catch(() => {})
  }, [isAuthenticated])

  const toggleProvider = (id) => {
    setSelectedProviders(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    )
  }

  const validateStep = () => {
    if (step === 0) {
      if (!vpnType) { toast.error('Выберите тип VPN'); return false }
    }
    if (step === 1) {
      if (vpnType === 'whitelist') {
        const ruProviders = selectedProviders.filter(id => {
          const p = providers.find(p => p.id === id)
          return p?.is_russian
        })
        const foreignProviders = selectedProviders.filter(id => {
          const p = providers.find(p => p.id === id)
          return !p?.is_russian
        })
        if (ruProviders.length < 1 || foreignProviders.length < 1) {
          toast.error('Для белых списков нужен 1 российский и 1 зарубежный провайдер')
          return false
        }
      } else {
        if (selectedProviders.length === 0) {
          toast.error('Выберите хотя бы одного провайдера')
          return false
        }
      }
    }
    if (step === 2) {
      if (!selectedPreset) { toast.error('Выберите конфигурацию сервера'); return false }
    }
    return true
  }

  const handleNext = () => {
    if (validateStep()) setStep(s => s + 1)
  }

  const handleBack = () => setStep(s => s - 1)

  const handlePay = async () => {
    setLoading(true)
    try {
      const res = await client.post('/payments/initiate', {
        type: 'custom_vpn',
        preset_id: selectedPreset,
        provider_ids: selectedProviders,
        vpn_type: vpnType,
      })
      navigate(`/payment/${res.data.payment_id}`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка создания платежа')
    } finally {
      setLoading(false)
    }
  }

  const selectedPresetObj = presets.find(p => p.id === selectedPreset)
  const selectedProviderObjs = providers.filter(p => selectedProviders.includes(p.id))

  const whitelistProviders = providers.filter(p => p.supports_whitelist)
  const ruProviders = providers.filter(p => p.is_russian)
  const foreignProviders = providers.filter(p => !p.is_russian)

  return (
    <div className="relative min-h-screen pt-24 pb-16">
      <AnimatedBackground />
      <div className="max-w-2xl mx-auto px-4 sm:px-6 relative z-10">

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="text-4xl font-extrabold text-white mb-2">
            Свой <span className="gradient-text">VPN сервер</span>
          </h1>
          <p className="text-[#94A3B8]">Выберите провайдеров и мощность по своим требованиям</p>
        </motion.div>

        <StepIndicator current={step} />

        <AnimatePresence mode="wait">
          {/* Step 0: VPN Type */}
          {step === 0 && (
            <motion.div
              key="step0"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.25 }}
            >
              <h2 className="text-xl font-bold text-white mb-6 text-center">Выберите тип VPN</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  {
                    value: 'whitelist',
                    icon: <Shield className="w-8 h-8" />,
                    title: 'Белые списки',
                    desc: 'Только заблокированные сайты через VPN. Максимальная скорость для российских ресурсов.',
                    color: 'from-purple-500/20 to-purple-900/20',
                    border: 'border-purple-500/30',
                    textColor: 'text-purple-400',
                  },
                  {
                    value: 'regular',
                    icon: <Zap className="w-8 h-8" />,
                    title: 'Обычный VPN',
                    desc: 'Весь трафик через VPN сервер. Полная анонимность и доступ к любым ресурсам.',
                    color: 'from-blue-500/20 to-blue-900/20',
                    border: 'border-blue-500/30',
                    textColor: 'text-blue-400',
                  },
                ].map(opt => (
                  <motion.button
                    key={opt.value}
                    onClick={() => setVpnType(opt.value)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={`p-6 rounded-xl border-2 text-left transition-all bg-gradient-to-br ${opt.color} ${
                      vpnType === opt.value
                        ? `${opt.border} ring-2 ring-primary/30`
                        : 'border-[#1E1E2E] hover:border-white/10'
                    }`}
                  >
                    <div className={`${opt.textColor} mb-3`}>{opt.icon}</div>
                    <h3 className="text-white font-bold mb-2">{opt.title}</h3>
                    <p className="text-[#94A3B8] text-sm">{opt.desc}</p>
                    {vpnType === opt.value && (
                      <div className="mt-3 flex items-center gap-1 text-xs text-primary font-medium">
                        <Check className="w-3 h-3" /> Выбрано
                      </div>
                    )}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 1: Providers */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.25 }}
            >
              <h2 className="text-xl font-bold text-white mb-2 text-center">Выберите провайдеров</h2>
              {vpnType === 'whitelist' && (
                <div className="flex items-start gap-2 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-3 mb-5 text-sm text-yellow-400">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  Для белых списков нужно выбрать минимум 1 российский и 1 зарубежный провайдер
                </div>
              )}

              {vpnType === 'whitelist' ? (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-[#94A3B8] mb-2">Российские серверы 🇷🇺</h3>
                    <div className="space-y-2">
                      {ruProviders.filter(p => p.supports_whitelist).map(p => (
                        <ProviderBadge
                          key={p.id}
                          provider={p}
                          selected={selectedProviders.includes(p.id)}
                          onClick={() => toggleProvider(p.id)}
                        />
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-[#94A3B8] mb-2">Зарубежные серверы 🌍</h3>
                    <div className="space-y-2">
                      {foreignProviders.filter(p => p.supports_whitelist).map(p => (
                        <ProviderBadge
                          key={p.id}
                          provider={p}
                          selected={selectedProviders.includes(p.id)}
                          onClick={() => toggleProvider(p.id)}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {providers.map(p => (
                    <ProviderBadge
                      key={p.id}
                      provider={p}
                      selected={selectedProviders.includes(p.id)}
                      onClick={() => toggleProvider(p.id)}
                    />
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* Step 2: Presets */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.25 }}
            >
              <h2 className="text-xl font-bold text-white mb-6 text-center">Конфигурация сервера</h2>
              {presets.length === 0 ? (
                <div className="text-center text-[#94A3B8] py-8">Нет доступных конфигураций</div>
              ) : (
                <div className="space-y-3">
                  {presets.map(preset => (
                    <motion.button
                      key={preset.id}
                      onClick={() => setSelectedPreset(preset.id)}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      className={`w-full p-4 rounded-xl border-2 text-left transition-all flex items-center justify-between ${
                        selectedPreset === preset.id
                          ? 'border-primary bg-primary/10'
                          : 'border-[#1E1E2E] bg-[#12121A] hover:border-white/10'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-[#0A0A0F] border border-[#1E1E2E] flex items-center justify-center">
                          <Server className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <div className="text-white font-medium text-sm">
                            {preset.ram_gb} ГБ RAM / {preset.cpu_count} vCPU
                          </div>
                          <div className="text-[#94A3B8] text-xs mt-0.5">Виртуальный сервер</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold gradient-text">{preset.price}₽</div>
                        <div className="text-[#94A3B8] text-xs">в месяц</div>
                      </div>
                    </motion.button>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* Step 3: Summary */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.25 }}
            >
              <h2 className="text-xl font-bold text-white mb-6 text-center">Ваш заказ</h2>
              <div className="vpn-card p-6 space-y-4">
                <div className="flex justify-between items-center py-3 border-b border-[#1E1E2E]">
                  <span className="text-[#94A3B8]">Тип VPN</span>
                  <span className="text-white font-medium">
                    {vpnType === 'whitelist' ? 'Белые списки' : 'Обычный VPN'}
                  </span>
                </div>
                <div className="py-3 border-b border-[#1E1E2E]">
                  <span className="text-[#94A3B8] block mb-2">Провайдеры</span>
                  <div className="flex flex-wrap gap-2">
                    {selectedProviderObjs.map(p => (
                      <span key={p.id} className="badge bg-primary/10 text-purple-300 border border-primary/20">
                        {p.name}
                      </span>
                    ))}
                  </div>
                </div>
                {selectedPresetObj && (
                  <>
                    <div className="flex justify-between items-center py-3 border-b border-[#1E1E2E]">
                      <span className="text-[#94A3B8]">Конфигурация</span>
                      <span className="text-white font-medium">
                        {selectedPresetObj.ram_gb} ГБ / {selectedPresetObj.cpu_count} vCPU
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-3">
                      <span className="text-[#94A3B8] font-semibold">Итого</span>
                      <span className="text-2xl font-bold gradient-text">{selectedPresetObj.price}₽/мес</span>
                    </div>
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex gap-3 mt-8">
          {step > 0 && (
            <button
              onClick={handleBack}
              className="btn-outline flex items-center gap-2 px-6 py-3 rounded-xl font-medium"
            >
              <ChevronLeft className="w-4 h-4" />
              Назад
            </button>
          )}
          {step < STEPS.length - 1 ? (
            <motion.button
              onClick={handleNext}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="btn-primary flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white"
            >
              Далее
              <ChevronRight className="w-4 h-4" />
            </motion.button>
          ) : (
            <motion.button
              onClick={handlePay}
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="btn-primary flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white disabled:opacity-50"
            >
              {loading ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                    className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                  />
                  Оформляем...
                </>
              ) : (
                <>Оплатить</>
              )}
            </motion.button>
          )}
        </div>
      </div>
    </div>
  )
}
