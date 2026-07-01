import { useState, useEffect, useCallback } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './components/Login'
import Chat from './components/Chat'
import Layout from './components/Layout/Layout'
import EmployeeDashboard from './components/Dashboards/EmployeeDashboard'
import ManagerDashboard from './components/Dashboards/ManagerDashboard'
import CEODashboard from './components/Dashboards/CEODashboard'


function App() {
    const [token, setToken] = useState(() => localStorage.getItem('qachat_token'))
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(!!localStorage.getItem('qachat_token'))

    const handleLogout = useCallback(() => {
        localStorage.removeItem('qachat_token')
        setToken(null)
        setUser(null)
        setLoading(false)
    }, [])

    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const githubToken = params.get('token')
        const error = params.get('error')

        if (githubToken) {
            localStorage.setItem('qachat_token', githubToken)
            setToken(githubToken)
            window.history.replaceState({}, '', '/')
            return
        }
        if (error) {
            console.error('OAuth error:', error)
            window.history.replaceState({}, '', '/')
        }
    }, [])

    useEffect(() => {
        if (!token) {
            setLoading(false)
            return
        }
        if (user) {
            setLoading(false)
            return
        }
        setLoading(true)
        fetch('/api/me', {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((r) => r.json())
            .then((data) => {
                if (data.success) {
                    setUser(data.user)
                } else {
                    handleLogout()
                }
            })
            .catch(() => {
                setUser(null)
                setLoading(false)
            })
            .finally(() => setLoading(false))
    }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

    const handleLoginSuccess = ({ token: t, user: u }) => {
        localStorage.setItem('qachat_token', t)
        setUser(u)
        setToken(t)
        setLoading(false)
    }

    if (loading) {
        return (
            <div className="main-wrapper" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ color: '#aaa', fontSize: '1rem' }}>Loading…</div>
            </div>
        )
    }

    if (!token || !user) {
        return <div className="main-wrapper"><Login onLoginSuccess={handleLoginSuccess} /></div>
    }

    // Role-based Dashboard Router
    const DashboardRouter = () => {
        if (user.role === 'ceo') return <CEODashboard user={user} token={token} onLogout={handleLogout} />;
        if (user.role === 'manager') return <ManagerDashboard user={user} token={token} onLogout={handleLogout} />;
        return <EmployeeDashboard user={user} token={token} onLogout={handleLogout} />;
    };

    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Layout user={user} token={token} onLogout={handleLogout} />}>
                    {/* Role-based dashboard root */}
                    <Route index element={<DashboardRouter />} />
                    

                    
                    {/* Legacy AI Chat */}
                    <Route path="ai-chat" element={<div style={{ height: 'calc(100vh - 40px)', padding: '20px' }}><Chat user={user} token={token} onLogout={handleLogout} /></div>} />
                    
                    {/* Catch all */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}

export default App
