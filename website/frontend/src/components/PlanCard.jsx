import React from 'react'
import { motion } from 'framer-motion'
import { Check, Zap, Shield, Clock, Wifi } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth.js'

function formatTraffic(gb) {
  if (!gb || gb === 0) return 'Безлимит'
  return `${gb} ГБ`
}

export default function PlanCard({ plan, index = 0, featured = false }) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  const handleBuy = () => {
    if (!isAuthenticated) {
      navigate('/register')
      return
    }
    navigate(`/plans?buy=${plan.id}`)
  }

  const isWhitelist = plan.type === 'whitelist'

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      whileHover={{ scale: 1.02, y: -4 }}
      className={`vpn-card p-6 relative overflow-hidden ${
        featured ? 'border-primary/60 shadow-lg shadow-primary/10' : ''
      }`}
    >
      {/* Featured badge */}
      {featured && (
        <div className="absolute top-0 right-0">
          <div className="bg-gradient-to-r from-primary to-secondary text-white text-xs font-semibold px-3 py-1 rounded-bl-xl">
            Популярный
          </div>
        </div>
      )}

      {/* Type badge */}
      <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium mb-4 ${
        isWhitelist
          ? 'bg-primary/15 text-purple-300 border border-primary/30'
          : 'bg-secondary/15 text-blue-300 border border-secondary/30'
      }`}>
        {isWhitelist ? <Shield className="w-3 h-3" /> : <Zap className="w-3 h-3" />}
        {isWhitelist ? 'Белый список' : 'Обычный VPN'}
      </div>

      <h3 className="text-xl font-bold text-white mb-2">{plan.name}</h3>
      <p className="text-[#94A3B8] text-sm mb-6 leading-relaxed">{plan.description}</p>

      {/* Price */}
      <div className="mb-6">
        <span className="text-4xl font-bold gradient-text">{plan.price}₽</span>
        <span className="text-[#94A3B8] text-sm ml-2">/ {plan.duration_days} дней</span>
      </div>

      {/* Features */}
      <ul className="space-y-3 mb-6">
        <li className="flex items-center gap-2 text-sm text-[#E2E8F0]">
          <Wifi className="w-4 h-4 text-primary flex-shrink-0" />
          <span>Трафик: {formatTraffic(plan.traffic_gb)}</span>
        </li>
        {plan.monthly_traffic_gb > 0 && (
          <li className="flex items-center gap-2 text-sm text-[#E2E8F0]">
            <Clock className="w-4 h-4 text-primary flex-shrink-0" />
            <span>{plan.monthly_traffic_gb} ГБ/месяц</span>
          </li>
        )}
        <li className="flex items-center gap-2 text-sm text-[#E2E8F0]">
          <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
          <span>До {plan.max_connections} устройств</span>
        </li>
        {isWhitelist && (
          <li className="flex items-center gap-2 text-sm text-[#E2E8F0]">
            <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
            <span>Только заблокированные сайты</span>
          </li>
        )}
        <li className="flex items-center gap-2 text-sm text-[#E2E8F0]">
          <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
          <span>Без логов активности</span>
        </li>
      </ul>

      {/* CTA */}
      <motion.button
        onClick={handleBuy}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`w-full py-3 rounded-xl font-semibold text-sm transition-all ${
          featured
            ? 'btn-primary text-white'
            : 'btn-outline text-[#E2E8F0] hover:border-primary'
        }`}
      >
        Купить
      </motion.button>
    </motion.div>
  )
}
