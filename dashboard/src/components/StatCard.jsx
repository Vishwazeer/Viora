import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

export default function StatCard({ label, value, icon: Icon, color = '#3d7bfd', trend, dark = false, negative = false }) {
  const isPositive = trend !== undefined ? (typeof trend === 'number' ? trend >= 0 : !trend.startsWith('-')) : true
  const displayTrend = trend !== undefined ? (typeof trend === 'number' ? `${trend >= 0 ? '+' : ''}${trend}%` : trend) : null

  return (
    <div className={`stat-card anim-fade-up ${dark ? 'dark' : ''}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div
          className="stat-icon"
          style={{
            background: dark ? 'rgba(255,255,255,0.1)' : `${color}14`,
            color: dark ? '#fff' : color
          }}
        >
          {Icon && <Icon size={18} strokeWidth={2.2} />}
        </div>
        {displayTrend && (
          <span style={{
            fontSize: 11.5,
            fontWeight: 700,
            padding: '3px 9px',
            borderRadius: 'var(--r-pill)',
            background: dark ? 'rgba(255,255,255,0.15)' : (negative ? 'var(--red-dim)' : 'var(--green-dim)'),
            color: dark ? '#fff' : (negative ? 'var(--red)' : 'var(--green)'),
            display: 'inline-flex',
            alignItems: 'center',
            gap: 3
          }}>
            {isPositive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
            {displayTrend}
          </span>
        )}
      </div>

      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  )
}

