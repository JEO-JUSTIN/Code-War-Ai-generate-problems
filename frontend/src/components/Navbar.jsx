// components/Navbar.jsx
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'

export default function Navbar() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()

    function handleLogout() {
        logout()
        navigate('/login')
    }

    return (
        <nav className="navbar">
            <Link to="/" className="nav-logo">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <defs><linearGradient id="gnav" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#6c63ff" /><stop offset="100%" stopColor="#a78bfa" />
                    </linearGradient></defs>
                    <path d="M8 6L3 12L8 18" stroke="url(#gnav)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M16 6L21 12L16 18" stroke="url(#gnav)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M13 4L11 20" stroke="url(#gnav)" strokeWidth="2" strokeLinecap="round" />
                </svg>
                CodeWar
            </Link>
            <div className="nav-spacer" />
            {user && (
                <>
                    <span className="nav-user">
                        <span className={`role-badge ${user.role}`}>{user.role}</span>
                        {user.username}
                    </span>
                    {user.role === 'admin' && <Link to="/admin" className="nav-link">Dashboard</Link>}
                    <button className="nav-logout" onClick={handleLogout}>Sign Out</button>
                </>
            )}
            {!user && <Link to="/login" className="btn-primary sm">Sign In</Link>}
        </nav>
    )
}
