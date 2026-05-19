import React from 'react'

const countryFlags = {
  true: '🇷🇺',  // Russian
  false: '🌍',   // Foreign (default)
}

const locationFlags = {
  'Россия': '🇷🇺',
  'Нидерланды': '🇳🇱',
  'Германия': '🇩🇪',
  'Финляндия': '🇫🇮',
  'США': '🇺🇸',
  'Франция': '🇫🇷',
  'Великобритания': '🇬🇧',
}

function getFlag(provider) {
  if (provider.is_russian) return '🇷🇺'
  for (const [country, flag] of Object.entries(locationFlags)) {
    if (provider.location?.includes(country)) return flag
  }
  return '🌍'
}

export default function ProviderBadge({ provider, selected, onClick }) {
  const flag = getFlag(provider)
  
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 rounded-xl border transition-all text-left ${
        selected
          ? 'border-primary bg-primary/10 text-white'
          : 'border-[#1E1E2E] bg-[#12121A] text-[#94A3B8] hover:border-primary/40 hover:text-white'
      }`}
    >
      <span className="text-xl">{flag}</span>
      <div>
        <div className="text-sm font-medium">{provider.name}</div>
        <div className="text-xs opacity-70">{provider.location}</div>
      </div>
      {selected && (
        <div className="ml-auto w-4 h-4 rounded-full bg-primary flex items-center justify-center">
          <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 12 12">
            <path d="M10 3L5 8.5 2 5.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      )}
    </button>
  )
}
