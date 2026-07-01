import { useState } from 'react'

function Login({ onLoginSuccess }) {
    const [mode, setMode] = useState('login') // 'login' | 'register' | 'forgot'
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [role, setRole] = useState('employee')
    const [employeeId, setEmployeeId] = useState('')
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    // Forgot password state
    const [fpEmail, setFpEmail] = useState('')
    const [fpRole, setFpRole] = useState('employee')
    const [fpNewPassword, setFpNewPassword] = useState('')
    const [fpConfirmPassword, setFpConfirmPassword] = useState('')
    const [fpShowPassword, setFpShowPassword] = useState(false)

    const switchMode = (m) => {
        setMode(m)
        setError('')
        setSuccess('')
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setIsLoading(true)

        const endpoint = mode === 'register' ? '/api/register' : '/api/login'

        try {
            const bodyData = { email: email.trim(), password: password.trim() }
            if (mode === 'register') {
                bodyData.role = role
                bodyData.employee_id = employeeId.trim()
            }
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyData),
            })

            const data = await response.json()

            if (data.success) {
                onLoginSuccess({ token: data.token, user: data.user })
            } else {
                setError(data.message || (mode === 'register' ? 'Registration failed' : 'Login failed'))
            }
        } catch (err) {
            setError('Could not connect to the server')
        } finally {
            setIsLoading(false)
        }
    }

    const handleForgotPassword = async (e) => {
        e.preventDefault()
        setError('')
        setSuccess('')

        if (fpNewPassword !== fpConfirmPassword) {
            setError('Passwords do not match')
            return
        }
        if (fpNewPassword.length < 6) {
            setError('Password must be at least 6 characters')
            return
        }

        setIsLoading(true)
        try {
            const res = await fetch('/api/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: fpEmail.trim().toLowerCase(),
                    role: fpRole,
                    new_password: fpNewPassword.trim(),
                }),
            })
            const data = await res.json()
            if (data.success) {
                setSuccess(data.message)
                // Pre-fill login form with the email for convenience
                setEmail(fpEmail.trim().toLowerCase())
                setFpEmail('')
                setFpRole('employee')
                setFpNewPassword('')
                setFpConfirmPassword('')
                // Auto-switch to login after 2.5 seconds
                setTimeout(() => switchMode('login'), 2500)
            } else {
                setError(data.message)
            }
        } catch {
            setError('Could not connect to the server')
        } finally {
            setIsLoading(false)
        }
    }

    const handleGitHubLogin = () => {
        window.location.href = '/api/auth/github'
    }

    const handleDemoLogin = (role) => {
        setEmail(`${role}@test.com`)
        setPassword('password123')
        setMode('login')
        setError('')
        setIsLoading(true)
        fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: `${role}@test.com`, password: 'password123' }),
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                onLoginSuccess({ token: data.token, user: data.user })
            } else {
                setError('Demo login failed. Did you register the demo accounts?')
            }
        })
        .catch(() => setError('Could not connect to the server'))
        .finally(() => setIsLoading(false))
    }

    return (
        <div className="login-container">
            <div className="login-card">
                <h1 className="login-logo">QA Chat</h1>
                <p style={{ color: '#aaa', fontSize: '0.85rem', marginBottom: '20px', textAlign: 'center' }}>
                    {mode === 'register' ? 'Create your account' : mode === 'forgot' ? 'Reset your password' : 'Sign in to your account'}
                </p>

                {error && <p className="error-message">{error}</p>}
                {success && (
                    <div style={{
                        background: '#d4edda', border: '1px solid #c3e6cb', borderRadius: '6px',
                        padding: '12px 14px', marginBottom: '14px', fontSize: '13px', color: '#155724',
                        display: 'flex', alignItems: 'center', gap: '8px'
                    }}>
                        ✅ {success}
                    </div>
                )}

                {/* ── Login / Register Form ── */}
                {(mode === 'login' || mode === 'register') && (
                    <form onSubmit={handleSubmit} className="login-form-fields">
                        {mode === 'register' && (
                            <>
                                <select
                                    value={role}
                                    onChange={(e) => setRole(e.target.value)}
                                    style={{ padding: '12px', border: '1px solid #dbdbdb', borderRadius: '4px', background: '#fafafa', fontSize: '14px', width: '100%', boxSizing: 'border-box' }}
                                >
                                    <option value="employee">Employee</option>
                                    <option value="manager">Manager</option>
                                    <option value="ceo">CEO</option>
                                </select>
                                <input
                                    type="text"
                                    placeholder="Employee ID (Optional)"
                                    value={employeeId}
                                    onChange={(e) => setEmployeeId(e.target.value)}
                                    style={{ padding: '12px', border: '1px solid #dbdbdb', borderRadius: '4px', background: '#fafafa', fontSize: '14px', width: '100%', boxSizing: 'border-box', marginTop: '10px' }}
                                />
                            </>
                        )}
                        <input
                            id="login-email"
                            type="email"
                            placeholder="Email address"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            autoComplete="email"
                            style={{ marginTop: '10px' }}
                        />
                        <input
                            id="login-password"
                            type="password"
                            placeholder="Password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                            minLength={6}
                        />
                        <button id="login-submit" type="submit" className="login-submit-btn" disabled={isLoading}>
                            {isLoading
                                ? (mode === 'register' ? 'Creating account…' : 'Signing in…')
                                : (mode === 'register' ? 'Create Account' : 'Sign In')}
                        </button>

                        {/* Forgot Password link — only on login mode */}
                        {mode === 'login' && (
                            <div style={{ textAlign: 'center', marginTop: '10px' }}>
                                <span
                                    onClick={() => switchMode('forgot')}
                                    style={{ fontSize: '13px', color: '#999', cursor: 'pointer', textDecoration: 'underline' }}
                                >
                                    Forgot your password?
                                </span>
                            </div>
                        )}
                    </form>
                )}

                {/* ── Forgot Password Form ── */}
                {mode === 'forgot' && (
                    <form onSubmit={handleForgotPassword} className="login-form-fields">

                        {/* Info box */}
                        <div style={{
                            background: '#e8f4fd', border: '1px solid #bee3f8', borderRadius: '6px',
                            padding: '11px 14px', marginBottom: '14px', fontSize: '12.5px', color: '#2b6cb0',
                            lineHeight: '1.5'
                        }}>
                            🔐 Enter your registered <strong>email</strong> and select your <strong>account role</strong> to verify your identity, then set a new password.
                        </div>

                        <input
                            type="email"
                            placeholder="Your registered email"
                            value={fpEmail}
                            onChange={e => setFpEmail(e.target.value)}
                            required
                            style={{ marginTop: '4px' }}
                        />
                        <select
                            value={fpRole}
                            onChange={e => setFpRole(e.target.value)}
                            required
                            style={{
                                padding: '12px', border: '1px solid #dbdbdb', borderRadius: '4px',
                                background: '#fafafa', fontSize: '14px', width: '100%',
                                boxSizing: 'border-box', marginTop: '10px'
                            }}
                        >
                            <option value="employee">Employee</option>
                            <option value="manager">Manager</option>
                            <option value="ceo">CEO</option>
                        </select>

                        <div style={{ position: 'relative', marginTop: '10px' }}>
                            <input
                                type={fpShowPassword ? 'text' : 'password'}
                                placeholder="New password (min. 6 characters)"
                                value={fpNewPassword}
                                onChange={e => setFpNewPassword(e.target.value)}
                                required
                                minLength={6}
                                style={{ width: '100%', boxSizing: 'border-box', paddingRight: '44px' }}
                            />
                            <button
                                type="button"
                                onClick={() => setFpShowPassword(p => !p)}
                                style={{
                                    position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                                    background: 'none', border: 'none', cursor: 'pointer', color: '#999', fontSize: '13px'
                                }}
                            >
                                {fpShowPassword ? '🙈' : '👁'}
                            </button>
                        </div>

                        <input
                            type={fpShowPassword ? 'text' : 'password'}
                            placeholder="Confirm new password"
                            value={fpConfirmPassword}
                            onChange={e => setFpConfirmPassword(e.target.value)}
                            required
                            minLength={6}
                            style={{ marginTop: '10px' }}
                        />

                        {/* Password match indicator */}
                        {fpNewPassword && fpConfirmPassword && (
                            <div style={{
                                fontSize: '12px', marginTop: '6px', padding: '6px 10px', borderRadius: '5px',
                                background: fpNewPassword === fpConfirmPassword ? '#d4edda' : '#f8d7da',
                                color: fpNewPassword === fpConfirmPassword ? '#155724' : '#721c24',
                            }}>
                                {fpNewPassword === fpConfirmPassword ? '✅ Passwords match' : '❌ Passwords do not match'}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="login-submit-btn"
                            disabled={isLoading || (fpNewPassword && fpConfirmPassword && fpNewPassword !== fpConfirmPassword)}
                            style={{ marginTop: '14px', background: '#16a085' }}
                        >
                            {isLoading ? 'Resetting password…' : 'Reset Password'}
                        </button>

                        <div style={{ textAlign: 'center', marginTop: '12px' }}>
                            <span
                                onClick={() => switchMode('login')}
                                style={{ fontSize: '13px', color: '#999', cursor: 'pointer', textDecoration: 'underline' }}
                            >
                                ← Back to Sign In
                            </span>
                        </div>
                    </form>
                )}

                {/* ── GitHub OAuth (not shown on forgot) ── */}
                {mode !== 'forgot' && (
                    <>
                        <div className="social-separator"><span>OR</span></div>
                        <button id="github-login-btn" className="github-link" onClick={handleGitHubLogin} style={{ width: '100%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24" style={{ marginRight: '8px' }}>
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.374-12-12-12z" />
                            </svg>
                            Continue with GitHub
                        </button>
                    </>
                )}
            </div>

            {/* Toggle login/register */}
            {mode !== 'forgot' && (
                <div className="login-card" style={{ padding: '20px', fontSize: '0.9rem', textAlign: 'center' }}>
                    {mode === 'login' ? (
                        <>Don't have an account?&nbsp;
                            <span
                                id="switch-to-register"
                                style={{ color: 'var(--insta-blue)', fontWeight: 600, cursor: 'pointer' }}
                                onClick={() => switchMode('register')}
                            >Sign up</span>
                        </>
                    ) : (
                        <>Already have an account?&nbsp;
                            <span
                                id="switch-to-login"
                                style={{ color: 'var(--insta-blue)', fontWeight: 600, cursor: 'pointer' }}
                                onClick={() => switchMode('login')}
                            >Sign in</span>
                        </>
                    )}
                </div>
            )}

            {/* Demo Logins */}
            {mode !== 'forgot' && (
                <div className="login-card" style={{ padding: '20px', fontSize: '0.9rem', textAlign: 'center', marginTop: '10px' }}>
                    <div style={{ marginBottom: '10px', color: '#666' }}>Quick Demo Logins:</div>
                    <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                        <button onClick={() => handleDemoLogin('employee')} style={{ padding: '8px 12px', background: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Employee</button>
                        <button onClick={() => handleDemoLogin('manager')} style={{ padding: '8px 12px', background: '#f39c12', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Manager</button>
                        <button onClick={() => handleDemoLogin('ceo')} style={{ padding: '8px 12px', background: '#8e44ad', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>CEO</button>
                    </div>
                </div>
            )}
        </div>
    )
}

export default Login
