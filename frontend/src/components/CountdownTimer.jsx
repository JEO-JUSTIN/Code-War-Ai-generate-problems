// components/CountdownTimer.jsx
import { useEffect, useState } from 'react'

function fmt(ms) {
    if (ms <= 0) return 'Now'
    const s = Math.floor(ms / 1000)
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = s % 60
    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m ${sec}s`
    return `${sec}s`
}

export default function CountdownTimer({ target, label = 'In' }) {
    const [ms, setMs] = useState(() => new Date(target) - Date.now())

    useEffect(() => {
        const iv = setInterval(() => setMs(new Date(target) - Date.now()), 1000)
        return () => clearInterval(iv)
    }, [target])

    const urgent = ms < 5 * 60 * 1000
    return (
        <div className="countdown" style={urgent ? { color: 'var(--red)' } : {}}>
            <span className="cd-label">{label}:</span>
            <span className="cd-time">{fmt(ms)}</span>
        </div>
    )
}
