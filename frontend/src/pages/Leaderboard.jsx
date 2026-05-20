// pages/Leaderboard.jsx — Per-contest leaderboard with auto-refresh
import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { apiLeaderboard, apiContest } from '../api'
import Navbar from '../components/Navbar'
import CountdownTimer from '../components/CountdownTimer'

export default function Leaderboard() {
    const { contestId } = useParams()
    const [entries, setEntries] = useState([])
    const [contest, setContest] = useState(null)
    const [loading, setLoading] = useState(true)
    const [lastRefresh, setLastRefresh] = useState(null)

    const load = useCallback(async () => {
        try {
            const [lb, ct] = await Promise.all([apiLeaderboard(contestId), apiContest(contestId)])
            setEntries(lb)
            setContest(ct)
            setLastRefresh(new Date())
        } catch { }
        setLoading(false)
    }, [contestId])

    useEffect(() => {
        load()
        const iv = setInterval(load, 15000)  // refresh every 15s
        return () => clearInterval(iv)
    }, [load])

    const medalEmoji = (rank) => rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : rank

    return (
        <div className="page">
            <Navbar />
            <div className="lb-wrap">
                <div className="lb-header">
                    <div>
                        <Link to="/" className="back-link">← Contests</Link>
                        <h1>{contest?.title || 'Leaderboard'}</h1>
                        {contest?.status === 'live' && (
                            <CountdownTimer target={contest.end_time} label="Ends in" />
                        )}
                    </div>
                    <div className="lb-meta">
                        {lastRefresh && <span className="muted-text">Updated {lastRefresh.toLocaleTimeString()}</span>}
                        <span className="badge badge-live" style={{ fontSize: 11 }}>Auto‑refresh 15s</span>
                    </div>
                </div>

                {loading && <div className="page-loading"><div className="spinner lg-spinner" /></div>}

                {!loading && entries.length === 0 && (
                    <div className="empty-state">No submissions yet. Be the first! 🚀</div>
                )}

                {entries.length > 0 && (
                    <div className="lb-table-wrap">
                        <table className="lb-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Participant</th>
                                    <th>Score</th>
                                    <th>Passed</th>
                                    <th>Last Submission</th>
                                </tr>
                            </thead>
                            <tbody>
                                {entries.map((e) => (
                                    <tr key={e.rank} className={e.rank <= 3 ? 'top-rank' : ''}>
                                        <td className="rank-cell">{medalEmoji(e.rank)}</td>
                                        <td className="username-cell">{e.username}</td>
                                        <td className="score-cell">{e.score}</td>
                                        <td className="cases-cell">{e.passed}/{e.total}</td>
                                        <td className="time-cell">{new Date(e.submitted_at).toLocaleTimeString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}
