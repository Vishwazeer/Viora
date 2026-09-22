import React, { useEffect, useState } from 'react'
import { Calendar, MessageSquare, CheckCircle, Clock, User, Phone, Stethoscope, ChevronRight } from 'lucide-react'

export default function Appointments() {
  const [appointments, setAppointments] = useState([])
  const [smsLogs, setSmsLogs] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      const headers = { 'X-Admin-Key': import.meta.env.VITE_ADMIN_KEY || 'demo-admin-key-2024' }
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const [apptsRes, smsRes] = await Promise.all([
        fetch(`${apiUrl}/appointments/`, { headers }),
        fetch(`${apiUrl}/appointments/sms-log`, { headers })
      ])
      
      if (apptsRes.ok) setAppointments(await apptsRes.json())
      if (smsRes.ok) setSmsLogs(await smsRes.json())
    } catch (err) {
      console.error("Failed to fetch appointment data", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 4000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ height: 28, width: 220 }} className="skeleton" />
        <div className="grid-2 stagger">
          <div style={{ height: 350 }} className="skeleton anim-fade-up" />
          <div style={{ height: 350 }} className="skeleton anim-fade-up" />
        </div>
      </div>
    )
  }

  return (
    <div className="anim-fade-up">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 className="page-title">Appointments & SMS Log</h1>
          <p className="page-sub">Confirmed clinic bookings and automated SMS dispatch feed</p>
        </div>
        <div className="live-indicator">
          <span className="pulse-dot" />
          Live Sync (4s)
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 20 }}>
        {/* Appointments Column */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-card)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 34, height: 34, borderRadius: 'var(--r-sm)',
                background: 'var(--blue-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <Calendar size={18} color="var(--blue)" />
              </div>
              <div>
                <h2 style={{ fontSize: 14.5, fontWeight: 700, color: 'var(--text-1)' }}>Latest Bookings</h2>
                <div style={{ fontSize: 11, color: 'var(--text-3)' }}>{appointments.length} confirmed appointments</div>
              </div>
            </div>
            <span className="badge badge-dark">{appointments.length} Booked</span>
          </div>

          <div style={{ maxHeight: 560, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {appointments.length === 0 ? (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)' }}>
                <Clock size={32} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
                <p style={{ fontSize: 13, fontWeight: 600 }}>No appointments booked yet.</p>
                <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>Call Viora on the Simulator to create one.</p>
              </div>
            ) : (
              appointments.map(a => (
                <div
                  key={a.id}
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-lg)',
                    padding: '16px',
                    boxShadow: 'var(--shadow-sm)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-dark)',
                        color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center'
                      }}>
                        <User size={15} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 13.5, color: 'var(--text-1)' }}>{a.patient_name}</div>
                        <div style={{ fontSize: 11.5, color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Phone size={11} /> {a.patient_phone}
                        </div>
                      </div>
                    </div>
                    <span className="badge badge-green">
                      <CheckCircle size={11} />
                      {a.status || 'Confirmed'}
                    </span>
                  </div>

                  <div style={{
                    background: '#ffffff',
                    borderRadius: 'var(--r-md)',
                    padding: '12px 14px',
                    border: '1px solid var(--border)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12.5 }}>
                      <Stethoscope size={14} color="var(--blue)" />
                      <span style={{ fontWeight: 700, color: 'var(--text-1)' }}>{a.doctor_name}</span>
                      <span style={{ color: 'var(--text-3)', fontSize: 11.5 }}>({a.department})</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, color: 'var(--green)', marginLeft: 21, fontWeight: 600 }}>
                      <Clock size={13} />
                      <span>{a.appointment_date} at {a.appointment_time}</span>
                    </div>
                    {a.reason && (
                      <div style={{ fontSize: 11.5, color: 'var(--text-3)', marginLeft: 21 }}>
                        Reason: {a.reason}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Outbound SMS Column */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-card)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 34, height: 34, borderRadius: 'var(--r-sm)',
                background: 'var(--green-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <MessageSquare size={18} color="var(--green)" />
              </div>
              <div>
                <h2 style={{ fontSize: 14.5, fontWeight: 700, color: 'var(--text-1)' }}>Outbound SMS (Demo)</h2>
                <div style={{ fontSize: 11, color: 'var(--text-3)' }}>Automated patient notifications</div>
              </div>
            </div>
            <span className="badge badge-green">{smsLogs.length} Sent</span>
          </div>

          <div style={{ maxHeight: 560, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {smsLogs.length === 0 ? (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)' }}>
                <MessageSquare size={32} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
                <p style={{ fontSize: 13, fontWeight: 600 }}>No SMS notifications logged yet.</p>
                <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>Booking an appointment triggers SMS dispatch.</p>
              </div>
            ) : (
              smsLogs.map(sms => (
                <div
                  key={sms.id}
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-lg)',
                    padding: '14px 16px',
                    display: 'flex',
                    gap: 12,
                    alignItems: 'flex-start',
                    boxShadow: 'var(--shadow-sm)'
                  }}
                >
                  <div style={{
                    width: 32, height: 32, borderRadius: '50%', background: 'var(--green-dim)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 2
                  }}>
                    <MessageSquare size={15} color="var(--green)" />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-1)' }}>
                        To: {sms.recipient_phone}
                      </span>
                      <span style={{ fontSize: 10.5, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                        {new Date(sms.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <div style={{
                      background: '#ffffff',
                      borderRadius: 'var(--r-md)',
                      padding: '12px 14px',
                      fontSize: 12,
                      color: 'var(--text-1)',
                      border: '1px solid var(--border)',
                      fontFamily: 'var(--font-mono)',
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.5
                    }}>
                      {sms.message_body}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

