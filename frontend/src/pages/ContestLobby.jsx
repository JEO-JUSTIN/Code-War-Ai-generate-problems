// pages/ContestLobby.jsx — list of contests for students
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiContests } from '../api'
import { useAuth } from '../AuthContext'
import Navbar from '../components/Navbar'
import CountdownTimer from '../components/CountdownTimer'

const BADGE = {
    scheduled: { cls: 'badge-scheduled', label: '⏰ Upcoming' },
    live: { cls: 'badge-live', label: '🟢 Live' },
    ended: { cls: 'badge-ended', label: '✓ Ended' },
}

export default function ContestLobby() {
    const [contests, setContests] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const { user } = useAuth()
    const navigate = useNavigate()

    useEffect(() => {
        apiContests()
            .then(setContests)
            .catch(e => setError(e.message))
            .finally(() => setLoading(false))
    }, [])

    return (
        <div className="page">
            <Navbar />
            <div className="lobby-wrap">
                <div className="lobby-header">
                    <h1>Contests</h1>
                    {user?.role === 'admin' && (
                        <button className="btn-primary sm" onClick={() => navigate('/admin')}>Admin Panel</button>
                    )}
                </div>

                {loading && <div className="page-loading"><div className="spinner lg-spinner" /></div>}
                {error && <div className="page-error">{error}</div>}

                {!loading && !error && contests.length === 0 && (
                    <div className="empty-state">No contests scheduled yet.</div>
                )}

                <div className="contest-grid">
                    {contests.map(c => {
                        const b = BADGE[c.status] || BADGE.ended
                        return (
                            <div key={c.id} className={`contest-card ${c.status}`}>
                                <div className="cc-top">
                                    <span className={`badge ${b.cls}`}>{b.label}</span>
                                    <span className="cc-problems">{c.problem_count} problem{c.problem_count !== 1 ? 's' : ''}</span>
                                </div>
                                <h2 className="cc-title">{c.title}</h2>
                                {c.description && <p className="cc-desc">{c.description}</p>}
                                <div className="cc-times">
                                    <span>Start: {new Date(c.start_time).toLocaleString()}</span>
                                    <span>End: {new Date(c.end_time).toLocaleString()}</span>
                                </div>
                                {c.status === 'live' && <CountdownTimer target={c.end_time} label="Ends in" />}
                                {c.status === 'scheduled' && <CountdownTimer target={c.start_time} label="Starts in" />}
                                <div className="cc-actions">
                                    {c.status === 'live' && (
                                        <Link to={`/contest/${c.id}`} className="btn-primary sm">Enter Contest →</Link>
                                    )}
                                    <Link to={`/contest/${c.id}/leaderboard`} className="btn-ghost sm">Leaderboard</Link>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}
