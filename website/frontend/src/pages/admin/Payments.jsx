import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { adminClient } from '../../api/client.js'
import toast from 'react-hot-toast'

const TABS = [
  { key: 'pending', label: 'Ожидают' },
  { key: 'confirmed', label: 'Подтверждены' },
  { key: 'rejected', label: 'Отклонены' },
]

function StatusBadge({ status }) {
  const map = { pending: 'badge-pending', confirmed: 'badge-confirmed', rejected: 'badge-rejected' }
  const labels = { pending: 'Ожидает', confirmed: 'Подтверждён', rejected: 'Отклонён' }
  return <span className={`badge ${map[status] || ''}`}>{labels[status] || status}</span>
}

function ConfirmModal({ payment, onClose, onDone }) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    if (!url.startsWith('http')) return toast.error('Введите корректную ссылку')
    setLoading(true)
    try {
      await adminClient.post(`/admin/payments/${payment.id}/confirm`, { subscription_url: url })
      toast.success('Платёж подтверждён')
      onDone()
    } catch { toast.error('Ошибка') } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="vpn-card p-6 w-full max-w-md relative z-10"
      >
        <h3 className="font-bold text-lg mb-1">Подтвердить платёж</h3>
        <p className="text-[#94A3B8] text-sm mb-4">ID: {payment.id.slice(0, 16)}… · {payment.amount} ₽</p>
        <label className="block text-sm text-[#94A3B8] mb-2">Ссылка на подписку (https://...)</label>
        <input
          className="input-field mb-4"
          placeholder="https://..."
          value={url}
          onChange={e => setUrl(e.target.value)}
        />
        <div className="flex gap-3">
          <button onClick={onClose} className="btn-outline flex-1 py-2.5 rounded-xl text-sm">Отмена</button>
          <button onClick={submit} disabled={loading} className="btn-primary flex-1 py-2.5 rounded-xl text-sm font-semibold">
            {loading ? 'Отправка...' : 'Подтвердить'}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

function RejectModal({ payment, onClose, onDone }) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setLoading(true)
    try {
      await adminClient.post(`/admin/payments/${payment.id}/reject`, { reason })
      toast.success('Платёж отклонён')
      onDone()
    } catch { toast.error('Ошибка') } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="vpn-card p-6 w-full max-w-md relative z-10"
      >
        <h3 className="font-bold text-lg mb-4">Отклонить платёж</h3>
        <textarea
          className="input-field mb-4 resize-none h-24"
          placeholder="Причина отклонения (будет отправлена пользователю)..."
          value={reason}
          onChange={e => setReason(e.target.value)}
        />
        <div className="flex gap-3">
          <button onClick={onClose} className="btn-outline flex-1 py-2.5 rounded-xl text-sm">Отмена</button>
          <button onClick={submit} disabled={loading} className="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all">
            {loading ? 'Отправка...' : 'Отклонить'}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

function PaymentRow({ payment, onUpdate }) {
  const [open, setOpen] = useState(false)
  const [confirmModal, setConfirmModal] = useState(false)
  const [rejectModal, setRejectModal] = useState(false)

  const done = () => { setConfirmModal(false); setRejectModal(false); onUpdate() }
  const d = payment.product_details || {}
  const isCustomVPN = payment.type === 'custom_vpn'
  const vpnTypeLabel = d.vpn_type === 'whitelist' ? 'Белый список' : 'Обычный'
  const productLabel = d.plan_name
    ? d.plan_name
    : isCustomVPN
      ? `Свой VPN (${vpnTypeLabel})`
      : '—'

  return (
    <>
      <AnimatePresence>
        {confirmModal && <ConfirmModal payment={payment} onClose={() => setConfirmModal(false)} onDone={done} />}
        {rejectModal && <RejectModal payment={payment} onClose={() => setRejectModal(false)} onDone={done} />}
      </AnimatePresence>

      <div className="vpn-card overflow-hidden">
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center gap-4 p-4 text-left hover:bg-[#1E1E2E]/40 transition-colors"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="font-semibold">{payment.amount} ₽</span>
              <StatusBadge status={payment.status} />
            </div>
            <div className="text-[#94A3B8] text-sm truncate">{productLabel}</div>
          </div>
          <div className="text-[#94A3B8] text-xs shrink-0">{payment.created_at?.slice(0, 10)}</div>
          {open ? <ChevronUp size={16} className="text-[#94A3B8] shrink-0" /> : <ChevronDown size={16} className="text-[#94A3B8] shrink-0" />}
        </button>

        <AnimatePresence>
          {open && (
            <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
              <div className="px-4 pb-4 border-t border-[#1E1E2E] pt-4 space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  <div><div className="text-[#94A3B8] text-xs mb-1">ID платежа</div><div className="font-mono text-xs">{payment.id}</div></div>
                  <div><div className="text-[#94A3B8] text-xs mb-1">Польз. ID</div><div>{payment.user_id}</div></div>
                  <div><div className="text-[#94A3B8] text-xs mb-1">Последние 4</div><div className="font-mono">{payment.last4 || '—'}</div></div>
                  <div><div className="text-[#94A3B8] text-xs mb-1">Продукт</div><div>{productLabel}</div></div>
                  {d.ram_gb && <div><div className="text-[#94A3B8] text-xs mb-1">Конфиг</div><div>{d.ram_gb} ГБ RAM / {d.cpu_count} vCPU</div></div>}
                </div>

                {d.provider_presets?.length > 0 && (
                  <div className="bg-[#0A0A0F]/60 rounded-xl p-3 space-y-2">
                    <div className="text-[#94A3B8] text-xs font-medium mb-2">Серверы заказа</div>
                    {d.provider_presets.map((pp, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="text-white font-medium">{pp.provider_name}</span>
                        <span className="text-[#94A3B8]">{pp.ram_gb} ГБ RAM / {pp.cpu_count} vCPU — <span className="text-white">{pp.price} ₽/мес</span></span>
                      </div>
                    ))}
                    <div className="border-t border-[#1E1E2E] pt-2 flex justify-between text-sm font-semibold">
                      <span className="text-[#94A3B8]">Итого</span>
                      <span className="text-white">{payment.amount} ₽/мес</span>
                    </div>
                  </div>
                )}

                {payment.status === 'pending' && (
                  <div className="flex gap-2 pt-1">
                    <button onClick={() => setConfirmModal(true)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/20 text-sm font-medium transition-all">
                      <CheckCircle size={14} /> Подтвердить
                    </button>
                    <button onClick={() => setRejectModal(true)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-sm font-medium transition-all">
                      <XCircle size={14} /> Отклонить
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}

export default function AdminPayments() {
  const [tab, setTab] = useState('pending')
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await adminClient.get(`/admin/payments?status=${tab}`)
      setPayments(res.data.items || [])
    } catch {} finally { setLoading(false) }
  }

  useEffect(() => { load() }, [tab])

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Платежи</h1>

      <div className="flex gap-2 mb-4">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              tab === t.key
                ? 'btn-primary'
                : 'btn-outline'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="spinner" /></div>
      ) : (
        <div className="space-y-2">
          {payments.map(p => <PaymentRow key={p.id} payment={p} onUpdate={load} />)}
          {payments.length === 0 && <p className="text-center text-[#94A3B8] py-8">Нет платежей в этом разделе</p>}
        </div>
      )}
    </div>
  )
}
