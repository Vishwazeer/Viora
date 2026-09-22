import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import LiveMonitor from './pages/LiveMonitor'
import CallLog from './pages/CallLog'
import TranscriptViewer from './pages/TranscriptViewer'
import EscalationQueue from './pages/EscalationQueue'
import SystemHealth from './pages/SystemHealth'
import Settings from './pages/Settings'
import Simulator from './pages/Simulator'
import Appointments from './pages/Appointments'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/monitor" replace />} />
          <Route path="monitor"     element={<LiveMonitor />} />
          <Route path="calls"       element={<CallLog />} />
          <Route path="calls/:id"   element={<TranscriptViewer />} />
          <Route path="escalations" element={<EscalationQueue />} />
          <Route path="appointments"element={<Appointments />} />
          <Route path="health"      element={<SystemHealth />} />
          <Route path="settings"    element={<Settings />} />
          <Route path="simulator"   element={<Simulator />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
