import React from 'react'

const OUTCOME = {
  resolved:  { cls: 'badge-green',  dot: 'var(--green)',  label: 'Resolved'  },
  escalated: { cls: 'badge-red',    dot: 'var(--red)',    label: 'Escalated' },
  abandoned: { cls: 'badge-amber',  dot: 'var(--amber)',  label: 'Abandoned' },
  failed:    { cls: 'badge-gray',   dot: 'var(--text-3)', label: 'Failed'    },
  in_progress:{ cls: 'badge-blue',  dot: 'var(--blue)',   label: 'Active'    },
}

const LANG = {
  'en-IN': { cls: 'badge-blue',   label: 'EN' },
  'hi-IN': { cls: 'badge-amber',  label: 'HI' },
  'mr-IN': { cls: 'badge-purple', label: 'MR' },
}

export default function StatusBadge({ type, value }) {
  if (type === 'outcome') {
    const s = OUTCOME[value] || { cls: 'badge-gray', dot: 'var(--text-3)', label: value }
    return (
      <span className={`badge ${s.cls}`}>
        <span className="badge-dot" style={{ background: s.dot }} />
        {s.label}
      </span>
    )
  }
  if (type === 'language') {
    const s = LANG[value] || { cls: 'badge-gray', label: value || '—' }
    return <span className={`badge ${s.cls}`}>{s.label}</span>
  }
  return <span className="badge badge-gray">{value || '—'}</span>
}
