import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import LoadingSpinner from './components/UI/LoadingSpinner'
import { useAuth } from './context/AuthContext'
import Analytics from './pages/Analytics'
import AuthTokenManagement from './pages/AuthTokenManagement'
import Dashboard from './pages/Dashboard'
import LiveIndices from './pages/LiveIndices'
import Login from './pages/Login'
import MultiUserAPI from './pages/MultiUserAPI'
import Settings from './pages/Settings'
import Trades from './pages/Trades'
import Users from './pages/Users'

function App() {
    const { user, loading } = useAuth()

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <LoadingSpinner size="large" />
            </div>
        )
    }

    return (
        <div className="App">
            <Routes>
                <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />

                {user ? (
                    <Route path="/" element={<Layout />}>
                        <Route index element={<Dashboard />} />
                        <Route path="dashboard" element={<Dashboard />} />
                        <Route path="live-indices" element={<LiveIndices />} />
                        <Route path="analytics" element={<Analytics />} />
                        <Route path="users" element={<Users />} />
                        <Route path="trades" element={<Trades />} />
                        <Route path="settings" element={<Settings />} />
                        <Route path="auth-tokens" element={<AuthTokenManagement />} />
                        <Route path="multi-user-api" element={<MultiUserAPI />} />
                    </Route>
                ) : (
                    <Route path="*" element={<Navigate to="/login" />} />
                )}
            </Routes>
        </div>
    )
}

export default App 