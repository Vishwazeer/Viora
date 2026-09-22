import React, { useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import { Search, Bell, AlertTriangle, Users, Activity, X, ShieldCheck, User } from 'lucide-react'

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifications, setNotifications] = useState([
    { id: '1', title: 'System Online', body: 'Viora receptionist is active and ready for calls.', time: 'Just now', type: 'info', read: false },
    { id: '2', title: 'Emergency Protocol Ready', body: '108 Ambulance escalation and red-flag triage active.', time: '10m ago', type: 'alert', read: false },
    { id: '3', title: 'HMS Sync Complete', body: 'Doctor rosters and slot availability updated from mock HMS.', time: '1h ago', type: 'success', read: true },
  ])

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        {/* Top Header */}
        <header className="top-header">
          <div className="search-wrap" style={{ width: 320 }}>
            <Search size={15} className="search-icon" />
            <input
              type="text"
              placeholder="Search patients, calls, or doctors..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && searchQuery) {
                  navigate(`/calls?search=${encodeURIComponent(searchQuery)}`)
                }
              }}
              className="input"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)' }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            {/* Notification Center */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="btn-icon"
                style={{ position: 'relative' }}
                title="Notification Center"
              >
                <Bell size={16} />
                {unreadCount > 0 && (
                  <span style={{
                    position: 'absolute', top: 7, right: 7, width: 8, height: 8,
                    background: 'var(--red)', borderRadius: '50%', border: '2px solid #fff'
                  }} />
                )}
              </button>

              {showNotifications && (
                <div style={{
                  position: 'absolute', right: 0, marginTop: 8, width: 320,
                  background: 'var(--bg-card)', borderRadius: 'var(--r-lg)',
                  boxShadow: 'var(--shadow-lg)', border: '1px solid var(--border)',
                  zIndex: 50, overflow: 'hidden'
                }}>
                  <div style={{
                    padding: '12px 16px', borderBottom: '1px solid var(--border)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    background: '#f9fafb'
                  }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-1)' }}>Notifications</span>
                    {unreadCount > 0 && (
                      <button
                        onClick={() => setNotifications(prev => prev.map(n => ({ ...n, read: true })))}
                        style={{ fontSize: 11, color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}
                      >
                        Mark all read
                      </button>
                    )}
                  </div>
                  <div style={{ maxHeight: 280, overflowY: 'auto' }}>
                    {notifications.map(n => (
                      <div
                        key={n.id}
                        style={{
                          padding: '12px 16px', borderBottom: '1px solid var(--border-light)',
                          display: 'flex', gap: 10, alignItems: 'flex-start',
                          background: !n.read ? 'rgba(61,123,253,0.03)' : 'transparent'
                        }}
                      >
                        <div style={{
                          width: 28, height: 28, borderRadius: '50%',
                          background: n.type === 'alert' ? 'var(--red-dim)' : n.type === 'success' ? 'var(--green-dim)' : 'var(--blue-dim)',
                          color: n.type === 'alert' ? 'var(--red)' : n.type === 'success' ? 'var(--green)' : 'var(--blue)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1
                        }}>
                          {n.type === 'alert' ? <AlertTriangle size={13} /> : <Activity size={13} />}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-1)' }}>{n.title}</div>
                            <span style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 500 }}>{n.time}</span>
                          </div>
                          <p style={{ fontSize: 11.5, color: 'var(--text-2)', marginTop: 2, lineHeight: 1.4 }}>{n.body}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Clinic Profile Chip */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              background: 'var(--bg-card)', padding: '5px 12px 5px 6px',
              borderRadius: 'var(--r-pill)', border: '1px solid var(--border)',
              boxShadow: 'var(--shadow-sm)'
            }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', background: 'var(--bg-dark)',
                color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, fontSize: 11
              }}>
                VH
              </div>
              <div style={{ lineHeight: 1.2 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-1)' }}>Viora Health</div>
                <div style={{ fontSize: 10, color: 'var(--text-3)' }}>Healthcare Platform</div>
              </div>
            </div>
          </div>
        </header>

        <Outlet />
      </main>
    </div>
  )
}

