import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, Zap, Eye, ChevronDown, ChevronUp, ArrowRight, Users, Lock, Globe } from 'lucide-react'
import AnimatedBackground from '../components/AnimatedBackground.jsx'
import ScrollReveal from '../components/ScrollReveal.jsx'
import PlanCard from '../components/PlanCard.jsx'
import client from '../api/client.js'

function useCountUp(target, duration = 2000, isVisible) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (!isVisible) return
    let start = 0
    const increment = target / (duration / 16)
    const timer = setInterval(() => {
      start += increment
      if (start >= target) { setCount(target); clearInterval(timer) }
      else setCount(Math.floor(start))
    }, 16)
    return () => clearInterval(timer)
  }, [target, duration, isVisible])
  return count
}

const faqs = [
  {
    q: 'Что такое VPN с белыми списками?',
    a: 'Это умный VPN, который направляет через зашифрованный канал только заблокированные сайты (Instagram, YouTube, X и др.), а все российские ресурсы работают напрямую на полной скорости. Идеально для ежедневного использования — скорость не падает, трафик экономится.',
  },
  {
    q: 'Что такое обычный VPN?',
    a: 'Весь интернет-трафик идёт через VPN-сервер. Российские сайты работают через сервер, что может немного снижать скорость. Зато дешевле и подходит для тех, кто хочет полную анонимность или доступ к зарубежным сервисам без исключений.',
  },
  {
    q: 'Как происходит оплата?',
    a: 'Вы переводите сумму на карту или номер телефона (СБП), которые выдаются случайным образом. После перевода вводите последние 4 цифры карты/номера телефона, с которого платили. Администратор проверяет платёж вручную — обычно в течение 30 минут.',
  },
  {
    q: 'Как подключиться после оплаты?',
    a: 'После подтверждения платежа вы получите ссылку на подписку. Добавьте её в один из клиентов: Android — Hiddify, Nekobox; iOS — Shadowrocket, Streisand; Windows/Mac — Hiddify Next. Обычно достаточно скопировать ссылку и импортировать через «Добавить → Подписка».',
  },
  {
    q: 'Как работает реферальная программа?',
    a: 'Поделитесь своей реферальной ссылкой. Когда приглашённый человек совершит первую покупку, вы автоматически получите +30 ГБ бонусного трафика. Количество приглашений не ограничено.',
  },
]

function FAQItem({ item, index }) {
  const [open, setOpen] = useState(false)
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.05 }}
      className="border border-[#1E1E2E] rounded-xl overflow-hidden"
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/2 transition-colors"
      >
        <span className="font-medium text-[#E2E8F0] pr-4">{item.q}</span>
        {open ? (
          <ChevronUp className="w-4 h-4 text-[#94A3B8] flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-[#94A3B8] flex-shrink-0" />
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            <div className="px-6 pb-4 text-[#94A3B8] text-sm leading-relaxed border-t border-[#1E1E2E] pt-4">
              {item.a}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function StatsSection() {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true) }, { threshold: 0.3 })
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])
  const users = useCountUp(5000, 2000, visible)
  const uptime = useCountUp(99, 1500, visible)
  const speed = useCountUp(1000, 2000, visible)

  return (
    <div ref={ref} className="grid grid-cols-3 gap-6 text-center">
      {[
        { value: `${users.toLocaleString()}+`, label: 'Пользователей' },
        { value: `${uptime}%`, label: 'Аптайм' },
        { value: `${speed} Мбит/с`, label: 'Скорость' },
      ].map((stat, i) => (
        <div key={i}>
          <div className="text-3xl md:text-4xl font-bold gradient-text">{stat.value}</div>
          <div className="text-[#94A3B8] text-sm mt-1">{stat.label}</div>
        </div>
      ))}
    </div>
  )
}

export default function Landing() {
  const [plans, setPlans] = useState([])
  const [activeTab, setActiveTab] = useState('whitelist')

  useEffect(() => {
    client.get('/plans').then(r => setPlans(r.data)).catch(() => {})
  }, [])

  const filteredPlans = plans.filter(p => p.type === activeTab)

  return (
    <div className="relative">
      <AnimatedBackground />

      {/* Hero */}
      <section className="relative min-h-screen flex items-center justify-center pt-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/10 text-sm text-purple-300 mb-8">
              <Shield className="w-4 h-4" />
              Защищённое соединение
            </div>
            <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-6 leading-tight">
              Быстрый и надёжный{' '}
              <span className="gradient-text">VPN</span>
            </h1>
            <p className="text-xl text-[#94A3B8] mb-10 max-w-2xl mx-auto leading-relaxed">
              Доступ к любым сайтам без замедления скорости. Умные белые списки, без логов, один клик для подключения.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                <Link
                  to="/plans"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-xl btn-primary text-white font-semibold text-lg"
                >
                  Выбрать план
                  <ArrowRight className="w-5 h-5" />
                </Link>
              </motion.div>
              <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-xl btn-outline text-[#E2E8F0] font-semibold text-lg"
                >
                  Попробовать
                </Link>
              </motion.div>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.7 }}
            className="mt-20 vpn-card p-8 max-w-2xl mx-auto"
          >
            <StatsSection />
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <motion.div
          animate={{ y: [0, 10, 0] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 text-[#94A3B8]"
        >
          <ChevronDown className="w-6 h-6" />
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <ScrollReveal>
            <div className="text-center mb-16">
              <h2 className="text-4xl font-bold text-white mb-4">
                Почему выбирают <span className="gradient-text">ConfigVPN</span>
              </h2>
              <p className="text-[#94A3B8] text-lg max-w-2xl mx-auto">
                Уникальная технология белых списков обеспечивает максимальную скорость и безопасность
              </p>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: <Shield className="w-7 h-7" />,
                title: 'Белые списки',
                description: 'Только заблокированные сайты идут через VPN. Российские ресурсы работают напрямую на полной скорости.',
                color: 'from-purple-500/20 to-purple-900/20',
                border: 'border-purple-500/20',
                iconBg: 'bg-purple-500/20 text-purple-400',
              },
              {
                icon: <Zap className="w-7 h-7" />,
                title: 'Высокая скорость',
                description: 'VK, Яндекс, Сбер и другие российские сервисы работают без VPN — на максимальной скорости вашего провайдера.',
                color: 'from-blue-500/20 to-blue-900/20',
                border: 'border-blue-500/20',
                iconBg: 'bg-blue-500/20 text-blue-400',
              },
              {
                icon: <Eye className="w-7 h-7" />,
                title: 'Без логов',
                description: 'Мы не храним логи вашей активности. Полная конфиденциальность и анонимность в интернете.',
                color: 'from-green-500/20 to-green-900/20',
                border: 'border-green-500/20',
                iconBg: 'bg-green-500/20 text-green-400',
              },
            ].map((feat, i) => (
              <ScrollReveal key={i} delay={i * 0.15}>
                <motion.div
                  whileHover={{ scale: 1.02, y: -4 }}
                  className={`vpn-card p-6 ${feat.border} bg-gradient-to-br ${feat.color} h-full`}
                >
                  <div className={`w-12 h-12 rounded-xl ${feat.iconBg} flex items-center justify-center mb-4`}>
                    {feat.icon}
                  </div>
                  <h3 className="text-xl font-bold text-white mb-3">{feat.title}</h3>
                  <p className="text-[#94A3B8] leading-relaxed">{feat.description}</p>
                </motion.div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* Plans */}
      <section className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <ScrollReveal>
            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold text-white mb-4">
                Выберите <span className="gradient-text">тариф</span>
              </h2>
              <p className="text-[#94A3B8] text-lg max-w-2xl mx-auto">
                Гибкие планы для любых потребностей
              </p>
            </div>
          </ScrollReveal>

          {/* Tabs */}
          <ScrollReveal>
            <div className="flex justify-center mb-8">
              <div className="inline-flex rounded-xl border border-[#1E1E2E] bg-[#12121A] p-1 gap-1">
                {[
                  { value: 'whitelist', label: 'С белыми списками' },
                  { value: 'regular', label: 'Обычный VPN' },
                ].map(tab => (
                  <button
                    key={tab.value}
                    onClick={() => setActiveTab(tab.value)}
                    className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                      activeTab === tab.value
                        ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-lg shadow-primary/20'
                        : 'text-[#94A3B8] hover:text-white'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {filteredPlans.map((plan, i) => (
              <PlanCard key={plan.id} plan={plan} index={i} featured={i === 0} />
            ))}
            {filteredPlans.length === 0 && (
              <div className="col-span-2 text-center text-[#94A3B8] py-12">Загрузка тарифов...</div>
            )}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <ScrollReveal>
            <div className="text-center mb-16">
              <h2 className="text-4xl font-bold text-white mb-4">
                Как это <span className="gradient-text">работает</span>
              </h2>
              <p className="text-[#94A3B8] text-lg">Четыре простых шага до защищённого интернета</p>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { step: '01', icon: <Users className="w-6 h-6" />, title: 'Регистрация', desc: 'Создайте аккаунт за 30 секунд' },
              { step: '02', icon: <Shield className="w-6 h-6" />, title: 'Выберите план', desc: 'Подберите оптимальный тариф' },
              { step: '03', icon: <Lock className="w-6 h-6" />, title: 'Оплата', desc: 'Переводом на карту или через СБП' },
              { step: '04', icon: <Globe className="w-6 h-6" />, title: 'Подключение', desc: 'Добавьте ссылку в VPN-клиент' },
            ].map((item, i) => (
              <ScrollReveal key={i} delay={i * 0.12}>
                <div className="relative">
                  {i < 3 && (
                    <div className="hidden md:block absolute top-8 left-full w-full h-px bg-gradient-to-r from-primary/40 to-transparent z-0" style={{ width: 'calc(100% - 40px)', left: 'calc(50% + 20px)' }} />
                  )}
                  <div className="vpn-card p-6 text-center relative z-10">
                    <div className="text-5xl font-black gradient-text mb-4 opacity-30">{item.step}</div>
                    <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mx-auto mb-4">
                      {item.icon}
                    </div>
                    <h3 className="font-bold text-white mb-2">{item.title}</h3>
                    <p className="text-[#94A3B8] text-sm">{item.desc}</p>
                  </div>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 relative z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <ScrollReveal>
            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold text-white mb-4">
                Часто задаваемые <span className="gradient-text">вопросы</span>
              </h2>
            </div>
          </ScrollReveal>
          <div className="space-y-3">
            {faqs.map((item, i) => <FAQItem key={i} item={item} index={i} />)}
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="py-24 relative z-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <ScrollReveal>
            <div className="relative rounded-2xl overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/30 via-secondary/20 to-primary/10" />
              <div className="absolute inset-0 border border-primary/20 rounded-2xl" />
              <div className="relative p-12 text-center">
                <h2 className="text-4xl font-bold text-white mb-4">Начните сейчас</h2>
                <p className="text-[#94A3B8] text-lg mb-8 max-w-xl mx-auto">
                  Присоединяйтесь к тысячам пользователей, которые уже защитили своё соединение
                </p>
                <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                  <Link
                    to="/register"
                    className="inline-flex items-center gap-2 px-10 py-4 rounded-xl btn-primary text-white font-bold text-lg glow-hover"
                  >
                    Создать аккаунт бесплатно
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                </motion.div>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>
    </div>
  )
}
