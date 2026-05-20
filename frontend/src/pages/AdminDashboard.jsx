// pages/AdminDashboard.jsx — Admin: view contests, create new one
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiAdminContests, apiAdminCreateContest } from '../api'
import { useAuth } from '../AuthContext'
import Navbar from '../components/Navbar'

export default function AdminDashboard() {
    const [contests, setContests] = useState([])
    const [loading, setLoading] = useState(true)
    const [showForm, setShowForm] = useState(false)
    const [form, setForm] = useState({ title: '', description: '', start_time: '', end_time: '' })
    const [saving, setSaving] = useState(false)
    const [err, setErr] = useState('')
    const { user } = useAuth()
    const navigate = useNavigate()

    // Redirect if not admin
    useEffect(() => { if (user && user.role !== 'admin') navigate('/') }, [user])

    const load = () => {
        apiAdminContests().then(setContests).catch(e => setErr(e.message)).finally(() => setLoading(false))
    }
    useEffect(load, [])

    const set = k => e => setForm(p => ({ ...p, [k]: e.target.value }))

    async function handleCreate(e) {
        e.preventDefault(); setErr(''); setSaving(true)
        try {
            await apiAdminCreateContest({
                title: form.title, description: form.description,
                start_time: new Date(form.start_time).toISOString(),
                end_time: new Date(form.end_time).toISOString(),
            })
            setShowForm(false)
            setForm({ title: '', description: '', start_time: '', end_time: '' })
            load()
        } catch (e) { setErr(e.message) } finally { setSaving(false) }
    }

    const STATUS_COLOR = { scheduled: '#fbbf24', live: '#4ade80', ended: '#4a5468' }

    return (
        <div className="page">
            <Navbar />
            <div className="admin-wrap">
                <div className="admin-header">
                    <h1>Admin Dashboard</h1>
                    <button className="btn-primary sm" onClick={() => setShowForm(p => !p)}>
                        {showForm ? '✕ Cancel' : '+ New Contest'}
                    </button>
                </div>

                {/* Create contest form */}
                {showForm && (
                    <form onSubmit={handleCreate} className="admin-form">
                        <h3>New Contest</h3>
                        <div className="form-row">
                            <label>Title <input value={form.title} onChange={set('title')} required /></label>
                            <label>Description <input value={form.description} onChange={set('description')} /></label>
                        </div>
                        <div className="form-row">
                            <label>Start Time <input type="datetime-local" value={form.start_time} onChange={set('start_time')} required /></label>
                            <label>End Time   <input type="datetime-local" value={form.end_time} onChange={set('end_time')} required /></label>
                        </div>
                        {err && <div className="auth-err">{err}</div>}
                        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Creating…' : 'Create Contest'}</button>
                    </form>
                )}

                {loading && <div className="page-loading"><div className="spinner lg-spinner" /></div>}

                <div className="contest-grid">
                    {contests.map(c => (
                        <div key={c.id} className="contest-card admin-card">
                            <div className="cc-top">
                                <span className="badge" style={{ background: STATUS_COLOR[c.status] + '22', color: STATUS_COLOR[c.status], border: `1px solid ${STATUS_COLOR[c.status]}44` }}>
                                    {c.status.toUpperCase()}
                                </span>
                                <span className="cc-problems">{c.problem_count} problems</span>
                            </div>
                            <h2 className="cc-title">{c.title}</h2>
                            <div className="cc-times">
                                <span>{new Date(c.start_time).toLocaleString()} → {new Date(c.end_time).toLocaleString()}</span>
                            </div>
                            <div className="cc-actions">
                                <Link to={`/admin/contest/${c.id}`} className="btn-primary sm">Manage →</Link>
                                <Link to={`/contest/${c.id}/leaderboard`} className="btn-ghost sm">Leaderboard</Link>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
