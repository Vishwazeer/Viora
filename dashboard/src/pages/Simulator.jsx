/* global TextDecoder */
import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  Room,
  RoomEvent,
  Track,
  createLocalAudioTrack,
} from 'livekit-client'
import { Phone, PhoneOff, Mic, MicOff, Loader, Radio, MessageSquare, AlertCircle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || ''
const ADMIN_KEY = import.meta.env.VITE_ADMIN_KEY || ''

const CALL_STATES = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  AGENT_JOINED: 'agent_joined',
  ENDED: 'ended',
  ERROR: 'error',
}

const STATE_LABELS = {
  [CALL_STATES.IDLE]:        { text: 'Ready to call', color: 'var(--text-3)' },
  [CALL_STATES.CONNECTING]:  { text: 'Connecting…',   color: '#f5a623' },
  [CALL_STATES.CONNECTED]:   { text: 'Waiting for Viora…', color: '#f5a623' },
  [CALL_STATES.AGENT_JOINED]:{ text: 'Viora is listening', color: '#22d3a8' },
  [CALL_STATES.ENDED]:       { text: 'Call ended',    color: 'var(--text-3)' },
  [CALL_STATES.ERROR]:       { text: 'Error',         color: '#f04747' },
}

export default function Simulator() {
  const [callState, setCallState] = useState(CALL_STATES.IDLE)
  const [transcript, setTranscript] = useState([])
  const [isMuted, setIsMuted] = useState(false)
  const [error, setError] = useState(null)
  const [duration, setDuration] = useState(0)

  const roomRef = useRef(null)
  const localTrackRef = useRef(null)
  const timerRef = useRef(null)
  const transcriptEndRef = useRef(null)

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript])

  // Call timer
  useEffect(() => {
    if (callState === CALL_STATES.AGENT_JOINED) {
      timerRef.current = setInterval(() => setDuration(d => d + 1), 1000)
    } else {
      clearInterval(timerRef.current)
      if (callState === CALL_STATES.IDLE || callState === CALL_STATES.ENDED) setDuration(0)
    }
    return () => clearInterval(timerRef.current)
  }, [callState])

  const formatDuration = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  const addMessage = useCallback((role, text) => {
    setTranscript(prev => [...prev, { role, text, ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }])
  }, [])

  const startCall = async () => {
    setError(null)
    setTranscript([])
    setCallState(CALL_STATES.CONNECTING)

    try {
      // 1. Get LiveKit token from backend
      const roomName = `viora-demo-${Date.now()}`
      const res = await fetch(`${API_BASE}/admin/simulator/token?room_name=${roomName}&identity=admin-${Date.now()}`, {
        method: 'POST',
        headers: { 'X-Admin-Key': ADMIN_KEY },
      })
      if (!res.ok) throw new Error(`Token request failed: ${res.status}`)
      const { token, livekit_url } = await res.json()

      // 2. Create and connect room
      const room = new Room({ adaptiveStream: true, dynacast: true })
      roomRef.current = room

      // Room event listeners
      room.on(RoomEvent.ParticipantConnected, (participant) => {
        if (participant.identity?.startsWith('agent') || participant.identity?.startsWith('viora')) {
          setCallState(CALL_STATES.AGENT_JOINED)
          addMessage('system', 'Viora has joined the call')
        }
      })

      room.on(RoomEvent.ParticipantDisconnected, () => {
        addMessage('system', 'Viora has left the call')
        endCall()
      })

      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach()
          el.style.display = 'none'
          document.body.appendChild(el)
        }
      })

      room.on(RoomEvent.DataReceived, (data) => {
        try {
          const msg = JSON.parse(new TextDecoder().decode(data))
          if (msg.type === 'transcript') {
            addMessage(msg.role || 'assistant', msg.text)
          }
        } catch { /* ignore non-JSON data */ }
      })

      room.on(RoomEvent.Disconnected, () => {
        setCallState(prev => prev !== CALL_STATES.ENDED ? CALL_STATES.ENDED : prev)
      })

      await room.connect(livekit_url, token)
      setCallState(CALL_STATES.CONNECTED)

      // 3. Publish microphone
      const localAudio = await createLocalAudioTrack({ echoCancellation: true, noiseSuppression: true })
      localTrackRef.current = localAudio
      await room.localParticipant.publishTrack(localAudio)

      addMessage('system', 'Microphone connected — waiting for Viora agent to join…')

    } catch (err) {
      console.error('Call error:', err)
      setError(err.message)
      setCallState(CALL_STATES.ERROR)
    }
  }

  const endCall = useCallback(async () => {
    setCallState(CALL_STATES.ENDED)
    if (localTrackRef.current) {
      localTrackRef.current.stop()
      localTrackRef.current = null
    }
    if (roomRef.current) {
      await roomRef.current.disconnect()
      roomRef.current = null
    }
    addMessage('system', 'Call ended')
  }, [addMessage])

  const toggleMute = () => {
    if (!localTrackRef.current) return
    if (isMuted) {
      localTrackRef.current.unmute()
    } else {
      localTrackRef.current.mute()
    }
    setIsMuted(m => !m)
  }

  const isActive = callState === CALL_STATES.CONNECTED || callState === CALL_STATES.AGENT_JOINED

  return (
    <div className="anim-fade-up" style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 className="page-title">Voice Call Simulator</h1>
          <p className="page-sub">Interactive browser-to-agent consultation — English, Hindi & Marathi</p>
        </div>
        {isActive && (
          <div className="live-indicator">
            <span className="pulse-dot" />
            <span>Duration: <strong style={{ color: 'var(--text-1)' }}>{formatDuration(duration)}</strong></span>
          </div>
        )}
      </div>

      {/* Info banner */}
      {callState === CALL_STATES.IDLE && (
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 'var(--r-lg)', padding: '16px 20px', marginBottom: 24,
          display: 'flex', alignItems: 'center', gap: 14, boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{
            width: 38, height: 38, borderRadius: '50%', background: 'var(--bg-dark)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', flexShrink: 0
          }}>
            <Radio size={18} />
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.4 }}>
            <strong style={{ color: 'var(--text-1)' }}>Real-Time WebRTC Simulation: </strong>
            Click <strong style={{ color: 'var(--text-1)' }}>Call Viora</strong> below to connect. Speak in English, Hindi, or Marathi to test appointment booking, symptoms triage, and doctor availability.
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.35fr', gap: 20 }}>
        {/* Left — Call controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Main call card */}
          <div className="card" style={{ textAlign: 'center', padding: '36px 24px' }}>
            {/* Avatar / pulse ring */}
            <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
              {callState === CALL_STATES.AGENT_JOINED && (
                <>
                  <div style={{ position: 'absolute', width: 120, height: 120, borderRadius: '50%', background: 'rgba(34,211,168,0.12)', animation: 'ping 2s cubic-bezier(0,0,0.2,1) infinite' }} />
                  <div style={{ position: 'absolute', width: 95, height: 95, borderRadius: '50%', background: 'rgba(34,211,168,0.2)', animation: 'ping 2s cubic-bezier(0,0,0.2,1) infinite 0.5s' }} />
                </>
              )}
              <div style={{
                width: 76, height: 76, borderRadius: '50%',
                background: callState === CALL_STATES.AGENT_JOINED
                  ? 'linear-gradient(135deg, #22d3a8, #3d7bfd)'
                  : 'var(--bg-dark)',
                color: '#fff',
                border: `3px solid ${callState === CALL_STATES.AGENT_JOINED ? '#22d3a8' : 'var(--border)'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: callState === CALL_STATES.AGENT_JOINED ? '0 8px 30px rgba(34,211,168,0.4)' : 'var(--shadow-md)',
                transition: 'all 0.4s ease', position: 'relative', zIndex: 1,
              }}>
                <Radio size={30} />
              </div>
            </div>

            <div style={{ fontWeight: 800, fontSize: 19, color: 'var(--text-1)', marginBottom: 4 }}>Viora Receptionist</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: STATE_LABELS[callState].color, marginBottom: 24 }}>
              {STATE_LABELS[callState].text}
            </div>

            {/* Primary Call Button (Keeping User-Fav Cyan Blue) */}
            {!isActive ? (
              <button
                id="call-viora-btn"
                onClick={callState === CALL_STATES.CONNECTING ? undefined : startCall}
                disabled={callState === CALL_STATES.CONNECTING}
                className="btn-cyan-blue"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 10,
                  padding: '14px 36px', borderRadius: 'var(--r-pill)',
                  fontWeight: 700, fontSize: 15, letterSpacing: '-0.01em',
                  cursor: callState === CALL_STATES.CONNECTING ? 'wait' : 'pointer',
                  opacity: callState === CALL_STATES.CONNECTING ? 0.75 : 1,
                }}
              >
                {callState === CALL_STATES.CONNECTING ? <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <Phone size={18} />}
                {callState === CALL_STATES.ERROR ? 'Retry Call' : callState === CALL_STATES.CONNECTING ? 'Connecting…' : 'Call Viora'}
              </button>
            ) : (
              <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                {/* Mute */}
                <button
                  id="mute-btn"
                  onClick={toggleMute}
                  style={{
                    width: 48, height: 48, borderRadius: '50%',
                    background: isMuted ? 'var(--red-dim)' : '#f3f4f6',
                    border: `1px solid ${isMuted ? 'var(--red)' : 'var(--border)'}`,
                    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'all 0.2s', color: isMuted ? 'var(--red)' : 'var(--text-1)'
                  }}
                >
                  {isMuted ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
                {/* End call */}
                <button
                  id="end-call-btn"
                  onClick={endCall}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    padding: '0 24px', height: 48, borderRadius: 'var(--r-pill)',
                    background: 'var(--red)',
                    border: 'none', cursor: 'pointer',
                    color: '#fff', fontWeight: 700, fontSize: 14,
                    boxShadow: '0 4px 16px rgba(239,68,68,0.3)', transition: 'all 0.2s',
                  }}
                >
                  <PhoneOff size={16} />
                  End Call
                </button>
              </div>
            )}
          </div>

          {/* Error Banner */}
          {error && (
            <div style={{
              background: 'var(--red-dim)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 'var(--r-md)', padding: '12px 16px',
              display: 'flex', gap: 10, fontSize: 12, color: 'var(--red)', alignItems: 'flex-start',
            }}>
              <AlertCircle size={14} style={{ marginTop: 1, flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Agent status checklist */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-1)', marginBottom: 14 }}>Connection Checklist</div>
            {[
              { label: 'FastAPI Backend Running (:8000)', ok: true },
              { label: 'LiveKit Voice Worker Active', ok: callState === CALL_STATES.AGENT_JOINED, pending: isActive && callState !== CALL_STATES.AGENT_JOINED },
              { label: 'Microphone Permission', ok: isActive },
              { label: 'WebRTC Room Channel', ok: isActive || callState === CALL_STATES.ENDED },
            ].map(({ label, ok, pending }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, fontSize: 12.5 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                  background: ok ? 'var(--green)' : pending ? 'var(--amber)' : '#d1d5db',
                  boxShadow: ok ? '0 0 6px rgba(16,185,129,0.5)' : 'none',
                }} />
                <span style={{ color: ok ? 'var(--text-1)' : 'var(--text-3)', fontWeight: ok ? 600 : 400 }}>{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right — Live Transcript */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, paddingBottom: 14, borderBottom: '1px solid var(--border)' }}>
            <MessageSquare size={16} color="var(--text-2)" />
            <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-1)' }}>Real-Time Voice Transcript</span>
            {isActive && (
              <span className="badge badge-green" style={{ marginLeft: 'auto' }}>
                Live Stream
              </span>
            )}
          </div>

          <div style={{
            flex: 1, minHeight: 360, maxHeight: 440, overflowY: 'auto',
            display: 'flex', flexDirection: 'column', gap: 12,
            paddingRight: 4,
          }}>
            {transcript.length === 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, color: 'var(--text-3)', fontSize: 13, gap: 8, paddingTop: 60 }}>
                <MessageSquare size={32} strokeWidth={1.2} />
                <span>Transcript will appear here in real-time as you speak</span>
              </div>
            )}
            {transcript.map((msg, i) => (
              <div key={i} style={{
                display: 'flex',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                alignItems: 'flex-end', gap: 10,
              }}>
                {msg.role === 'system' ? (
                  <div style={{
                    width: '100%', textAlign: 'center', fontSize: 11,
                    color: 'var(--text-3)', padding: '4px 0', fontFamily: 'var(--font-mono)'
                  }}>
                    — {msg.text} —
                  </div>
                ) : (
                  <>
                    <div style={{
                      width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
                      background: msg.role === 'user' ? 'var(--bg-dark)' : 'var(--blue-dim)',
                      color: msg.role === 'user' ? '#fff' : 'var(--blue)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 10, fontWeight: 800,
                    }}>
                      {msg.role === 'user' ? 'YOU' : 'AI'}
                    </div>
                    <div style={{
                      maxWidth: '78%',
                      background: msg.role === 'user' ? 'var(--bg-dark)' : '#f9fafb',
                      color: msg.role === 'user' ? '#fff' : 'var(--text-1)',
                      border: `1px solid ${msg.role === 'user' ? 'var(--bg-dark)' : 'var(--border)'}`,
                      borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                      padding: '11px 15px', fontSize: 13, lineHeight: 1.5,
                      boxShadow: 'var(--shadow-sm)'
                    }}>
                      {msg.text}
                      <div style={{ fontSize: 10, color: msg.role === 'user' ? '#9ca3af' : 'var(--text-3)', marginTop: 4, textAlign: 'right' }}>
                        {msg.ts}
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}
            <div ref={transcriptEndRef} />
          </div>
        </div>
      </div>

      <style>{`
        @keyframes ping {
          75%, 100% { transform: scale(1.4); opacity: 0; }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

