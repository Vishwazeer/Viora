import React, { useState, useEffect, useCallback } from 'react'
import StatCard from '../components/StatCard'
import { PhoneCall, CheckCircle, Clock, TrendingUp, Radio, Calendar as CalendarIcon, ChevronLeft, ChevronRight, Download, Activity, PhoneIncoming } from 'lucide-react'
import { fetchStats, fetchCalls } from '../api/client'
import StatusBadge from '../components/StatusBadge'

const TIME_FILTERS = ['Day', 'Week', 'Month', 'Year']

export default function LiveMonitor() {
  const [stats, setStats] = useState(null)
  const [recentCalls, setRecentCalls] = useState([])
  const [loading, setLoading] = useState(true)
  const [timeFilter, setTimeFilter] = useState('Day')
  const [selectedDate, setSelectedDate] = useState(new Date())

  const load = useCallback(async () => {
    try {
      const [statsData, callsData] = await Promise.all([
        fetchStats(),
        fetchCalls({ page: 1, page_size: 5 })
      ])
      setStats(statsData)
      setRecentCalls(callsData.calls || [])
    } catch {
      setStats({
        total_calls: 248, today_calls: 19,
        resolution_rate: 88.5, escalation_rate: 6.2,
        avg_duration_seconds: 135,
        intents: [
          { intent: 'Appointment', count: 94 },
          { intent: 'Lab Report', count: 48 },
          { intent: 'OPD Timings', count: 39 },
          { intent: 'Prescription', count: 33 },
          { intent: 'Triage', count: 26 },
        ],
        languages: [
          { language: 'en-IN', count: 142 },
          { language: 'hi-IN', count: 74 },
          { language: 'mr-IN', count: 38 },
        ],
      })
      setRecentCalls([
        { id: '1', patient_phone: '+919876543210', language: 'en-IN', primary_intent: 'appointment_book', outcome: 'resolved', duration_seconds: 82 },
        { id: '2', patient_phone: '+919811223344', language: 'hi-IN', primary_intent: 'symptom_triage', outcome: 'resolved', duration_seconds: 145 },
        { id: '3', patient_phone: '+919822334455', language: 'mr-IN', primary_intent: 'lab_report', outcome: 'resolved', duration_seconds: 64 },
        { id: '4', patient_phone: '+919833445566', language: 'en-IN', primary_intent: 'emergency', outcome: 'escalated', duration_seconds: 35 },
      ])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const refresh = setInterval(load, 10000)
    return () => clearInterval(refresh)
  }, [load])

  // Mini Calendar Days
  const generateDays = (date) => {
    const days = []
    for (let i = -2; i <= 2; i++) {
      const d = new Date(date)
      d.setDate(d.getDate() + i)
      days.push(d)
    }
    return days
  }
  const calendarDays = generateDays(selectedDate)

  // Simulated 7-day flow
  const weeklyData = [
    { label: 'Mon', count: 34 },
    { label: 'Tue', count: 42 },
    { label: 'Wed', count: 38 },
    { label: 'Thu', count: 51 },
    { label: 'Fri', count: 47 },
    { label: 'Sat', count: 29 },
    { label: 'Sun', count: 18 },
  ]
  const maxWeeklyCount = Math.max(...weeklyData.map(d => d.count), 1)

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ height: 28, width: 220 }} className="skeleton" />
      <div className="grid-4 stagger">
        {[0, 1, 2, 3].map(i => <div key={i} style={{ height: 130 }} className="skeleton anim-fade-up" />)}
      </div>
      <div className="grid-2-1" style={{ marginTop: 8 }}>
        <div style={{ height: 280 }} className="skeleton" />
        <div style={{ height: 280 }} className="skeleton" />
      </div>
    </div>
  )

  const mins = Math.floor((stats?.avg_duration_seconds ?? 0) / 60)
  const secs = (stats?.avg_duration_seconds ?? 0) % 60
  const resRate = stats?.resolution_rate ?? 85
  const donutOffset = 125 - (125 * resRate / 100)

  return (
    <div className="anim-fade-up">
      {/* Top Header Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 className="page-title">Reception Dashboard</h1>
          <p className="page-sub">Real-time telemetry, inbound call traffic, and AI resolution analytics</p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Time Filter Pills */}
          <div className="pill-group">
            {TIME_FILTERS.map(filter => (
              <button
                key={filter}
                onClick={() => setTimeFilter(filter)}
                className={`pill-btn ${timeFilter === filter ? 'active' : ''}`}
              >
                {filter}
              </button>
            ))}
          </div>

          <div className="live-indicator">
            <span className="pulse-dot" />
            Active
          </div>
        </div>
      </div>

      {/* 4 Stat Cards (1st Card Dark Drishti Style) */}
      <div className="grid-4 stagger" style={{ marginBottom: 24 }}>
        <StatCard
          label="Total Intake Calls"
          value={stats?.total_calls ?? 0}
          icon={PhoneIncoming}
          trend={14.8}
          dark={true}
        />
        <StatCard
          label="Today's Patient Calls"
          value={stats?.today_calls ?? 0}
          icon={TrendingUp}
          color="#10b981"
          trend={6.2}
        />
        <StatCard
          label="AI Resolution Rate"
          value={`${stats?.resolution_rate ?? 0}%`}
          icon={CheckCircle}
          color="#3d7bfd"
          trend={3.5}
        />
        <StatCard
          label="Avg Call Duration"
          value={`${mins}m ${secs}s`}
          icon={Clock}
          color="#f59e0b"
          trend={-4.1}
        />
      </div>

      {/* Charts & Calendar Grid */}
      <div className="grid-2-1" style={{ marginBottom: 24 }}>
        {/* Weekly Call Flow Bar Chart */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>Weekly Patient Call Flow</h3>
              <p style={{ fontSize: 11.5, color: 'var(--text-3)' }}>Call volume distribution across OPD days</p>
            </div>
            <span className="badge badge-dark">Weekly</span>
          </div>

          {/* Bar Visualizer */}
          <div style={{ height: 180, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 14, padding: '0 8px' }}>
            {weeklyData.map((data, i) => {
              const heightPercent = Math.max((data.count / maxWeeklyCount) * 100, 8)
              return (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end', gap: 8 }}>
                  <div style={{
                    width: '100%',
                    height: `${heightPercent}%`,
                    background: i === 3 ? 'var(--bg-dark)' : '#374151',
                    borderRadius: 10,
                    transition: 'height 0.4s ease',
                    position: 'relative'
                  }}>
                    <div style={{
                      position: 'absolute', top: -22, left: '50%', transform: 'translateX(-50%)',
                      fontSize: 10, fontWeight: 700, color: 'var(--text-2)', fontFamily: 'var(--font-mono)'
                    }}>
                      {data.count}
                    </div>
                  </div>
                  <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-3)' }}>
                    {data.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Right Column: Mini Calendar & Donut */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Mini Calendar Card */}
          <div className="card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <button
                onClick={() => { const d = new Date(selectedDate); d.setMonth(d.getMonth() - 1); setSelectedDate(d); }}
                className="btn-icon" style={{ width: 28, height: 28 }}
              >
                <ChevronLeft size={14} />
              </button>
              <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-1)' }}>
                {selectedDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
              </span>
              <button
                onClick={() => { const d = new Date(selectedDate); d.setMonth(d.getMonth() + 1); setSelectedDate(d); }}
                className="btn-icon" style={{ width: 28, height: 28 }}
              >
                <ChevronRight size={14} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', textAlign: 'center', gap: 6 }}>
              {calendarDays.map((d, i) => (
                <span key={`day-${i}`} style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--text-3)' }}>
                  {d.toLocaleDateString('en-US', { weekday: 'short' })}
                </span>
              ))}
              {calendarDays.map((d, i) => {
                const isSelected = d.toDateString() === selectedDate.toDateString()
                return (
                  <button
                    key={`date-${i}`}
                    onClick={() => setSelectedDate(d)}
                    style={{
                      padding: '7px 0', borderRadius: 'var(--r-sm)', border: 'none', cursor: 'pointer',
                      fontSize: 12, fontWeight: 700, transition: 'all 0.15s',
                      background: isSelected ? 'var(--bg-dark)' : 'transparent',
                      color: isSelected ? '#fff' : 'var(--text-1)',
                      boxShadow: isSelected ? 'var(--shadow-sm)' : 'none'
                    }}
                  >
                    {d.getDate()}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Daily Resolution Donut */}
          <div className="card" style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-1)', marginBottom: 2 }}>Daily Resolution</h4>
              <span style={{ fontSize: 11.5, color: 'var(--green)', fontWeight: 600 }}>↗ {resRate}% Handled by AI</span>
            </div>
            <div style={{ position: 'relative', width: 52, height: 52, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
                <circle cx="26" cy="26" r="21" stroke="#e5e7eb" strokeWidth="4.5" fill="transparent" />
                <circle
                  cx="26" cy="26" r="21"
                  stroke="#111827" strokeWidth="4.5" fill="transparent"
                  strokeDasharray="132" strokeDashoffset={donutOffset}
                  style={{ transition: 'stroke-dashoffset 1s ease' }}
                />
              </svg>
              <span style={{ position: 'absolute', fontSize: 11, fontWeight: 800, color: 'var(--text-1)' }}>
                {Math.round(resRate)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>Live Inbound Feed</h3>
            <p style={{ fontSize: 11.5, color: 'var(--text-3)' }}>Latest patient interactions processed by Viora</p>
          </div>
          <span className="badge badge-gray">{recentCalls.length} Recent</span>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Patient Phone</th>
                <th>Language</th>
                <th>Intent</th>
                <th>Outcome</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {recentCalls.map(c => (
                <tr key={c.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: '50%', background: '#f3f4f6',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 11
                      }}>
                        📞
                      </div>
                      <span style={{ fontWeight: 600, color: 'var(--text-1)', fontFamily: 'var(--font-mono)' }}>{c.patient_phone}</span>
                    </div>
                  </td>
                  <td><StatusBadge type="language" value={c.language} /></td>
                  <td>
                    <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>
                      {(c.primary_intent || 'General Inquiry').replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td><StatusBadge type="outcome" value={c.outcome} /></td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)', fontSize: 12 }}>
                    {c.duration_seconds}s
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

