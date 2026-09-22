import React, { useState, useEffect } from 'react'
import { fetchConfig, fetchFlags, patchFlag } from '../api/client'
import { Settings2, ShieldCheck, Sliders, Server, MessageSquare, Stethoscope } from 'lucide-react'

const FLAG_META = {
  triage_enabled:               { label: 'Symptom Triage Assessment',   desc: 'Allows callers to describe symptoms for emergency screening.' },
  lab_lookup_enabled:           { label: 'Lab Report Lookup',            desc: 'Enables patients to query real-time lab diagnostic status.' },
  prescription_lookup_enabled:  { label: 'Prescription Status Check',    desc: 'Allows callers to check their active medications.' },
  registration_enabled:         { label: 'New Patient Intake Drafts',    desc: 'Accepts new patient draft registrations into HMS.' },
  faq_enabled:                  { label: 'Clinic FAQ & Information',     desc: 'Answers questions about OPD hours, address, and doctors.' },
  sms_summary_enabled:          { label: 'Automated Post-Call SMS',      desc: 'Dispatches booking confirmations & SMS alerts.' },
}

function Toggle({ on, onChange, saving }) {
  return (
    <button
      className={`toggle${on ? ' on' : ''}`}
      onClick={onChange}
      disabled={saving}
      style={{ opacity: saving ? 0.5 : 1 }}
    >
      <div className="toggle-thumb" />
    </button>
  )
}

function ConfigItem({ label, value }) {
  return (
    <div style={{ background: '#f9fafb', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
      <div style={{ fontSize: 10.5, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 13,
        color: typeof value === 'string' && value.startsWith('✗') ? 'var(--red)'
             : typeof value === 'string' && value.startsWith('✓') ? 'var(--green)'
             : 'var(--text-1)',
        fontWeight: 600,
        marginTop: 4
      }}>
        {value}
      </div>
    </div>
  )
}

export default function Settings() {
  const [config, setConfig] = useState(null)
  const [flags, setFlags] = useState({})
  const [saving, setSaving] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [cfg, fl] = await Promise.all([fetchConfig(), fetchFlags()])
        setConfig(cfg)
        setFlags(fl.flags || {})
      } catch {
        setConfig({
          version: '1.0.0', environment: 'development', hms_provider: 'mock',
          supported_languages: ['en-IN', 'hi-IN', 'mr-IN'],
          stt_model: 'saaras:v2 (Sarvam AI)',
          tts_model: 'bulbul:v2 (Sarvam AI)',
          tts_voice: 'meera (Hindi/English)',
          llm_model: 'llama-3.3-70b-versatile (Groq)',
          audio_retention_days: 7,
          emergency_number: '108',
        })
        setFlags({
          triage_enabled: true,
          lab_lookup_enabled: true,
          prescription_lookup_enabled: true,
          registration_enabled: true,
          faq_enabled: true,
          sms_summary_enabled: true,
        })
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleToggle = async (flag) => {
    const next = !flags[flag]
    setSaving(flag)
    try {
      await patchFlag(flag, next)
      setFlags(f => ({ ...f, [flag]: next }))
    } catch {
      setFlags(f => ({ ...f, [flag]: next }))
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="anim-fade-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 className="page-title">Settings & Configuration</h1>
          <p className="page-sub">Manage Viora reception features, clinical guardrails, and model hyperparameters</p>
        </div>
        <span className="badge badge-dark">Production Config</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20 }}>
        {/* Left — Feature Flags */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid var(--border)' }}>
            <Sliders size={16} color="var(--blue)" />
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>Clinical Feature Switches</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {Object.entries(FLAG_META).map(([flag, meta], i) => (
              <div
                key={flag}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '14px 0', borderBottom: i < Object.keys(FLAG_META).length - 1 ? '1px solid var(--border-light)' : 'none'
                }}
              >
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-1)' }}>{meta.label}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-3)', marginTop: 2 }}>{meta.desc}</div>
                </div>
                <Toggle
                  on={!!flags[flag]}
                  onChange={() => handleToggle(flag)}
                  saving={saving === flag}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Right — Model Parameters */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid var(--border)' }}>
            <Server size={16} color="var(--green)" />
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>AI & Telephony Pipeline</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <ConfigItem label="LLM Reasoning Engine" value={config?.llm_model ?? 'Llama 3.3 70B (Groq)'} />
            <ConfigItem label="Speech-to-Text Model" value={config?.stt_model ?? 'Sarvam saaras:v2'} />
            <ConfigItem label="Text-to-Speech Model" value={config?.tts_model ?? 'Sarvam bulbul:v2'} />
            <ConfigItem label="TTS Voice Character" value={config?.tts_voice ?? 'meera (warm receptionist)'} />
            <ConfigItem label="Emergency Ambulance Escalation" value="Dial 108 Advisory & Instant Transfer" />
            <ConfigItem label="Supported Languages" value="English, Hindi, Marathi (Code-Switching)" />
          </div>
        </div>
      </div>
    </div>
  )
}

