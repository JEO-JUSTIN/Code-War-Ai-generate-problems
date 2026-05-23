// api.js — Centralized API client for CodeWar
// Determine API base URL: use env var if available, otherwise use current host
const getBaseURL = () => {
    if (import.meta.env.VITE_API_URL) {
        return import.meta.env.VITE_API_URL
    }
    // Auto-detect from current location (works in production)
    return window.location.origin
}
const BASE = getBaseURL()

function getToken() {
    return localStorage.getItem('cw_token')
}

async function req(method, path, body, auth = true) {
    const headers = { 'Content-Type': 'application/json' }
    if (auth) {
        const t = getToken()
        if (t) headers['Authorization'] = `Bearer ${t}`
    }
    const res = await fetch(BASE + path, {
        method,
        headers,
        body: body != null ? JSON.stringify(body) : undefined,
    })
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Request failed')
    }
    return res.json()
}

// Auth
export const apiRegister = (d) => req('POST', '/auth/register', d, false)
export const apiLogin = async (username, password) => {
    const fd = new URLSearchParams({ username, password })
    const res = await fetch(BASE + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: fd
    })
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Login failed') }
    return res.json()
}
export const apiMe = () => req('GET', '/auth/me')

// Contests (public)
export const apiContests = () => req('GET', '/contests', null, false)
export const apiContest = (id) => req('GET', `/contests/${id}`, null, false)
export const apiProblems = (cid) => req('GET', `/contests/${cid}/problems`)
export const apiProblem = (cid, pid) => req('GET', `/contests/${cid}/problems/${pid}`)
export const apiSubmit = (cid, body) => req('POST', `/contests/${cid}/submit`, body)
export const apiMySubmissions = (cid, pid) => req('GET', `/contests/${cid}/submissions?problem_id=${pid}`)
export const apiLeaderboard = (cid) => req('GET', `/contests/${cid}/leaderboard`, null, false)
export const apiExecute = (body) => req('POST', '/execute', body, false)

// Admin
export const apiAdminContests = () => req('GET', '/admin/contests')
export const apiAdminCreateContest = (body) => req('POST', '/admin/contests', body)
export const apiAdminGenerateProblem = (cid, body) => req('POST', `/admin/contests/${cid}/problems/generate`, body)
export const apiAdminDeleteProblem = (cid, pid) => req('DELETE', `/admin/contests/${cid}/problems/${pid}`)
export const apiAdminUpdateTestcases = (cid, pid, body) => req('PUT', `/admin/contests/${cid}/problems/${pid}/testcases`, body)
