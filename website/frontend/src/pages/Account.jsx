import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Copy, Check, User, CreditCard, Gift, Plus, ExternalLink, Ban } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar.jsx'
import Footer from '../components/Footer.jsx'
import client from '../api/client.js'
import useAuthStore from '../store/auth.js'

const PAGE_TRANSITION = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.3 },
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast.success('Скопировано!')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Не удалось скопировать')
    }
  }
  return (
    <button onClick={handleCopy} className="p-1.5 rounded-lg hover:bg-white/5 text-[#94A3B8] hover:text-white transition-all flex-shrink-0" title="Скопировать">
      {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
    </button>
  )
}

function Spinner() {
  return (
    <div className="flex justify-center py-8">
      <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
    </div>
  )
}

function StatusBadge({ status }) {
  const map = {
    draft:     { cls: 'badge-inactive', label: 'Не завершён' },
    pending:   { cls: 'badge-pending',  label: 'Ожидает' },
    confirmed: { cls: 'badge-confirmed', label: 'Подтверждён' },
    rejected:  { cls: 'badge-rejected', label: 'Отклонён' },
  }
  const { cls, label } = map[status] || { cls: 'badge-inactive', label: status }
  return <span className={`badge ${cls}`}>{label}</span>
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export default function Account() {
  const { user, logout } = useAuthStore()
  const [isBanned, setIsBanned] = useState(false)
  const [subscriptions, setSubscriptions] = useState([])
  const [referral, setReferral] = useState(null)
  const [payments, setPayments] = useState([])
  const [loadingSubs, setLoadingSubs] = useState(true)
  const [loadingRef, setLoadingRef] = useState(true)
  const [loadingPay, setLoadingPay] = useState(true)

  useEffect(() => {
    // Check ban status in real time
    client.get('/auth/me')
      .then((r) => {
        if (r.data.is_blocked) {
          setIsBanned(true)
          logout()
        }
      })
      .catch(() => {})

    client.get('/subscriptions')
      .then((r) => setSubscriptions(r.data))
      .catch(() => {})
      .finally(() => setLoadingSubs(false))

    client.get('/referrals/stats')
      .then((r) => setReferral(r.data))
      .catch(() => {})
      .finally(() => setLoadingRef(false))

    client.get('/payments')
      .then((r) => setPayments(r.data))
      .catch(() => {})
      .finally(() => setLoadingPay(false))
  }, [])

  const referralLink = referral?.referral_code
    ? `${window.location.origin}/register?ref=${referral.referral_code}`
    : null

  if (isBanned) {
    return (
      <motion.div {...PAGE_TRANSITION}>
        <Navbar />
        <div className="min-h-screen flex items-center justify-center px-4">
          <div className="text-center max-w-md">
            <div className="w-20 h-20 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
              <Ban className="w-10 h-10 text-red-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">Аккаунт заблокирован</h2>
            <p className="text-[#94A3B8] leading-relaxed">
              Ваш аккаунт был заблокирован администратором. Если вы считаете это ошибкой, свяжитесь с поддержкой.
            </p>
          </div>
        </div>
        <Footer />
      </motion.div>
    )
  }

  return (
    <motion.div {...PAGE_TRANSITION}>
      <Navbar />
      <div className="min-h-screen pt-24 pb-20 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-white">Личный кабинет</h1>
              <p className="text-[#94A3B8] mt-1">Добро пожаловать, {user?.full_name || 'Пользователь'}!</p>
            </div>
            <Link to="/plans" className="btn-primary px-5 py-2.5 rounded-xl text-white text-sm font-medium flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Купить подписку
            </Link>
          </div>

          {/* Subscriptions */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="vpn-card p-6 mb-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                <User className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Подписки</h2>
                <p className="text-[#94A3B8] text-xs">Ваши активные VPN-подписки</p>
              </div>
            </div>

            {loadingSubs ? (
              <Spinner />
            ) : subscriptions.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-[#94A3B8] mb-4">Нет активных подписок</div>
                <Link to="/plans" className="btn-primary px-6 py-2.5 rounded-xl text-white text-sm font-medium inline-flex items-center gap-2">
                  <Plus className="w-4 h-4" />
                  Выбрать тариф
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {subscriptions.map((sub) => (
                  <div key={sub.id} className="bg-[#0A0A0F] rounded-xl p-4 border border-[#1E1E2E]">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`badge ${sub.is_active ? 'badge-active' : 'badge-inactive'}`}>
                            {sub.is_active ? 'Активна' : 'Неактивна'}
                          </span>
                          <span className="badge bg-primary/10 text-purple-300 border border-primary/20">
                            {sub.type === 'whitelist' ? 'Белый список' : 'Обычный'}
                          </span>
                        </div>
                        {sub.expires_at && (
                          <p className="text-[#94A3B8] text-sm">До {formatDate(sub.expires_at)}</p>
                        )}
                      </div>
                      {sub.traffic_gb > 0 && (
                        <div className="text-right">
                          <div className="text-white font-semibold">{(sub.traffic_gb - sub.used_gb).toFixed(1)} ГБ</div>
                          <div className="text-[#94A3B8] text-xs">осталось</div>
                        </div>
                      )}
                    </div>

                    {sub.subscription_url && (
                      <div>
                        <p className="text-[#94A3B8] text-xs mb-1.5">Ссылка для подключения:</p>
                        <div className="flex items-center gap-2 bg-[#1E1E2E]/60 rounded-lg px-3 py-2">
                          <code className="text-xs text-[#94A3B8] flex-1 truncate font-mono">{sub.subscription_url}</code>
                          <CopyButton text={sub.subscription_url} />
                          <a
                            href={sub.subscription_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 rounded-lg hover:bg-white/5 text-[#94A3B8] hover:text-white transition-all"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </motion.section>

          {/* Referral */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="vpn-card p-6 mb-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center">
                <Gift className="w-5 h-5 text-secondary" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Реферальная программа</h2>
                <p className="text-[#94A3B8] text-xs">Приглашайте друзей и получайте бонусы</p>
              </div>
            </div>

            {loadingRef ? (
              <Spinner />
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0A0A0F] rounded-xl p-4 border border-[#1E1E2E] text-center">
                    <div className="text-3xl font-bold gradient-text">{referral?.invited_count ?? 0}</div>
                    <div className="text-[#94A3B8] text-sm mt-1">Приглашено</div>
                  </div>
                  <div className="bg-[#0A0A0F] rounded-xl p-4 border border-[#1E1E2E] text-center">
                    <div className="text-3xl font-bold gradient-text">{referral?.bonus_gb ?? 0} ГБ</div>
                    <div className="text-[#94A3B8] text-sm mt-1">Бонус получено</div>
                  </div>
                </div>

                {referralLink && (
                  <div>
                    <p className="text-[#94A3B8] text-sm mb-2">Ваша реферальная ссылка:</p>
                    <div className="flex items-center gap-2 bg-[#0A0A0F] rounded-xl px-4 py-3 border border-[#1E1E2E]">
                      <span className="text-sm text-[#E2E8F0] flex-1 truncate font-mono">{referralLink}</span>
                      <CopyButton text={referralLink} />
                    </div>
                  </div>
                )}
              </div>
            )}
          </motion.section>

          {/* Payments */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="vpn-card p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center">
                <CreditCard className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">История платежей</h2>
                <p className="text-[#94A3B8] text-xs">Все ваши транзакции</p>
              </div>
            </div>

            {loadingPay ? (
              <Spinner />
            ) : payments.length === 0 ? (
              <p className="text-[#94A3B8] text-center py-6">История платежей пуста</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[#94A3B8] border-b border-[#1E1E2E]">
                      <th className="text-left py-3 pr-4 font-medium">Дата</th>
                      <th className="text-left py-3 pr-4 font-medium">Тип</th>
                      <th className="text-left py-3 pr-4 font-medium">Сумма</th>
                      <th className="text-left py-3 font-medium">Статус</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1E1E2E]">
                    {payments.map((pay) => (
                      <tr key={pay.id} className="hover:bg-white/2 transition-colors">
                        <td className="py-3 pr-4 text-[#94A3B8]">{formatDate(pay.created_at)}</td>
                        <td className="py-3 pr-4 text-[#E2E8F0]">
                          {pay.type === 'subscription' ? 'Подписка' : 'Свой VPN'}
                        </td>
                        <td className="py-3 pr-4 text-[#E2E8F0] font-medium">{pay.amount}₽</td>
                        <td className="py-3">
                          {pay.status === 'draft' ? (
                            <Link
                              to={`/payment/${pay.id}`}
                              className="badge badge-inactive hover:border-primary/50 hover:text-purple-300 transition-colors"
                            >
                              Не завершён →
                            </Link>
                          ) : (
                            <StatusBadge status={pay.status} />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </motion.section>
        </div>
      </div>
      <Footer />
    </motion.div>
  )
}
