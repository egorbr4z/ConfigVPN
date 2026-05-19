import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Pencil, Trash2, X, Infinity } from 'lucide-react'
import { adminClient } from '../../api/client.js'
import toast from 'react-hot-toast'

const empty = { name: '', type: 'regular', price: '', duration_days: 30, traffic_gb: 100, monthly_traffic_gb: 0, max_connections: 1, description: '' }

function PlanModal({ plan, onClose, onSave }) {
  const [form, setForm] = useState(plan || empty)
  const [loading, setLoading] = useState(false)
  const isNew = !plan

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    setLoading(true)
    try {
      if (isNew) {
        await adminClient.post('/admin/plans', { ...form, price: +form.price, traffic_gb: +form.traffic_gb, monthly_traffic_gb: +form.monthly_traffic_gb, max_connections: +form.max_connections, duration_days: +form.duration_days })
        toast.success('Тариф добавлен')
      } else {
        await adminClient.patch(`/admin/plans/${plan.id}`, { name: form.name, price: +form.price, description: form.description, monthly_traffic_gb: +form.monthly_traffic_gb, max_connections: +form.max_connections })
        toast.success('Тариф обновлён')
      }
      onSave()
    } catch { toast.error('Ошибка') } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 overflow-y-auto py-8">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="vpn-card p-6 w-full max-w-md relative z-10 my-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-lg">{isNew ? 'Новый тариф' : 'Редактировать'}</h3>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-white"><X size={20} /></button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-[#94A3B8] block mb-1">Название</label>
            <input className="input-field" value={form.name} onChange={e => set('name', e.target.value)} placeholder="Обычный VPN — 1 месяц" />
          </div>

          {isNew && (
            <div>
              <label className="text-xs text-[#94A3B8] block mb-1">Тип</label>
              <div className="flex gap-2">
                {['whitelist', 'regular'].map(t => (
                  <button key={t} onClick={() => set('type', t)} className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${form.type === t ? 'btn-primary' : 'btn-outline'}`}>
                    {t === 'whitelist' ? '🔒 Белый список' : '💰 Обычный'}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[#94A3B8] block mb-1">Цена (₽)</label>
              <input type="number" className="input-field" value={form.price} onChange={e => set('price', e.target.value)} placeholder="299" />
            </div>
            {isNew && (
              <div>
                <label className="text-xs text-[#94A3B8] block mb-1">Дней</label>
                <input type="number" className="input-field" value={form.duration_days} onChange={e => set('duration_days', e.target.value)} />
              </div>
            )}
            <div>
              <label className="text-xs text-[#94A3B8] block mb-1">Трафик/мес (0=∞)</label>
              <input type="number" className="input-field" value={form.monthly_traffic_gb} onChange={e => set('monthly_traffic_gb', e.target.value)} placeholder="0" />
            </div>
            <div>
              <label className="text-xs text-[#94A3B8] block mb-1">Подключений</label>
              <input type="number" className="input-field" value={form.max_connections} onChange={e => set('max_connections', e.target.value)} />
            </div>
          </div>

          <div>
            <label className="text-xs text-[#94A3B8] block mb-1">Описание</label>
            <textarea className="input-field resize-none h-20" value={form.description} onChange={e => set('description', e.target.value)} />
          </div>
        </div>

        <div className="flex gap-3 mt-5">
          <button onClick={onClose} className="btn-outline flex-1 py-2.5 rounded-xl text-sm">Отмена</button>
          <button onClick={submit} disabled={loading} className="btn-primary flex-1 py-2.5 rounded-xl text-sm font-semibold">{loading ? 'Сохранение...' : 'Сохранить'}</button>
        </div>
      </motion.div>
    </div>
  )
}

export default function AdminPlans() {
  const [plans, setPlans] = useState([])
  const [modal, setModal] = useState(null) // null | 'new' | plan object

  const load = async () => {
    try { const r = await adminClient.get('/admin/plans'); setPlans(r.data) } catch {}
  }

  useEffect(() => { load() }, [])

  const toggle = async (plan) => {
    try {
      await adminClient.patch(`/admin/plans/${plan.id}`, { is_active: !plan.is_active })
      toast.success(plan.is_active ? 'Деактивирован' : 'Активирован')
      load()
    } catch { toast.error('Ошибка') }
  }

  const del = async (id) => {
    if (!confirm('Удалить тариф?')) return
    try { await adminClient.delete(`/admin/plans/${id}`); toast.success('Удалён'); load() } catch { toast.error('Ошибка') }
  }

  return (
    <div>
      <AnimatePresence>
        {modal !== null && <PlanModal plan={modal === 'new' ? null : modal} onClose={() => setModal(null)} onSave={() => { setModal(null); load() }} />}
      </AnimatePresence>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Тарифы</h1>
        <button onClick={() => setModal('new')} className="btn-primary flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold">
          <Plus size={16} /> Добавить
        </button>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {plans.map((plan, i) => (
          <motion.div key={plan.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }} className="vpn-card p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`badge ${plan.is_active ? 'badge-active' : 'badge-inactive'}`}>{plan.is_active ? 'Активен' : 'Неактивен'}</span>
                  <span className="text-xs text-[#94A3B8]">{plan.type === 'whitelist' ? '🔒' : '💰'}</span>
                </div>
                <h3 className="font-semibold">{plan.name}</h3>
              </div>
              <span className="text-xl font-bold gradient-text">{plan.price} ₽</span>
            </div>

            <div className="space-y-1 text-sm text-[#94A3B8] mb-4">
              <div className="flex justify-between"><span>Трафик/мес</span><span className="text-[#E2E8F0]">{plan.monthly_traffic_gb === 0 ? '∞' : `${plan.monthly_traffic_gb} ГБ`}</span></div>
              <div className="flex justify-between"><span>Подключений</span><span className="text-[#E2E8F0]">{plan.max_connections}</span></div>
              <div className="flex justify-between"><span>Срок</span><span className="text-[#E2E8F0]">{plan.duration_days} дн.</span></div>
            </div>

            <div className="flex gap-2">
              <button onClick={() => toggle(plan)} className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all ${plan.is_active ? 'bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20' : 'bg-green-500/10 text-green-400 hover:bg-green-500/20'}`}>
                {plan.is_active ? 'Деактивировать' : 'Активировать'}
              </button>
              <button onClick={() => setModal(plan)} className="p-1.5 rounded-lg bg-[#1E1E2E] text-[#94A3B8] hover:text-white transition-colors"><Pencil size={14} /></button>
              <button onClick={() => del(plan.id)} className="p-1.5 rounded-lg bg-[#1E1E2E] text-[#94A3B8] hover:text-red-400 transition-colors"><Trash2 size={14} /></button>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
