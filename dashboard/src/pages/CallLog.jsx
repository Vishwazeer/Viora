import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import StatusBadge from '../components/StatusBadge'
import { Search, ChevronLeft, ChevronRight, ExternalLink, Phone, Filter } from 'lucide-react'
import { fetchCalls } from '../api/client'
import { formatDistanceToNow } from 'date-fns'

const DEMO_CALLS = Array.from({ length: 10 }, (_, i) => ({
  id: `demo-${i}`,
  patient_phone: `+9198765432${String(i).padStart(2,'0')}`,
  language: ['en-IN', 'hi-IN', 'mr-IN'][i % 3],
  primary_intent: ['appointment_book', 'lab_report', 'opd_timings', 'symptom_triage', 'emergency'][i % 5],
  outcome: ['resolved', 'escalated', 'resolved', 'abandoned', 'resolved'][i % 5],
  started_at: new Date(Date.now() - i * 3720000).toISOString(),
  duration_seconds: 72 + i * 28,
  turn_count: 3 + i,
  sentiment_score: 0.4 + (i % 5) * 0.12,
}))

function SentimentBar({ score }) {
  const pct = Math.round((score ?? 0.5) * 100)
  const color = pct >= 70 ? 'var(--green)' : pct >= 45 ? 'var(--amber)' : 'var(--red)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ width: 50, height: 5, background: '#e5e7eb', borderRadius: 999, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 999, transition: 'width 0.6s' }} />
      </div>
      <span style={{ fontSize: 11, color: 'var(--text-2)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{pct}%</span>
    </div>
  )
}

export default function CallLog() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialSearch = searchParams.get('search') || ''

  const [calls, setCalls] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState(initialSearch)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchCalls({ page, page_size: 15, search: search || undefined })
      setCalls(data.calls)
      setTotal(data.total)
    } catch {
      setCalls(DEMO_CALLS)
      setTotal(DEMO_CALLS.length)
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => { load() }, [load])

  const pages = Math.max(1, Math.ceil(total / 15))

  return (
    <div className="anim-fade-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 className="page-title">Patient Call Logs</h1>
          <p className="page-sub">{total} total voice sessions recorded and transcribed</p>
        </div>
        <div className="live-indicator">
          <span className="pulse-dot" />
          <span>{total} Calls Recorded</span>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Table Filter Bar */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid var(--border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
          background: 'var(--bg-card)'
        }}>
          <div className="search-wrap" style={{ width: 280 }}>
            <Search size={14} className="search-icon" />
            <input
              type="text"
              className="input"
              placeholder="Search phone number or intent..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
            />
          </div>
          <span className="badge badge-gray">Page {page} of {pages}</span>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Patient Phone</th>
                <th>Language</th>
                <th>Primary Goal</th>
                <th>Outcome</th>
                <th>Duration</th>
                <th>Turns</th>
                <th>Sentiment</th>
                <th>Started</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {calls.map(c => (
                <tr
                  key={c.id}
                  className="clickable"
                  onClick={() => navigate(`/calls/${c.id}`)}
                >
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 30, height: 30, borderRadius: '50%', background: '#f3f4f6',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                      }}>
                        <Phone size={13} color="var(--text-2)" />
                      </div>
                      <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-1)' }}>
                        {c.patient_phone}
                      </span>
                    </div>
                  </td>
                  <td><StatusBadge type="language" value={c.language} /></td>
                  <td>
                    <span style={{ textTransform: 'capitalize', fontWeight: 600, color: 'var(--text-1)', fontSize: 13 }}>
                      {(c.primary_intent || '—').replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td><StatusBadge type="outcome" value={c.outcome} /></td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-2)' }}>
                    {c.duration_seconds ? `${Math.floor(c.duration_seconds / 60)}m ${c.duration_seconds % 60}s` : '—'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-2)' }}>
                    {c.turn_count ?? '—'}
                  </td>
                  <td><SentimentBar score={c.sentiment_score} /></td>
                  <td style={{ fontSize: 11.5, color: 'var(--text-3)' }}>
                    {c.started_at ? formatDistanceToNow(new Date(c.started_at), { addSuffix: true }) : '—'}
                  </td>
                  <td>
                    <button className="btn-icon" style={{ width: 28, height: 28 }} title="View Transcript">
                      <ExternalLink size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{
          padding: '12px 20px', borderTop: '1px solid var(--border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: 'var(--bg-card)'
        }}>
          <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
            Showing {calls.length} of {total} records
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="btn btn-ghost"
              style={{ padding: '5px 12px', fontSize: 12 }}
            >
              <ChevronLeft size={13} /> Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page >= pages}
              className="btn btn-ghost"
              style={{ padding: '5px 12px', fontSize: 12 }}
            >
              Next <ChevronRight size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
