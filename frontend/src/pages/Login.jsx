// pages/Login.jsx — Login & Register page
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiLogin, apiRegister } from '../api'
import { useAuth } from '../AuthContext'

export default function Login() {
    const [tab, setTab] = useState('login')
    const [form, setForm] = useState({ username: '', email: '', password: '' })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const { login } = useAuth()
    const navigate = useNavigate()

    const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }))

    async function handleSubmit(e) {
        e.preventDefault()
        setError(''); setLoading(true)
        try {
            if (tab === 'login') {
                const data = await apiLogin(form.username, form.password)
                login(data.access_token, { id: data.user_id, username: data.username, role: data.role })
                navigate(data.role === 'admin' ? '/admin' : '/')
            } else {
                await apiRegister({ username: form.username, email: form.email, password: form.password })
                setTab('login'); setError('Registered! Please log in.')
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-logo">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                        <defs><linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#6c63ff" /><stop offset="100%" stopColor="#a78bfa" />
                        </linearGradient></defs>
                        <path d="M8 6L3 12L8 18" stroke="url(#g2)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M16 6L21 12L16 18" stroke="url(#g2)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M13 4L11 20" stroke="url(#g2)" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    <span>CodeWar</span>
                </div>
                <p className="auth-sub">Intra-department coding contest</p>

                <div className="auth-tabs">
                    <button className={tab === 'login' ? 'active' : ''} onClick={() => setTab('login')}>Login</button>
                    <button className={tab === 'register' ? 'active' : ''} onClick={() => setTab('register')}>Register</button>
                </div>

                <form onSubmit={handleSubmit} className="auth-form">
                    <label>Username
                        <input value={form.username} onChange={set('username')} required autoFocus />
                    </label>
                    {tab === 'register' && (
                        <label>Email
                            <input type="email" value={form.email} onChange={set('email')} required />
                        </label>
                    )}
                    <label>Password
                        <input type="password" value={form.password} onChange={set('password')} required />
                    </label>
                    {error && <div className={`auth-err ${error.startsWith('Registered') ? 'auth-ok' : ''}`}>{error}</div>}
                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? 'Please wait…' : tab === 'login' ? 'Sign In' : 'Create Account'}
                    </button>
                </form>
            </div>
        </div>
    )
}
