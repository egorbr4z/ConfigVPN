import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, X, Trash2, ChevronDown, ChevronUp, Pencil, Server } from 'lucide-react'
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
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
        className="vpn-card p-6 w-full max-w-md relative z-10">
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
          <button onClick={submit} disabled={loading} className="btn-primary flex-1 py-2.5 rounded-xl text-sm font-semibold">
            {loading ? 'Сохранение...' : 'Добавить'}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

function PresetModal({ providerId, preset, onClose, onSave }) {
  const editing = !!preset
  const [form, setForm] = useState({
    ram_gb: preset?.ram_gb ?? 2,
    cpu_count: preset?.cpu_count ?? 1,
    price: preset?.price ?? 0,
    is_active: preset?.is_active ?? true,
  })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    if (!form.ram_gb || !form.cpu_count || !form.price) return toast.error('Заполните все поля')
    setLoading(true)
    try {
      const body = { provider_id: providerId, ram_gb: +form.ram_gb, cpu_count: +form.cpu_count, price: +form.price, is_active: form.is_active }
      if (editing) {
        await adminClient.put(`/admin/presets/${preset.id}`, body)
        toast.success('Пресет обновлён')
      } else {
        await adminClient.post('/admin/presets', body)
        toast.success('Пресет добавлен')
      }
      onSave()
    } catch { toast.error('Ошибка') } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
        className="vpn-card p-6 w-full max-w-sm relative z-10">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-lg">{editing ? 'Изменить пресет' : 'Новый пресет'}</h3>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-white"><X size={20} /></button>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[#94A3B8] block mb-1">RAM (ГБ)</label>
              <input type="number" min="1" className="input-field" value={form.ram_gb} onChange={e => set('ram_gb', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-[#94A3B8] block mb-1">CPU (vCPU)</label>
              <input type="number" min="1" className="input-field" value={form.cpu_count} onChange={e => set('cpu_count', e.target.value)} />
            </div>
          </div>
          <div>
            <label className="text-xs text-[#94A3B8] block mb-1">Цена (₽/мес)</label>
            <input type="number" min="0" className="input-field" value={form.price} onChange={e => set('price', e.target.value)} />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" className="accent-purple-500" checked={form.is_active} onChange={e => set('is_active', e.target.checked)} />
            <span className="text-sm">Активен</span>
          </label>
        </div>
        <div className="flex gap-3 mt-5">
          <button onClick={onClose} className="btn-outline flex-1 py-2.5 rounded-xl text-sm">Отмена</button>
          <button onClick={submit} disabled={loading} className="btn-primary flex-1 py-2.5 rounded-xl text-sm font-semibold">
            {loading ? 'Сохранение...' : (editing ? 'Сохранить' : 'Добавить')}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

function ProviderRow({ provider, allPresets, onToggle, onDelete, onPresetsChange, onOpenPresetModal }) {
  const [expanded, setExpanded] = useState(false)

  const presets = allPresets.filter(p => p.provider_id === provider.id)

  const deletePreset = async (id) => {
    if (!confirm('Удалить пресет?')) return
    try { await adminClient.delete(`/admin/presets/${id}`); toast.success('Удалён'); onPresetsChange() } catch { toast.error('Ошибка') }
  }

  return (
    <>
      <tr className="hover:bg-[#1E1E2E]/40 transition-colors border-b border-[#1E1E2E]">
        <td className="p-3">
          <button onClick={() => setExpanded(v => !v)} className="text-[#94A3B8] hover:text-white transition-colors">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </td>
        <td className="p-3 font-medium">{provider.name}</td>
        <td className="p-3 text-[#94A3B8] text-sm">{provider.location}</td>
        <td className="p-3 font-mono text-xs text-[#94A3B8]">{provider.server_ip}</td>
        <td className="p-3 text-center">
          <button onClick={() => onToggle(provider, 'is_russian')} className="text-lg" title="Сменить тип">
            {provider.is_russian ? '🇷🇺' : '🌍'}
          </button>
        </td>
        <td className="p-3 text-center">
          <button onClick={() => onToggle(provider, 'supports_whitelist')} className={`badge ${provider.supports_whitelist ? 'badge-active' : 'badge-inactive'}`}>
            {provider.supports_whitelist ? 'Да' : 'Нет'}
          </button>
        </td>
        <td className="p-3 text-center">
          <button onClick={() => onToggle(provider, 'is_active')} className={`badge ${provider.is_active ? 'badge-active' : 'badge-inactive'}`}>
            {provider.is_active ? 'Активен' : 'Откл.'}
          </button>
        </td>
        <td className="p-3">
          <button onClick={() => onDelete(provider.id)} className="text-[#94A3B8] hover:text-red-400 transition-colors"><Trash2 size={15} /></button>
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={8} className="bg-[#0A0A0F]/60 border-b border-[#1E1E2E]">
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-[#94A3B8] flex items-center gap-2">
                  <Server size={14} /> Конфигурации сервера
                </span>
                <button
                  onClick={() => onOpenPresetModal(provider.id, null)}
                  className="btn-primary flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold"
                >
                  <Plus size={13} /> Добавить
                </button>
              </div>

              {presets.length === 0 ? (
                <p className="text-[#94A3B8] text-xs py-2">Нет конфигураций — добавьте первую</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {presets.map(preset => (
                    <div key={preset.id} className="flex items-center justify-between p-3 rounded-xl bg-[#12121A] border border-[#1E1E2E]">
                      <div>
                        <div className="text-sm font-medium text-white">
                          {preset.ram_gb} ГБ RAM / {preset.cpu_count} vCPU
                        </div>
                        <div className="text-xs text-[#94A3B8] mt-0.5">
                          {preset.price}₽/мес
                          {!preset.is_active && <span className="ml-2 text-yellow-500">• откл.</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 ml-3">
                        <button onClick={() => onOpenPresetModal(provider.id, preset)} className="text-[#94A3B8] hover:text-white transition-colors">
                          <Pencil size={13} />
                        </button>
                        <button onClick={() => deletePreset(preset.id)} className="text-[#94A3B8] hover:text-red-400 transition-colors">
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export default function AdminProviders() {
  const [providers, setProviders] = useState([])
  const [allPresets, setAllPresets] = useState([])
  const [providerModal, setProviderModal] = useState(false)
  // presetModal: null | { providerId, preset (null = new) }
  const [presetModal, setPresetModal] = useState(null)

  const loadProviders = async () => {
    try { const r = await adminClient.get('/admin/providers'); setProviders(r.data) } catch {}
  }

  const loadPresets = async () => {
    try { const r = await adminClient.get('/admin/presets'); setAllPresets(r.data) } catch {}
  }

  useEffect(() => { loadProviders(); loadPresets() }, [])

  const toggle = async (prov, field) => {
    try { await adminClient.patch(`/admin/providers/${prov.id}`, { [field]: !prov[field] }); loadProviders() } catch { toast.error('Ошибка') }
  }

  const del = async (id) => {
    if (!confirm('Удалить провайдера?')) return
    try { await adminClient.delete(`/admin/providers/${id}`); toast.success('Удалён'); loadProviders() } catch { toast.error('Ошибка') }
  }

  const openPresetModal = (providerId, preset) => setPresetModal({ providerId, preset })

  return (
    <div>
      {/* Modals rendered OUTSIDE the table to avoid invalid HTML nesting */}
      <AnimatePresence>
        {providerModal && (
          <ProviderModal
            onClose={() => setProviderModal(false)}
            onSave={() => { setProviderModal(false); loadProviders() }}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {presetModal && (
          <PresetModal
            providerId={presetModal.providerId}
            preset={presetModal.preset}
            onClose={() => setPresetModal(null)}
            onSave={() => { setPresetModal(null); loadPresets() }}
          />
        )}
      </AnimatePresence>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Провайдеры</h1>
        <button onClick={() => setProviderModal(true)} className="btn-primary flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold">
          <Plus size={16} /> Добавить
        </button>
      </div>

      <div className="vpn-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[#94A3B8] border-b border-[#1E1E2E]">
              <th className="p-3 w-8" />
              <th className="text-left p-3">Название</th>
              <th className="text-left p-3">Локация</th>
              <th className="text-left p-3">IP</th>
              <th className="text-center p-3">Тип</th>
              <th className="text-center p-3">WL</th>
              <th className="text-center p-3">Статус</th>
              <th className="p-3 w-8" />
            </tr>
          </thead>
          <tbody>
            {providers.map(p => (
              <ProviderRow
                key={p.id}
                provider={p}
                allPresets={allPresets}
                onToggle={toggle}
                onDelete={del}
                onPresetsChange={loadPresets}
                onOpenPresetModal={openPresetModal}
              />
            ))}
          </tbody>
        </table>
        {providers.length === 0 && <p className="text-center text-[#94A3B8] py-8">Нет провайдеров</p>}
      </div>
    </div>
  )
}
