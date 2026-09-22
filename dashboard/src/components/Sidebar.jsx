import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  HeartPulse, Settings, Radio, Phone, CalendarDays, Activity, PhoneCall, AlertTriangle, ChevronRight, Zap
} from 'lucide-react'

const NAV = [
  { to: '/monitor',      icon: Radio,        label: 'Dashboard' },
  { to: '/simulator',    icon: Phone,        label: 'Call Simulator' },
  { to: '/calls',        icon: PhoneCall,    label: 'Call Logs' },
  { to: '/appointments', icon: CalendarDays, label: 'Appointments & SMS' },
  { to: '/escalations',  icon: AlertTriangle,label: 'Escalations' },
  { to: '/health',       icon: HeartPulse,   label: 'System Health' },
  { to: '/settings',     icon: Settings,     label: 'Settings' },
]

export default function Sidebar() {
  const navigate = useNavigate()

  return (
    <aside className="sidebar">
      <div>
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="logo-icon">
            <Activity size={20} color="#fff" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: '-0.02em', color: 'var(--text-1)' }}>
              Viora
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 600, letterSpacing: '0.04em' }}>
              HEALTHCARE RECEPTIONIST
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="sidebar-nav">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              {({ isActive }) => (
                <>
                  <div
                    className="nav-icon"
                    style={{
                      background: isActive ? 'var(--bg-dark)' : 'transparent',
                      color: isActive ? '#fff' : 'var(--text-2)'
                    }}
                  >
                    <Icon size={16} strokeWidth={isActive ? 2.3 : 1.8} />
                  </div>
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Dark Quick Action Card (Drishti Inspired) */}
        <div style={{ marginTop: 24, padding: '0 4px' }}>
          <div style={{
            background: 'var(--bg-dark)',
            color: '#fff',
            padding: 18,
            borderRadius: 'var(--r-lg)',
            boxShadow: 'var(--shadow-md)',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <div style={{ position: 'relative', zIndex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <span className="pulse-dot" />
                <h3 style={{ fontSize: 13, fontWeight: 700 }}>Live Voice Agent</h3>
              </div>
              <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 12 }}>
                Test the Indian multilingual triage & appointment flow.
              </p>
              <button
                onClick={() => navigate('/simulator')}
                className="btn btn-cyan-blue"
                style={{
                  width: '100%',
                  justifyContent: 'center',
                  fontSize: 12,
                  padding: '7px 12px',
                  borderRadius: 'var(--r-pill)',
                  fontWeight: 700
                }}
              >
                <Phone size={13} />
                Open Simulator
              </button>
            </div>
            <div style={{
              position: 'absolute', top: -20, right: -20, width: 80, height: 80,
              background: 'rgba(34,211,168,0.15)', borderRadius: '50%', filter: 'blur(16px)'
            }} />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="pulse-dot" />
            <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-1)' }}>Live Ready</span>
          </div>
          <span style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>v1.0.0</span>
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-3)' }}>DPDP Act · 100% Compliant</div>
      </div>
    </aside>
  )
}

