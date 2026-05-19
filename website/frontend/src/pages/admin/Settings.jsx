import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Save, Plus, Trash2, Eye, EyeOff } from 'lucide-react'
import { adminClient } from '../../api/client.js'
import toast from 'react-hot-toast'

export default function AdminSettings() {
  const [settings, setSettings] = useState(null)
  const [faq, setFaq] = useState('')
  const [bonusGb, setBonusGb] = useState(30)
  const [newCred, setNewCred] = useState({ username: '', password: '' })
  const [showPwd, setShowPwd] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    adminClient.get('/admin/settings').then(r => {
      setSettings(r.data)
      setFaq(r.data.faq_text || '')
      setBonusGb(r.data.referral_bonus_gb || 30)
    }).catch(() => {})
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
      const r = await adminClient.get('/admin/settings')
      setSettings(r.data)
    } catch { toast.error('Ошибка') }
  }

  const removeAdmin = async (username) => {
    if (!confirm(`Удалить администратора ${username}?`)) return
    try {
      await adminClient.delete(`/admin/settings/admin-credentials/${username}`)
      toast.success('Удалён')
      const r = await adminClient.get('/admin/settings')
      setSettings(r.data)
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
