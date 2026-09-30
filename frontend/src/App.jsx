import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom'
import { isLoggedIn, clearToken } from './api/client'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Documents from './pages/Documents.jsx'
import Chat from './pages/Chat.jsx'

function ProtectedRoute({ children }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />
}

function NavBar() {
  const navigate = useNavigate()
  const logout = () => {
    clearToken()
    navigate('/login')
  }
  if (!isLoggedIn()) return null
  return (
    <nav className="flex items-center justify-between px-6 py-3 bg-slate-900 text-white">
      <div className="flex items-center gap-6">
        <span className="font-semibold text-lg">ResearchMind</span>
        <Link to="/chat" className="text-sm text-slate-300 hover:text-white">Chat</Link>
        <Link to="/documents" className="text-sm text-slate-300 hover:text-white">Documents</Link>
      </div>
      <button onClick={logout} className="text-sm bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded">
        Logout
      </button>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/documents" element={<ProtectedRoute><Documents /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
        <Route path="/" element={<Navigate to={isLoggedIn() ? '/chat' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}
