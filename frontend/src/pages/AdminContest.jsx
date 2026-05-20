// pages/AdminContest.jsx — Manage a contest: generate problems via LLM
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { apiAdminContests, apiAdminGenerateProblem, apiAdminDeleteProblem, apiProblems, apiAdminUpdateTestcases } from '../api'
import Navbar from '../components/Navbar'

const TOPICS = [
    'Arrays', 'Strings', 'Linked Lists', 'Trees', 'Graphs',
    'Dynamic Programming', 'Greedy', 'Binary Search', 'Sorting',
    'Recursion', 'Math', 'Bit Manipulation', 'Hashing', 'Two Pointers',
    'Stack & Queue', 'Backtracking',
]

const DIFFICULTIES = ['easy', 'medium', 'hard']

const DIFF_COLORS = { easy: 'var(--green)', medium: 'var(--yellow)', hard: 'var(--red)' }

export default function AdminContest() {
    const { contestId } = useParams()
    const [problems, setProblems] = useState([])
    const [contest, setContest] = useState(null)
    const [loading, setLoading] = useState(true)
    const [generating, setGenerating] = useState(false)
    const [genForm, setGenForm] = useState({ topic: 'Arrays', difficulty: 'easy' })
    const [genErr, setGenErr] = useState('')
    const [preview, setPreview] = useState(null)
    const [editingTestcases, setEditingTestcases] = useState(null)
    const [testcases, setTestcases] = useState([])
    const [savingTestcases, setSavingTestcases] = useState(false)
    const [tcErr, setTcErr] = useState('')

    const setF = k => e => setGenForm(p => ({ ...p, [k]: e.target.value }))

    const load = async () => {
        try {
            const [ps, cs] = await Promise.all([apiProblems(contestId), apiAdminContests()])
            setProblems(ps)
            setContest(cs.find(c => c.id === parseInt(contestId)))
        } catch { }
        setLoading(false)
    }
    useEffect(() => { load() }, [contestId])

    async function handleGenerate(e) {
        e.preventDefault(); setGenErr(''); setGenerating(true); setPreview(null)
        try {
            const p = await apiAdminGenerateProblem(contestId, genForm)
            setPreview(p)
            setProblems(prev => [...prev, p])
        } catch (e) { setGenErr(e.message) } finally { setGenerating(false) }
    }

    async function handleDelete(pid) {
        if (!confirm('Delete this problem?')) return
        await apiAdminDeleteProblem(contestId, pid)
        setProblems(prev => prev.filter(p => p.id !== pid))
    }

    function openTestcaseEditor(problem) {
        setEditingTestcases(problem.id)
        const parsed = JSON.parse(problem.test_cases || '[]')
        setTestcases(parsed && Array.isArray(parsed) ? parsed : [])
        setTcErr('')
    }

    async function handleSaveTestcases() {
        if (!editingTestcases) return
        if (testcases.length === 0) {
            setTcErr('At least one test case is required')
            return
        }
        // Validate all testcases have input and expected_output
        if (testcases.some(tc => !tc.input || !tc.expected_output)) {
            setTcErr('All test cases must have input and expected output')
            return
        }
        setSavingTestcases(true)
        try {
            await apiAdminUpdateTestcases(contestId, editingTestcases, { test_cases: testcases })
            // Update problems list
            setProblems(prev => prev.map(p => {
                if (p.id === editingTestcases) {
                    return { ...p, test_cases: JSON.stringify(testcases) }
                }
                return p
            }))
            setEditingTestcases(null)
            setTestcases([])
        } catch (e) {
            setTcErr(e.message)
        } finally {
            setSavingTestcases(false)
        }
    }

    function handleUpdateTestcase(index, field, value) {
        setTestcases(prev => {
            const updated = [...prev]
            updated[index] = { ...updated[index], [field]: value }
            return updated
        })
    }

    function handleAddTestcase() {
        setTestcases(prev => [...prev, { input: '', expected_output: '' }])
    }

    function handleRemoveTestcase(index) {
        setTestcases(prev => prev.filter((_, i) => i !== index))
    }

    return (
        <div className="page">
            <Navbar />
            <div className="admin-wrap">
                <div className="admin-header">
                    <div>
                        <Link to="/admin" className="back-link">← Dashboard</Link>
                        <h1>{contest?.title || 'Contest Management'}</h1>
                        <p className="muted-text" style={{ marginTop: 4 }}>
                            {contest && `${new Date(contest.start_time).toLocaleString()} → ${new Date(contest.end_time).toLocaleString()}`}
                        </p>
                    </div>
                    <Link to={`/contest/${contestId}/leaderboard`} className="btn-ghost sm">View Leaderboard</Link>
                </div>

                {/* LLM generator */}
                <div className="admin-form">
                    <h3>🤖 Generate Problem with AI</h3>
                    <form onSubmit={handleGenerate}>
                        <div className="form-row">
                            <label>Topic
                                <select value={genForm.topic} onChange={setF('topic')}>
                                    {TOPICS.map(t => <option key={t}>{t}</option>)}
                                </select>
                            </label>
                            <label>Difficulty
                                <select value={genForm.difficulty} onChange={setF('difficulty')}>
                                    {DIFFICULTIES.map(d => <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>)}
                                </select>
                            </label>
                            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                                <button type="submit" className="btn-primary" disabled={generating} style={{ height: 40 }}>
                                    {generating ? <><span className="spinner" />Generating…</> : '✨ Generate'}
                                </button>
                            </div>
                        </div>
                        {generating && (
                            <div className="gen-loading">
                                <div className="spinner lg-spinner" />
                                <span>Asking Gemini to create a {genForm.difficulty} {genForm.topic} problem…</span>
                            </div>
                        )}
                        {genErr && <div className="auth-err">{genErr}</div>}
                    </form>

                    {/* Preview last generated */}
                    {preview && (
                        <div className="problem-preview">
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                                <span style={{ fontWeight: 700, fontSize: 15 }}>{preview.title}</span>
                                <span style={{ color: DIFF_COLORS[preview.difficulty], fontSize: 12, textTransform: 'capitalize' }}>
                                    {preview.difficulty}
                                </span>
                                <span className="badge badge-live" style={{ fontSize: 11 }}>✓ Added to contest</span>
                            </div>
                            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                {preview.description?.slice(0, 300)}…
                            </p>
                            <div style={{ marginTop: 8, display: 'flex', gap: 10 }}>
                                <span className="time-badge">📋 {JSON.parse(preview.test_cases || '[]').length} test cases</span>
                                <span className="time-badge">🏅 {preview.base_score} pts</span>
                                <span className="time-badge">⏱ {preview.time_limit_ms}ms</span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Problems list */}
                <div className="problems-section">
                    <h3>Problems ({problems.length})</h3>
                    {loading && <div className="page-loading"><div className="spinner lg-spinner" /></div>}
                    {!loading && problems.length === 0 && (
                        <div className="empty-state">No problems yet. Use the generator above!</div>
                    )}
                    {problems.map((p, i) => (
                        <div key={p.id} className="problem-row">
                            <div className="pr-left">
                                <span className="pr-letter">{String.fromCharCode(65 + i)}</span>
                                <div>
                                    <div className="pr-title">{p.title}</div>
                                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                                        <span style={{ color: DIFF_COLORS[p.difficulty], fontSize: 11, textTransform: 'capitalize' }}>{p.difficulty}</span>
                                        <span className="muted-text" style={{ fontSize: 11 }}>{p.topic}</span>
                                        <span className="time-badge">{JSON.parse(p.test_cases || '[]').length} test cases</span>
                                    </div>
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                <span className="time-badge">🏅 {p.base_score} pts</span>
                                <button className="btn-ghost sm" onClick={() => openTestcaseEditor(p)}>✏️ Test Cases</button>
                                <button className="tc-remove" onClick={() => handleDelete(p.id)}>✕ Remove</button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Testcase Editor Modal */}
                {editingTestcases && (
                    <div style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        zIndex: 1000
                    }}>
                        <div style={{
                            background: 'var(--bg-surface)', borderRadius: 8, padding: 24, maxWidth: 700, width: '90%',
                            maxHeight: '90vh', overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h3>Edit Test Cases</h3>
                                <button onClick={() => setEditingTestcases(null)} style={{
                                    background: 'transparent', border: 'none', color: 'var(--text-secondary)',
                                    fontSize: 24, cursor: 'pointer'
                                }}>✕</button>
                            </div>

                            {tcErr && <div className="auth-err" style={{ marginBottom: 16 }}>{tcErr}</div>}

                            <div style={{ marginBottom: 16, maxHeight: 400, overflowY: 'auto' }}>
                                {testcases.map((tc, idx) => (
                                    <div key={idx} style={{
                                        display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12,
                                        marginBottom: 12, padding: 12, background: 'var(--bg-editor)',
                                        borderRadius: 4, border: '1px solid var(--border)'
                                    }}>
                                        <div>
                                            <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                                                Input
                                            </label>
                                            <textarea value={tc.input} onChange={e => handleUpdateTestcase(idx, 'input', e.target.value)}
                                                style={{
                                                    width: '100%', padding: 8, background: 'var(--bg-panel)', border: '1px solid var(--border)',
                                                    borderRadius: 4, color: 'var(--text-primary)', fontFamily: 'monospace', fontSize: 12,
                                                    minHeight: 60
                                                }} />
                                        </div>
                                        <div>
                                            <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                                                Expected Output
                                            </label>
                                            <textarea value={tc.expected_output} onChange={e => handleUpdateTestcase(idx, 'expected_output', e.target.value)}
                                                style={{
                                                    width: '100%', padding: 8, background: 'var(--bg-panel)', border: '1px solid var(--border)',
                                                    borderRadius: 4, color: 'var(--text-primary)', fontFamily: 'monospace', fontSize: 12,
                                                    minHeight: 60
                                                }} />
                                        </div>
                                        <button onClick={() => handleRemoveTestcase(idx)}
                                            style={{
                                                background: 'transparent', border: 'none', color: 'var(--red)', cursor: 'pointer',
                                                fontSize: 18, alignSelf: 'start', padding: '4px 8px'
                                            }}>✕</button>
                                    </div>
                                ))}
                            </div>

                            <button onClick={handleAddTestcase}
                                style={{
                                    width: '100%', padding: '10px 16px', background: 'transparent',
                                    border: '1px dashed var(--accent)', borderRadius: 4, color: 'var(--accent)',
                                    cursor: 'pointer', marginBottom: 16, fontWeight: 500
                                }}>
                                + Add Test Case
                            </button>

                            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                                <button onClick={() => setEditingTestcases(null)}
                                    style={{
                                        padding: '10px 20px', background: 'transparent', border: '1px solid var(--border)',
                                        borderRadius: 4, color: 'var(--text-primary)', cursor: 'pointer'
                                    }}>
                                    Cancel
                                </button>
                                <button onClick={handleSaveTestcases} disabled={savingTestcases}
                                    style={{
                                        padding: '10px 20px', background: 'var(--accent)', border: 'none',
                                        borderRadius: 4, color: 'white', cursor: 'pointer', fontWeight: 500,
                                        opacity: savingTestcases ? 0.7 : 1
                                    }}>
                                    {savingTestcases ? '⏳ Saving…' : '✓ Save Test Cases'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
