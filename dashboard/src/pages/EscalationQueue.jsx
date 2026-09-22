import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ExternalLink, Zap, AlertTriangle, Phone, CheckCircle, ShieldAlert } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import { fetchEscalations } from '../api/client'
import { formatDistanceToNow } from 'date-fns'

const REASON_META = {
  emergency:         { label: 'Medical Emergency (108)', cls: 'badge-red',    icon: '🚨' },
  patient_requested: { label: 'Human Front-Desk Request', cls: 'badge-amber', icon: '👤' },
  max_clarifications:{ label: 'Max Retries Reached', cls: 'badge-gray', icon: '🔄' },
  technical_failure: { label: 'Audio Bridge Issue', cls: 'badge-gray',   icon: '⚙️' },
  mental_health:     { label: 'Mental Health Advisory', cls: 'badge-purple', icon: '🧠' },
}

const DEMO = [
  { id: 'e1', patient_phone: '+919876543210', language: 'en-IN', escalation_reason: 'emergency', started_at: new Date(Date.now() - 120000).toISOString(), duration_seconds: 38, turn_count: 2, outcome: 'escalated' },
  { id: 'e2', patient_phone: '+919988776655', language: 'hi-IN', escalation_reason: 'mental_health', started_at: new Date(Date.now() - 1800000).toISOString(), duration_seconds: 95, turn_count: 6, outcome: 'escalated' },
  { id: 'e3', patient_phone: '+919123456789', language: 'mr-IN', escalation_reason: 'patient_requested', started_at: new Date(Date.now() - 7200000).toISOString(), duration_seconds: 112, turn_count: 4, outcome: 'escalated' },
]

export default function EscalationQueue() {
  const navigate = useNavigate()
  const [calls, setCalls] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchEscalations()
        setCalls(data.calls || [])
        setTotal(data.total || 0)
      } catch {
        setCalls(DEMO)
        setTotal(DEMO.length)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className="anim-fade-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 className="page-title">Escalation Queue</h1>
          <p className="page-sub">{total} high-priority calls transferred to clinic medical staff</p>
        </div>
        <div className="badge badge-red" style={{ padding: '6px 14px', fontSize: 12 }}>
          <ShieldAlert size={14} />
          {total} Requiring Human Review
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Patient Phone</th>
                <th>Language</th>
                <th>Escalation Trigger</th>
                <th>Duration</th>
                <th>Turns</th>
                <th>Transferred At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {calls.map(c => {
                const meta = REASON_META[c.escalation_reason] || { label: c.escalation_reason || 'Manual Transfer', cls: 'badge-gray', icon: '⚡' }
                return (
                  <tr
                    key={c.id}
                    className="clickable"
                    onClick={() => navigate(`/calls/${c.id}`)}
                  >
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{
                          width: 32, height: 32, borderRadius: '50%', background: 'var(--red-dim)',
                          color: 'var(--red)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}>
                          <AlertTriangle size={15} />
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-1)' }}>
                          {c.patient_phone}
                        </span>
                      </div>
                    </td>
                    <td><StatusBadge type="language" value={c.language} /></td>
                    <td>
                      <span className={`badge ${meta.cls}`} style={{ gap: 6 }}>
                        <span>{meta.icon}</span>
                        {meta.label}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-2)' }}>
                      {c.duration_seconds}s
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-2)' }}>
                      {c.turn_count}
                    </td>
                    <td style={{ fontSize: 11.5, color: 'var(--text-3)' }}>
                      {c.started_at ? formatDistanceToNow(new Date(c.started_at), { addSuffix: true }) : '—'}
                    </td>
                    <td>
                      <button
                        onClick={e => { e.stopPropagation(); navigate(`/calls/${c.id}`) }}
                        className="btn btn-ghost"
                        style={{ padding: '4px 10px', fontSize: 11.5 }}
                      >
                        Review <ExternalLink size={11} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
