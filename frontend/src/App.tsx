import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import Dashboard from './pages/Dashboard'
import VideoUpload from './pages/VideoUpload'
import RealTimeMonitoring from './pages/RealTimeMonitoring'
import Results from './pages/Results'
import Sessions from './pages/Sessions'
import Comparison from './pages/Comparison'
import Settings from './pages/Settings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/upload" element={<VideoUpload />} />
        <Route path="/monitoring" element={<RealTimeMonitoring />} />
        <Route path="/results/:sessionId?" element={<Results />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/comparison" element={<Comparison />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}

export default App

