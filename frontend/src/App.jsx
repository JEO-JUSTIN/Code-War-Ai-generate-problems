// App.jsx — React Router shell for CodeWar platform
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'

import Login from './pages/Login'
import ContestLobby from './pages/ContestLobby'
import ContestRoom from './pages/ContestRoom'
import Leaderboard from './pages/Leaderboard'
import AdminDashboard from './pages/AdminDashboard'
import AdminContest from './pages/AdminContest'

function ProtectedRoute({ children, adminOnly = false }) {
  const { user, ready } = useAuth()
  if (!ready) return <div className="page-loading"><div className="spinner lg-spinner" /></div>
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.role !== 'admin') return <Navigate to="/" replace />
  return children
}

function AppRoutes() {
  const { user, ready } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={
        ready && user ? <Navigate to={user.role === 'admin' ? '/admin' : '/'} replace /> : <Login />
      } />
      <Route path="/" element={<ContestLobby />} />
      <Route path="/contest/:contestId" element={
        <ProtectedRoute><ContestRoom /></ProtectedRoute>
      } />
      <Route path="/contest/:contestId/leaderboard" element={<Leaderboard />} />
      <Route path="/admin" element={
        <ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>
      } />
      <Route path="/admin/contest/:contestId" element={
        <ProtectedRoute adminOnly><AdminContest /></ProtectedRoute>
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
