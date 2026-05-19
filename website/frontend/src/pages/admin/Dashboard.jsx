import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Users, CreditCard, Activity, Clock } from 'lucide-react'
import { adminClient } from '../../api/client.js'

function StatCard({ label, value, icon: Icon, color, delay }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="vpn-card p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-[#94A3B8] text-sm">{label}</span>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
          <Icon size={17} />
        </div>
      </div>
      <div className="text-3xl font-bold">{value ?? '—'}</div>
    </motion.div>
  )
}

function StatusBadge({ status }) {
  const map = {
    pending: { label: 'Ожидает', cls: 'badge-pending' },
    confirmed: { label: 'Подтверждён', cls: 'badge-confirmed' },
    rejected: { label: 'Отклонён', cls: 'badge-rejected' },
  }
  const { label, cls } = map[status] || { label: status, cls: '' }
  return <span className={`badge ${cls}`}>{label}</span>
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [payments, setPayments] = useState([])

  useEffect(() => {
    adminClient.get('/admin/stats').then(r => setStats(r.data)).catch(() => {})
    adminClient.get('/admin/payments?status=pending&limit=8').then(r => setPayments(r.data.items || [])).catch(() => {})
  }, [])

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Дашборд</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Пользователей" value={stats?.total_users} icon={Users} color="bg-purple-600/20 text-purple-400" delay={0} />
        <StatCard label="Ожидают оплат" value={stats?.pending_payments} icon={Clock} color="bg-yellow-500/20 text-yellow-400" delay={0.05} />
        <StatCard label="Активных подписок" value={stats?.active_subscriptions} icon={Activity} color="bg-green-500/20 text-green-400" delay={0.1} />
        <StatCard label="Всего платежей" value={stats?.total_payments} icon={CreditCard} color="bg-blue-500/20 text-blue-400" delay={0.15} />
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="vpn-card p-5">
        <h2 className="font-semibold mb-4 text-[#94A3B8] text-sm uppercase tracking-wide">Ожидающие платежи</h2>
        {payments.length === 0 ? (
          <p className="text-[#94A3B8] text-sm py-4 text-center">Нет ожидающих платежей</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#94A3B8] border-b border-[#1E1E2E]">
                  <th className="text-left pb-3 pr-4">ID</th>
                  <th className="text-left pb-3 pr-4">Пользователь</th>
                  <th className="text-left pb-3 pr-4">Сумма</th>
                  <th className="text-left pb-3 pr-4">Дата</th>
                  <th className="text-left pb-3">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E1E2E]">
                {payments.map(p => (
                  <tr key={p.id} className="hover:bg-[#1E1E2E]/40 transition-colors">
                    <td className="py-3 pr-4 font-mono text-xs text-[#94A3B8]">{p.id.slice(0, 8)}…</td>
                    <td className="py-3 pr-4">{p.user_id}</td>
                    <td className="py-3 pr-4 font-semibold">{p.amount} ₽</td>
                    <td className="py-3 pr-4 text-[#94A3B8]">{p.created_at?.slice(0, 10)}</td>
                    <td className="py-3"><StatusBadge status={p.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  )
}
