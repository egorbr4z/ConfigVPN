import React from 'react'
import { Link } from 'react-router-dom'
import { Shield, Mail } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="border-t border-[#1E1E2E] bg-[#0A0A0F] mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div>
            <Link to="/" className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                <Shield className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-lg text-white">ConfigVPN</span>
            </Link>
            <p className="text-[#94A3B8] text-sm leading-relaxed">
              Быстрый и надёжный VPN с технологией белых списков. Безопасный доступ к любым ресурсам.
            </p>
          </div>

          {/* Links */}
          <div>
            <h3 className="text-white font-semibold mb-4">Навигация</h3>
            <ul className="space-y-2">
              {[
                { to: '/', label: 'Главная' },
                { to: '/plans', label: 'Тарифы' },
                { to: '/custom-vpn', label: 'Свой сервер' },
                { to: '/register', label: 'Регистрация' },
              ].map((link) => (
                <li key={link.to}>
                  <Link to={link.to} className="text-[#94A3B8] hover:text-white text-sm transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Info */}
          <div>
            <h3 className="text-white font-semibold mb-4">Поддержка</h3>
            <ul className="space-y-2 text-[#94A3B8] text-sm">
              <li>Поддерживаемые клиенты:</li>
              <li className="ml-2">Android: Hiddify, Nekobox</li>
              <li className="ml-2">iOS: Shadowrocket</li>
              <li className="ml-2">PC: Hiddify Next</li>
            </ul>
          </div>
        </div>

        <div className="border-t border-[#1E1E2E] mt-8 pt-8 text-center text-[#94A3B8] text-sm">
          <p>© 2024 ConfigVPN. Все права защищены.</p>
        </div>
      </div>
    </footer>
  )
}
