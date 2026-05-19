import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Save, Plus, Trash2, Eye, EyeOff, CreditCard, Phone } from 'lucide-react'
import { adminClient } from '../../api/client.js'
import toast from 'react-hot-toast'

export default function AdminSettings() {
  const [settings, setSettings] = useState(null)
  const [faq, setFaq] = useState('')
  const [bonusGb, setBonusGb] = useState(30)
  const [newCred, setNewCred] = useState({ username: '', password: '' })
  const [showPwd, setShowPwd] = useState(false)
  const [saving, setSaving] = useState(false)

  // Requisites state
  const [requisites, setRequisites] = useState([])
  const [newReq, setNewReq] = useState({ type: 'card', value: '', holder_name: '', is_active: true })

  const loadSettings = async () => {
    try {
      const r = await adminClient.get('/admin/settings')
      setSettings(r.data)
      setFaq(r.data.faq_text || '')
      setBonusGb(r.data.referral_bonus_gb || 30)
    } catch {}
  }

  const loadRequisites = async () => {
    try {
      const r = await adminClient.get('/admin/requisites')
      setRequisites(r.data)
    } catch {}
  }

  useEffect(() => {
    loadSettings()
    loadRequisites()
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      await adminClient.patch('/admin/settings', { faq_text: faq, referral_bonus_gb: +bonusGb })
      toast.success('Настройки сохранены')
    } catch { toast.error('Ошибка') } finally { setSaving(false) }
  }

  const addAdmin = async () => {
    if (!newCred.username || !newCred.password) return toast.error('Заполните логин и пароль')
    try {
      await adminClient.post('/admin/settings/admin-credentials', newCred)
      toast.success('Администратор добавлен')
      setNewCred({ username: '', password: '' })
      loadSettings()
    } catch { toast.error('Ошибка') }
  }

  const removeAdmin = async (username) => {
    if (!confirm(`Удалить администратора ${username}?`)) return
    try {
      await adminClient.delete(`/admin/settings/admin-credentials/${username}`)
      toast.success('Удалён')
      loadSettings()
    } catch { toast.error('Ошибка') }
  }

  const addRequisite = async () => {
    if (!newReq.value || !newReq.holder_name) return toast.error('Заполните реквизит и владельца')
    try {
      await adminClient.post('/admin/requisites', newReq)
      toast.success('Реквизит добавлен')
      setNewReq({ type: 'card', value: '', holder_name: '', is_active: true })
      loadRequisites()
    } catch { toast.error('Ошибка') }
  }

  const toggleRequisite = async (req) => {
    try {
      await adminClient.put(`/admin/requisites/${req.id}`, { ...req, is_active: !req.is_active })
      loadRequisites()
    } catch { toast.error('Ошибка') }
  }

  const deleteRequisite = async (id) => {
    if (!confirm('Удалить реквизит?')) return
    try {
      await adminClient.delete(`/admin/requisites/${id}`)
      toast.success('Удалён')
      loadRequisites()
    } catch { toast.error('Ошибка') }
  }

  if (!settings) return <div className="flex justify-center py-12"><div className="spinner" /></div>

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Настройки</h1>

      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="vpn-card p-5">
        <h2 className="font-semibold mb-4">Реферальная программа</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm text-[#94A3B8] whitespace-nowrap">Бонус за реферала (ГБ)</label>
          <input type="number" className="input-field w-28" value={bonusGb} onChange={e => setBonusGb(e.target.value)} />
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="vpn-card p-5">
        <h2 className="font-semibold mb-4">Текст FAQ</h2>
        <p className="text-xs text-[#94A3B8] mb-2">Поддерживает Markdown: *жирный*, _курсив_</p>
        <textarea
          className="input-field resize-none h-64 font-mono text-sm"
          value={faq}
          onChange={e => setFaq(e.target.value)}
        />
      </motion.div>

      <button
        onClick={save}
        disabled={saving}
        className="btn-primary flex items-center gap-2 px-6 py-3 rounded-xl font-semibold"
      >
        <Save size={16} />
        {saving ? 'Сохранение...' : 'Сохранить настройки'}
      </button>

      {/* Requisites */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} className="vpn-card p-5">
        <h2 className="font-semibold mb-4">Реквизиты для оплаты</h2>

        <div className="space-y-2 mb-4">
          {requisites.length === 0 && (
            <p className="text-[#94A3B8] text-sm">Нет реквизитов — добавьте хотя бы один</p>
          )}
          {requisites.map(req => (
            <div key={req.id} className="flex items-center justify-between p-3 rounded-xl bg-[#1E1E2E]">
              <div className="flex items-center gap-3">
                <div className="text-[#94A3B8]">
                  {req.type === 'card' ? <CreditCard size={15} /> : <Phone size={15} />}
                </div>
                <div>
                  <div className="font-mono text-sm font-medium">{req.value}</div>
                  <div className="text-xs text-[#94A3B8]">{req.holder_name}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleRequisite(req)}
                  className={`badge text-xs ${req.is_active ? 'badge-active' : 'badge-inactive'}`}
                >
                  {req.is_active ? 'Активен' : 'Откл.'}
                </button>
                <button onClick={() => deleteRequisite(req.id)} className="text-[#94A3B8] hover:text-red-400 transition-colors ml-1">
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Add new requisite */}
        <div className="space-y-2 pt-3 border-t border-[#1E1E2E]">
          <div className="flex gap-2">
            <select
              className="input-field w-32 text-sm"
              value={newReq.type}
              onChange={e => setNewReq(r => ({ ...r, type: e.target.value }))}
            >
              <option value="card">Карта</option>
              <option value="phone">Телефон</option>
            </select>
            <input
              className="input-field flex-1 text-sm"
              placeholder={newReq.type === 'card' ? '0000 0000 0000 0000' : '+79991234567'}
              value={newReq.value}
              onChange={e => setNewReq(r => ({ ...r, value: e.target.value }))}
            />
          </div>
          <div className="flex gap-2">
            <input
              className="input-field flex-1 text-sm"
              placeholder="Имя владельца"
              value={newReq.holder_name}
              onChange={e => setNewReq(r => ({ ...r, holder_name: e.target.value }))}
            />
            <label className="flex items-center gap-1.5 text-sm whitespace-nowrap cursor-pointer">
              <input type="checkbox" className="accent-purple-500" checked={newReq.is_active} onChange={e => setNewReq(r => ({ ...r, is_active: e.target.checked }))} />
              Активен
            </label>
            <button onClick={addRequisite} className="btn-primary px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap flex items-center gap-1.5">
              <Plus size={15} /> Добавить
            </button>
          </div>
        </div>
      </motion.div>

      {/* Admins */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="vpn-card p-5">
        <h2 className="font-semibold mb-4">Администраторы</h2>

        <div className="space-y-2 mb-4">
          {(settings.admin_credentials || []).map(a => (
            <div key={a.username} className="flex items-center justify-between p-3 rounded-xl bg-[#1E1E2E]">
              <span className="font-medium">{a.username}</span>
              <button onClick={() => removeAdmin(a.username)} className="text-[#94A3B8] hover:text-red-400 transition-colors">
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <input
            className="input-field flex-1"
            placeholder="Логин"
            value={newCred.username}
            onChange={e => setNewCred(c => ({ ...c, username: e.target.value }))}
          />
          <div className="relative flex-1">
            <input
              type={showPwd ? 'text' : 'password'}
              className="input-field pr-9"
              placeholder="Пароль"
              value={newCred.password}
              onChange={e => setNewCred(c => ({ ...c, password: e.target.value }))}
            />
            <button onClick={() => setShowPwd(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94A3B8]">
              {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          <button onClick={addAdmin} className="btn-primary px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap flex items-center gap-1.5">
            <Plus size={15} /> Добавить
          </button>
        </div>
      </motion.div>
    </div>
  )
}
