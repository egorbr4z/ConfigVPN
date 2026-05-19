import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, ChevronDown, ChevronUp, Ban, CheckCircle, Gift } from 'lucide-react'
import { adminClient } from '../../api/client.js'
import toast from 'react-hot-toast'

function UserRow({ user, onUpdate }) {
  const [open, setOpen] = useState(false)
  const [bonus, setBonus] = useState('')
  const [loading, setLoading] = useState(false)

  const toggleBlock = async () => {
    try {
      await adminClient.patch(`/admin/users/${user.telegram_id}`, { is_blocked: !user.is_blocked })
      toast.success(user.is_blocked ? 'Пользователь разблокирован' : 'Пользователь заблокирован')
      onUpdate()
    } catch { toast.error('Ошибка') }
  }

  const addBonus = async () => {
    const gb = parseFloat(bonus)
    if (!gb || gb <= 0) return toast.error('Введите корректное число ГБ')
    setLoading(true)
    try {
      await adminClient.patch(`/admin/users/${user.telegram_id}`, { add_bonus_gb: gb })
      toast.success(`+${gb} ГБ начислено`)
      setBonus('')
      onUpdate()
    } catch { toast.error('Ошибка') } finally { setLoading(false) }
  }

  return (
    <div className="vpn-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-4 p-4 text-left hover:bg-[#1E1E2E]/40 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{user.full_name}</span>
            {user.is_blocked && <span className="badge badge-rejected text-xs">Заблокирован</span>}
          </div>
          <div className="text-[#94A3B8] text-sm">{user.phone} · ID {user.telegram_id}</div>
        </div>
        <div className="text-[#94A3B8] text-sm shrink-0">{user.created_at?.slice(0, 10)}</div>
        {open ? <ChevronUp size={16} className="text-[#94A3B8] shrink-0" /> : <ChevronDown size={16} className="text-[#94A3B8] shrink-0" />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-[#1E1E2E] pt-4 space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <div>
                  <div className="text-[#94A3B8] text-xs mb-1">Реф. код</div>
                  <div className="font-mono">{user.referral_code}</div>
                </div>
                <div>
                  <div className="text-[#94A3B8] text-xs mb-1">Бонус ГБ</div>
                  <div>{user.bonus_gb} ГБ</div>
                </div>
                <div>
                  <div className="text-[#94A3B8] text-xs mb-1">Username</div>
                  <div>{user.username ? `@${user.username}` : '—'}</div>
                </div>
                <div>
                  <div className="text-[#94A3B8] text-xs mb-1">Приглашён</div>
                  <div>{user.referred_by || '—'}</div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  onClick={toggleBlock}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    user.is_blocked
                      ? 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
                      : 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                  }`}
                >
                  {user.is_blocked ? <CheckCircle size={14} /> : <Ban size={14} />}
                  {user.is_blocked ? 'Разблокировать' : 'Заблокировать'}
                </button>

                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={bonus}
                    onChange={e => setBonus(e.target.value)}
                    placeholder="ГБ"
                    className="input-field w-20 py-1.5 text-sm"
                  />
                  <button
                    onClick={addBonus}
                    disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-600/20 text-purple-400 hover:bg-purple-600/30 text-sm font-medium transition-all"
                  >
                    <Gift size={14} />
                    Бонус
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function AdminUsers() {
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await adminClient.get(`/admin/users?search=${encodeURIComponent(search)}`)
      setUsers(res.data.items || [])
    } catch { toast.error('Ошибка загрузки') } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Пользователи</h1>
        <span className="text-[#94A3B8] text-sm">{users.length} всего</span>
      </div>

      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
        <input
          className="input-field pl-9"
          placeholder="Поиск по телефону или ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && load()}
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="spinner" /></div>
      ) : (
        <div className="space-y-2">
          {users.map(u => <UserRow key={u.telegram_id} user={u} onUpdate={load} />)}
          {users.length === 0 && <p className="text-center text-[#94A3B8] py-8">Пользователи не найдены</p>}
        </div>
      )}
    </div>
  )
}
