import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import Dashboard from './pages/Dashboard'
import VideoUpload from './pages/VideoUpload'
import RealTimeMonitoring from './pages/RealTimeMonitoring'
import LocalMode from './pages/LocalMode'
import Results from './pages/Results'
import Sessions from './pages/Sessions'
import Comparison from './pages/Comparison'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Register from './pages/Register'
import Candidates from './pages/Candidates'
import Barem from './pages/Barem'

// Protected Route component
const ProtectedRoute = ({ children }: { children: React.ReactElement }) => {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/upload" element={<VideoUpload />} />
                <Route path="/monitoring" element={<RealTimeMonitoring />} />
                <Route path="/local-mode" element={<LocalMode />} />
                <Route path="/results/:sessionId?" element={<Results />} />
                <Route path="/sessions" element={<Sessions />} />
                <Route path="/comparison" element={<Comparison />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/candidates" element={<Candidates />} />
                <Route path="/barem" element={<Barem />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App

