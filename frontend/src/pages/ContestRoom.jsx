// pages/ContestRoom.jsx — Problem view + code editor + submit
import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
import { indentOnInput, bracketMatching } from '@codemirror/language'
import { closeBrackets } from '@codemirror/autocomplete'
import { oneDark } from '@codemirror/theme-one-dark'
import { python } from '@codemirror/lang-python'
import { cpp } from '@codemirror/lang-cpp'
import { java } from '@codemirror/lang-java'

import { apiProblems, apiSubmit, apiMySubmissions, apiExecute } from '../api'
import Navbar from '../components/Navbar'
import CountdownTimer from '../components/CountdownTimer'

const LANGS = {
    python: { label: 'Python', color: '#3b82f6', ext: () => python() },
    c: { label: 'C', color: '#a78bfa', ext: () => cpp() },
    java: { label: 'Java', color: '#f97316', ext: () => java() },
}

const WRAP = {
    python: (code, driver) => `${code}\n\n${driver}`,
    c: (code, driver) => `#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n\n${code}\n\n${driver}`,
    java: (code, driver) => {
        const ind = "\n    " + code.trim().replace(/\n/g, "\n    ")
        return `import java.util.Scanner;\npublic class Main {\n    ${ind.trim()}\n\n    ${driver}\n}`
    },
}

const VERDICT_CLASS = {
    'Accepted': 'v-ac',
    'Wrong Answer': 'v-wa',
    'Compilation Error': 'v-ce',
    'Runtime Error': 'v-re',
    'Time Limit Exceeded': 'v-tle',
}

function CodeEditor({ language, value, onChange }) {
    const elRef = useRef(null)
    const viewRef = useRef(null)
    const cbRef = useRef(onChange); cbRef.current = onChange

    useEffect(() => {
        if (!elRef.current) return
        const ext = LANGS[language]?.ext() || python()
        const view = new EditorView({
            state: EditorState.create({
                doc: value,
                extensions: [
                    lineNumbers(), highlightActiveLine(), highlightActiveLineGutter(),
                    history(), indentOnInput(), bracketMatching(), closeBrackets(),
                    keymap.of([...defaultKeymap, ...historyKeymap]),
                    oneDark, ext,
                    EditorView.updateListener.of(u => { if (u.docChanged) cbRef.current(u.state.doc.toString()) }),
                    EditorView.theme({
                        '&': { height: '100%', background: 'var(--bg-editor)' },
                        '.cm-scroller': { overflow: 'auto' },
                        '.cm-content': { padding: '12px 0' },
                        '.cm-line': { padding: '0 16px' },
                        '.cm-gutters': { background: '#0a0c10', borderRight: '1px solid #1e2230' },
                        '.cm-lineNumbers .cm-gutterElement': { padding: '0 8px 0 4px', color: '#3a4058' },
                        '.cm-activeLineGutter': { background: '#13161d' },
                    }),
                    EditorView.lineWrapping,
                ],
            }),
            parent: elRef.current,
        })
        viewRef.current = view
        return () => { view.destroy(); viewRef.current = null }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [language])

    useEffect(() => {
        const v = viewRef.current; if (!v) return
        const cur = v.state.doc.toString()
        if (cur !== value) v.dispatch({ changes: { from: 0, to: cur.length, insert: value } })
    }, [value])

    return <div ref={elRef} className="cm-shell" />
}

export default function ContestRoom() {
    const { contestId } = useParams()
    const navigate = useNavigate()

    const [problems, setProblems] = useState([])
    const [activePid, setActivePid] = useState(null)
    const [language, setLanguage] = useState('python')
    const [codes, setCodes] = useState(() => {
        try {
            const saved = localStorage.getItem(`contest_codes_${contestId}`)
            return saved ? JSON.parse(saved) : {}
        } catch {
            return {}
        }
    })
    const [submitting, setSubmitting] = useState(false)
    const [result, setResult] = useState(null)
    const [running, setRunning] = useState(false)
    const [runResult, setRunResult] = useState(null)
    const [history_, setHistory] = useState([])
    const [loadErr, setLoadErr] = useState('')
    const [contest, setContest] = useState(null)
    const [activeTab, setActiveTab] = useState('problem')  // 'problem' | 'result' | 'history'

    // Save codes to localStorage whenever they change
    useEffect(() => {
        localStorage.setItem(`contest_codes_${contestId}`, JSON.stringify(codes))
    }, [codes, contestId])

    useEffect(() => {
        apiProblems(contestId).then(ps => {
            setProblems(ps)
            if (ps.length) setActivePid(ps[0].id)
        }).catch(e => setLoadErr(e.message))
    }, [contestId])

    const activeProblem = problems.find(p => p.id === activePid)

    // Default stub when switching problems/languages
    useEffect(() => {
        if (!activeProblem) return
        const key = `${activePid}_${language}`
        if (!codes[key]) {
            const stub = language === 'python' ? activeProblem.func_sig_py
                : language === 'c' ? activeProblem.func_sig_c
                    : activeProblem.func_sig_java
            setCodes(p => ({ ...p, [key]: stub || '' }))
        }
    }, [activePid, language, activeProblem])

    const userCode = codes[`${activePid}_${language}`] || ''
    const setUserCode = (v) => setCodes(p => ({ ...p, [`${activePid}_${language}`]: v }))

    async function loadHistory() {
        if (!activePid) return
        try {
            const subs = await apiMySubmissions(contestId, activePid)
            setHistory(subs)
        } catch { }
    }

    async function handleRun() {
        if (!activeProblem || running || submitting) return
        setRunning(true); setRunResult(null)

        const driver = language === 'python' ? activeProblem.driver_py
            : language === 'c' ? activeProblem.driver_c
                : activeProblem.driver_java

        // User only writes the function — we wrap it here
        const fullCode = WRAP[language]?.(userCode, driver) || userCode

        // Default: take the first example input if there is any, else "1"
        const exs = (() => { try { return JSON.parse(activeProblem?.examples || '[]') } catch { return [] } })()
        const stdin = exs.length > 0 ? exs[0].input : "1"

        try {
            const res = await apiExecute({
                language,
                code: fullCode,
                stdin
            })
            setRunResult({ ...res, _input: stdin, _expected: exs[0]?.output })
            setActiveTab('run_result')
        } catch (e) {
            setRunResult({ error: e.message })
            setActiveTab('run_result')
        } finally {
            setRunning(false)
        }
    }

    async function handleSubmit() {
        if (!activeProblem || submitting) return
        setSubmitting(true); setResult(null)

        try {
            const sub = await apiSubmit(contestId, {
                problem_id: activeProblem.id,
                language,
                code: userCode,
            })
            setResult(sub)
            setActiveTab('result')
            loadHistory()
        } catch (e) {
            setResult({ error: e.message })
        } finally {
            setSubmitting(false)
        }
    }

    useEffect(() => {
        if (activeTab === 'history') loadHistory()
    }, [activeTab])

    const examples = (() => { try { return JSON.parse(activeProblem?.examples || '[]') } catch { return [] } })()

    if (loadErr) return (
        <div className="page"><Navbar />
            <div className="page-error">{loadErr}<br /><Link to="/">← Back to contests</Link></div>
        </div>
    )

    return (
        <div className="app-shell">
            <header className="topbar">
                <Link to="/" className="topbar-logo" style={{ textDecoration: 'none' }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <defs><linearGradient id="gn" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#6c63ff" /><stop offset="100%" stopColor="#a78bfa" />
                        </linearGradient></defs>
                        <path d="M8 6L3 12L8 18" stroke="url(#gn)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M16 6L21 12L16 18" stroke="url(#gn)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        <path d="M13 4L11 20" stroke="url(#gn)" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    CodeWar
                </Link>
                <div className="topbar-divider" />

                {/* Problem selector */}
                <div className="tc-tabs" style={{ maxWidth: 400, padding: '0 4px' }}>
                    {problems.map((p, i) => (
                        <button key={p.id} className={`tc-tab ${activePid === p.id ? 'active' : ''}`}
                            onClick={() => setActivePid(p.id)} style={{ whiteSpace: 'nowrap' }}>
                            {String.fromCharCode(65 + i)}. {p.title}
                        </button>
                    ))}
                </div>

                <div className="topbar-spacer" />
                <Link to={`/contest/${contestId}/leaderboard`} className="ghost-btn" style={{ textDecoration: 'none' }}>🏆 Leaderboard</Link>
                <kbd className="hint-key">Ctrl+Enter</kbd>
                <button className="run-btn" onClick={handleRun} disabled={running || submitting || !activeProblem} style={{ background: '#4b5563', marginRight: 8 }}>
                    {running ? <><span className="spinner" />Running…</> : <>▶ Run (Examples)</>}
                </button>
                <button className="run-btn" onClick={handleSubmit} disabled={running || submitting || !activeProblem}>
                    {submitting ? <><span className="spinner" />Judging…</> : <>☁ Submit</>}
                </button>
            </header>

            <div className="main-body">
                {/* Left: problem statement */}
                <div className="editor-pane" style={{ flex: '0 0 42%', background: 'var(--bg-panel)' }}>
                    <div className="pane-header">
                        <span style={{ fontWeight: 600, fontSize: 13 }}>
                            {activeProblem ? `${activeProblem.title}` : 'Loading…'}
                        </span>
                        {activeProblem && (
                            <span className={`verdict verdict-${activeProblem.difficulty}`} style={{ textTransform: 'capitalize', marginLeft: 8 }}>
                                {activeProblem.difficulty}
                            </span>
                        )}
                    </div>
                    <div className="output-content" style={{ fontFamily: 'var(--font-sans)', fontSize: 13.5, lineHeight: 1.75 }}>
                        {activeProblem ? (
                            <div className="problem-statement">
                                <p style={{ whiteSpace: 'pre-wrap' }}>{activeProblem.description}</p>
                                {activeProblem.constraints && (
                                    <div className="prob-section">
                                        <h4>Constraints</h4>
                                        <p style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }}>{activeProblem.constraints}</p>
                                    </div>
                                )}
                                {examples.length > 0 && (
                                    <div className="prob-section">
                                        <h4>Examples</h4>
                                        {examples.map((ex, i) => (
                                            <div key={i} className="example-block">
                                                <div><strong>Input:</strong> <code>{ex.input}</code></div>
                                                <div><strong>Output:</strong> <code>{ex.output}</code></div>
                                                {ex.explanation && <div className="ex-explain">{ex.explanation}</div>}
                                            </div>
                                        ))}
                                    </div>
                                )}
                                <div className="prob-meta">
                                    <span>⏱ {activeProblem.time_limit_ms}ms</span>
                                    <span>💾 {activeProblem.memory_limit_mb}MB</span>
                                    <span>🏅 {activeProblem.base_score}pts</span>
                                </div>
                            </div>
                        ) : <div className="page-loading"><div className="spinner lg-spinner" /></div>}
                    </div>
                </div>

                <div className="resizer" />

                {/* Right: code editor + output */}
                <div className="right-pane">
                    <div className="pane-header">
                        <div className="lang-tabs" style={{ border: 'none', background: 'transparent', padding: 0 }}>
                            {Object.entries(LANGS).map(([k, cfg]) => (
                                <button key={k} className={`lang-tab ${language === k ? 'active' : ''}`}
                                    onClick={() => setLanguage(k)}>
                                    <span className="lang-dot" style={language !== k ? { background: cfg.color } : {}} />
                                    {cfg.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div style={{ flex: '1 1 55%', overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                        {activeProblem && (
                            <CodeEditor language={language} value={userCode} onChange={setUserCode} />
                        )}
                    </div>

                    {/* Submission result */}
                    <div className="output-section" style={{ flex: '0 0 auto', maxHeight: '35%' }}>
                        <div className="output-tabs-row">
                            <button className={`output-tab ${activeTab === 'problem' ? 'active' : ''}`} onClick={() => setActiveTab('problem')}>Overview</button>
                            <button className={`output-tab ${activeTab === 'run_result' ? 'active' : ''}`} onClick={() => setActiveTab('run_result')}>Run Result</button>
                            <button className={`output-tab ${activeTab === 'result' ? 'active' : ''}`} onClick={() => setActiveTab('result')}>Submit Result</button>
                            <button className={`output-tab ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>Submissions</button>
                        </div>
                        <div className="output-content">
                            {activeTab === 'problem' && (
                                <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                                    <p>Write your <code>solution()</code> function above and press <kbd className="mini-key">Submit</kbd>.</p>
                                    <p style={{ marginTop: 8 }}>The driver code is hidden — your function return value is compared against expected outputs.</p>
                                </div>
                            )}
                            {activeTab === 'run_result' && runResult && (
                                <div className="result-block">
                                    {runResult.error && <div className="err-banner banner-re"><strong>Error:</strong> {runResult.error}</div>}
                                    {!runResult.error && (
                                        <>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                                <span className={`verdict ${runResult.exit_code === 0 ? 'v-ac' : 'v-re'}`}>
                                                    {runResult.exit_code === 0 ? 'Finished execution' : `Exit code: ${runResult.exit_code}`}
                                                </span>
                                                <span className="time-badge">{runResult.execution_time_ms} ms</span>
                                            </div>
                                            <div className="diff-grid">
                                                <div className="diff-col">
                                                    <div className="diff-label">Example Input</div>
                                                    <pre className="diff-pre">{runResult._input}</pre>
                                                </div>
                                                <div className="diff-col">
                                                    <div className="diff-label">Your Output</div>
                                                    <pre className="diff-pre">{runResult.stdout || ' '}</pre>
                                                </div>
                                            </div>
                                            {runResult.stderr && (
                                                <div className="err-banner banner-re" style={{ marginTop: 12 }}>
                                                    <strong>Stderr:</strong> <pre style={{ margin: 0, marginTop: 4 }}>{runResult.stderr}</pre>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}
                            {activeTab === 'result' && result && (
                                <div className="result-block">
                                    {result.error && <div className="err-banner banner-re"><strong>Error:</strong> {result.error}</div>}
                                    {!result.error && (
                                        <>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                                <span className={`verdict ${VERDICT_CLASS[result.verdict] || 'verdict-idle'}`}>{result.verdict}</span>
                                                <span className="time-badge">{result.execution_ms} ms</span>
                                                <span className="time-badge">Score: {result.score}</span>
                                            </div>
                                            <div className="diff-grid">
                                                <div className="diff-col">
                                                    <div className="diff-label">Passed</div>
                                                    <pre className="diff-pre diff-ac">{result.passed_cases} / {result.total_cases} test cases</pre>
                                                </div>
                                                {result.stderr && (
                                                    <div className="diff-col">
                                                        <div className="diff-label">Stderr</div>
                                                        <pre className="diff-pre diff-wa" style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{result.stderr}</pre>
                                                    </div>
                                                )}
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                            {activeTab === 'history' && (
                                <div className="result-block">
                                    {history_.length === 0
                                        ? <span className="muted-text">No submissions for this problem yet.</span>
                                        : history_.map(s => (
                                            <div key={s.id} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                                <span className={`verdict ${VERDICT_CLASS[s.verdict] || 'verdict-idle'}`}>{s.verdict}</span>
                                                <span className="time-badge">{s.passed_cases}/{s.total_cases}</span>
                                                <span className="time-badge">Score: {s.score}</span>
                                                <span className="muted-text" style={{ marginLeft: 'auto' }}>{new Date(s.submitted_at).toLocaleTimeString()}</span>
                                            </div>
                                        ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
