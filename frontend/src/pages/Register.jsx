import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, setToken } from '../api/client'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.register(email, password, displayName)
      setToken(res.token)
      navigate('/chat')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-md w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-slate-900">Create your account</h1>
        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
        <input
          type="text" placeholder="Display name" value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="w-full mb-3 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
        />
        <input
          type="email" placeholder="Email" value={email} required
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-3 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
        />
        <input
          type="password" placeholder="Password (min 8 chars)" value={password} required minLength={8}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-5 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
        />
        <button
          type="submit" disabled={loading}
          className="w-full bg-slate-900 text-white py-2 rounded-lg hover:bg-slate-800 disabled:opacity-50"
        >
          {loading ? 'Creating account...' : 'Register'}
        </button>
        <p className="text-sm text-slate-500 mt-4 text-center">
          Already have an account? <Link to="/login" className="text-slate-900 font-medium">Sign in</Link>
        </p>
      </form>
    </div>
  )
}
