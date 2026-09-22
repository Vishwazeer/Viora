import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Bot, Clock, Mic, Hash, FileText, CheckCircle } from 'lucide-react'
import { fetchCall } from '../api/client'
import StatusBadge from '../components/StatusBadge'

const DEMO_CALL = {
  id: 'demo-1', patient_phone: '+919876543210',
  language: 'en-IN', primary_intent: 'appointment_book',
  outcome: 'resolved', duration_seconds: 187, turn_count: 10,
  started_at: new Date().toISOString(), consent_given: true,
  sentiment_score: 0.78,
  summary: "Patient successfully booked an appointment with Dr. Priya Sharma for Friday at 10:00 AM. Verbal DPDP consent was verified and appointment confirmation SMS dispatched.",
  transcript: [
    { role: 'assistant', text: "Namaste! Thank you for calling Viora Health. I'm Viora, your healthcare receptionist. How may I help you today?", language: 'en-IN' },
    { role: 'user', text: 'I want to book an appointment with Dr. Priya Sharma for this Friday.', language: 'en-IN' },
    { role: 'assistant', text: "I'd be happy to help with that. May I please have your full name and preferred time slot for Friday?", language: 'en-IN' },
    { role: 'user', text: 'My name is Ramesh Joshi and around 10:00 AM please.', language: 'en-IN' },
    { role: 'assistant', text: "Thank you Ramesh-ji. Dr. Priya Sharma is available at 10:00 AM on Friday. I have confirmed your appointment. You will receive an SMS confirmation on your phone.", language: 'en-IN' },
    { role: 'user', text: 'Thank you very much, that was fast.', language: 'en-IN' },
    { role: 'assistant', text: "You're most welcome! Take care and have a wonderful day.", language: 'en-IN' },
  ],
}

function MetaItem({ icon: Icon, label, value, valueColor }) {
  return (
    <div style={{ background: '#f9fafb', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10.5, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
        <Icon size={12} />
        {label}
      </div>
      <div style={{ fontSize: 13.5, fontWeight: 700, color: valueColor || 'var(--text-1)', marginTop: 4 }}>
        {value}
      </div>
    </div>
  )
}

export default function TranscriptViewer() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [call, setCall] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchCall(id)
        setCall(data)
      } catch {
        setCall(DEMO_CALL)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ height: 28, width: 140 }} className="skeleton" />
      <div style={{ height: 120 }} className="skeleton" />
      <div style={{ height: 400 }} className="skeleton" />
    </div>
  )

  if (!call) return (
    <div style={{ color: 'var(--red)', padding: 40, textAlign: 'center' }}>Call transcript record not found.</div>
  )

  const mins = Math.floor((call.duration_seconds ?? 0) / 60)
  const secs = (call.duration_seconds ?? 0) % 60
  const sentPct = Math.round((call.sentiment_score ?? 0.5) * 100)

  return (
    <div className="anim-fade-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <button className="btn btn-ghost" onClick={() => navigate('/calls')} style={{ gap: 6 }}>
          <ArrowLeft size={14} /> Back to Logs
        </button>
        <span className="badge badge-dark">Call #{id}</span>
      </div>

      {/* Call Metadata Card */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: call.summary ? 16 : 0 }}>
          <MetaItem icon={Mic}   label="Patient Phone" value={<span style={{ fontFamily: 'var(--font-mono)' }}>{call.patient_phone}</span>} />
          <MetaItem icon={Hash}  label="Outcome"       value={<StatusBadge type="outcome" value={call.outcome} />} />
          <MetaItem icon={Clock} label="Duration"      value={`${mins}m ${secs}s`} />
          <MetaItem icon={Hash}  label="Language"      value={<StatusBadge type="language" value={call.language} />} />
          <MetaItem icon={Hash}  label="Caller Goal"   value={(call.primary_intent || '—').replace(/_/g, ' ')} />
          <MetaItem icon={Hash}  label="Turn Count"    value={`${call.turn_count} messages`} />
          <MetaItem icon={CheckCircle} label="DPDP Consent" value={call.consent_given ? '✓ Verified' : '✗ Not Captured'} valueColor={call.consent_given ? 'var(--green)' : 'var(--red)'} />
          <div style={{ background: '#f9fafb', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 10.5, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>Sentiment</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
              <div style={{ flex: 1, height: 6, background: '#e5e7eb', borderRadius: 999, overflow: 'hidden' }}>
                <div style={{
                  width: `${sentPct}%`, height: '100%', borderRadius: 999,
                  background: sentPct >= 70 ? 'var(--green)' : sentPct >= 45 ? 'var(--amber)' : 'var(--red)',
                }} />
              </div>
              <span style={{ fontSize: 12.5, fontFamily: 'var(--font-mono)', color: 'var(--text-1)', fontWeight: 700 }}>{sentPct}%</span>
            </div>
          </div>
        </div>

        {call.summary && (
          <div style={{ paddingTop: 14, borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700, marginBottom: 6 }}>
              Clinical AI Summary
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-1)', lineHeight: 1.6 }}>{call.summary}</p>
          </div>
        )}
      </div>

      {/* Transcript Chat Log */}
      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-1)', marginBottom: 20, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Conversation Transcript ({call.turn_count} Turns)
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {(call.transcript || []).map((turn, i) => (
            <div
              key={i}
              className={`bubble-wrap${turn.role === 'user' ? ' user' : ''} anim-fade-up`}
            >
              <div className={`bubble-avatar ${turn.role === 'user' ? 'user' : 'agent'}`}>
                {turn.role === 'user'
                  ? <User size={15} color="#fff" />
                  : <Bot size={15} color="#fff" />}
              </div>
              <div className={`bubble ${turn.role === 'user' ? 'user' : 'agent'}`}>
                <div className="bubble-meta" style={{ color: turn.role === 'user' ? '#9ca3af' : 'var(--text-3)' }}>
                  {turn.role === 'user' ? 'Patient' : 'Viora Receptionist'}
                  {turn.language && (
                    <span style={{ marginLeft: 8, opacity: 0.8 }}>
                      · {turn.language === 'en-IN' ? 'English' : turn.language === 'hi-IN' ? 'Hindi' : 'Marathi'}
                    </span>
                  )}
                </div>
                {turn.text}
              </div>
            </div>
          ))}

          {(!call.transcript || call.transcript.length === 0) && (
            <p style={{ color: 'var(--text-3)', textAlign: 'center', padding: 40 }}>No transcript messages recorded for this call.</p>
          )}
        </div>
      </div>
    </div>
  )
}
