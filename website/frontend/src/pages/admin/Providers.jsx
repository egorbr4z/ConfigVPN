import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, X, Trash2 } from 'lucide-react'
import { adminClient } from '../../api/client.js'
import toast from 'react-hot-toast'

function ProviderModal({ onClose, onSave }) {
  const [form, setForm] = useState({ name: '', location: '', server_ip: '', supports_whitelist: true, is_russian: false })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    if (!form.name || !form.location || !form.server_ip) return toast.error('Заполните все поля')
    setLoading(true)
    try {
      await adminClient.post('/admin/providers', form)
      toast.success('Провайдер добавлен')
      onSave()
    } catch { toast.error('Ошибка') } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="vpn-card p-6 w-full max-w-md relative z-10">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-lg">Новый провайдер</h3>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-white"><X size={20} /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-[#94A3B8] block mb-1">Название</label>
            <input className="input-field" value={form.name} onChange={e => set('name', e.target.value)} placeholder="NL-Amsterdam-01" />
          </div>
          <div>
            <label className="text-xs text-[#94A3B8] block mb-1">Локация</label>
            <input className="input-field" value={form.location} onChange={e => set('location', e.target.value)} placeholder="Нидерланды, Амстердам" />
          </div>
          <div>
            <label className="text-xs text-[#94A3B8] block mb-1">IP сервера</label>
            <input className="input-field" value={form.server_ip} onChange={e => set('server_ip', e.target.value)} placeholder="185.100.65.10" />
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="accent-purple-500" checked={form.supports_whitelist} onChange={e => set('supports_whitelist', e.target.checked)} />
              <span className="text-sm">Белые списки</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="accent-purple-500" checked={form.is_russian} onChange={e => set('is_russian', e.target.checked)} />
              <span className="text-sm">🇷🇺 Российский</span>
            </label>
          </div>
        </div>
        <div className="flex gap-3 mt-5">
          <button onClick={onClose} className="btn-outline flex-1 py-2.5 rounded-xl text-sm">Отмена</button>
          <button onClick={submit} disabled={loading} className="btn-primary flex-1 py-2.5 rounded-xl text-sm font-semibold">{loading ? 'Сохранение...' : 'Добавить'}</button>
        </div>
      </motion.div>
    </div>
  )
}

export default function AdminProviders() {
  const [providers, setProviders] = useState([])
  const [modal, setModal] = useState(false)

  const load = async () => {
    try { const r = await adminClient.get('/admin/providers'); setProviders(r.data) } catch {}
  }

  useEffect(() => { load() }, [])

  const toggle = async (prov, field) => {
    try {
      await adminClient.patch(`/admin/providers/${prov.id}`, { [field]: !prov[field] })
      load()
    } catch { toast.error('Ошибка') }
  }

  const del = async (id) => {
    if (!confirm('Удалить провайдера?')) return
    try { await adminClient.delete(`/admin/providers/${id}`); toast.success('Удалён'); load() } catch { toast.error('Ошибка') }
  }

  return (
    <div>
      <AnimatePresence>{modal && <ProviderModal onClose={() => setModal(false)} onSave={() => { setModal(false); load() }} />}</AnimatePresence>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Провайдеры</h1>
        <button onClick={() => setModal(true)} className="btn-primary flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold">
          <Plus size={16} /> Добавить
        </button>
      </div>

      <div className="vpn-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[#94A3B8] border-b border-[#1E1E2E]">
              <th className="text-left p-4">Название</th>
              <th className="text-left p-4">Локация</th>
              <th className="text-left p-4">IP</th>
              <th className="text-center p-4">Тип</th>
              <th className="text-center p-4">WL</th>
              <th className="text-center p-4">Статус</th>
              <th className="p-4" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E1E2E]">
            {providers.map((p, i) => (
              <motion.tr key={p.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }} className="hover:bg-[#1E1E2E]/40 transition-colors">
                <td className="p-4 font-medium">{p.name}</td>
                <td className="p-4 text-[#94A3B8]">{p.location}</td>
                <td className="p-4 font-mono text-xs text-[#94A3B8]">{p.server_ip}</td>
                <td className="p-4 text-center">
                  <button onClick={() => toggle(p, 'is_russian')} className="text-lg" title="Сменить тип">
                    {p.is_russian ? '🇷🇺' : '🌍'}
                  </button>
                </td>
                <td className="p-4 text-center">
                  <button onClick={() => toggle(p, 'supports_whitelist')} className={`badge ${p.supports_whitelist ? 'badge-active' : 'badge-inactive'}`}>
                    {p.supports_whitelist ? 'Да' : 'Нет'}
                  </button>
                </td>
                <td className="p-4 text-center">
                  <button onClick={() => toggle(p, 'is_active')} className={`badge ${p.is_active ? 'badge-active' : 'badge-inactive'}`}>
                    {p.is_active ? 'Активен' : 'Откл.'}
                  </button>
                </td>
                <td className="p-4">
                  <button onClick={() => del(p.id)} className="text-[#94A3B8] hover:text-red-400 transition-colors"><Trash2 size={15} /></button>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
        {providers.length === 0 && <p className="text-center text-[#94A3B8] py-8">Нет провайдеров</p>}
      </div>
    </div>
  )
}
