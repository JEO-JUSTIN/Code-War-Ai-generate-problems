// AuthContext.jsx — global auth state
import { createContext, useContext, useState, useEffect } from 'react'
import { apiMe } from './api'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [ready, setReady] = useState(false)

    useEffect(() => {
        const token = localStorage.getItem('cw_token')
        if (token) {
            apiMe().then(setUser).catch(() => localStorage.removeItem('cw_token')).finally(() => setReady(true))
        } else {
            setReady(true)
        }
    }, [])

    function login(token, userObj) {
        localStorage.setItem('cw_token', token)
        setUser(userObj)
    }

    function logout() {
        localStorage.removeItem('cw_token')
        setUser(null)
    }

    return <AuthCtx.Provider value={{ user, ready, login, logout }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)
