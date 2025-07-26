import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useWebSocket } from '../../context/WebSocketContext'
import Header from './Header'
import Sidebar from './Sidebar'

const Layout = () => {
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const { connectionStatus } = useWebSocket()

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Connection Status Banner */}
            {connectionStatus !== 'connected' && (
                <div className={`w-full px-4 py-2 text-center text-sm font-medium ${connectionStatus === 'connecting' ? 'bg-warning-100 text-warning-800' :
                        connectionStatus === 'error' ? 'bg-danger-100 text-danger-800' :
                            'bg-gray-100 text-gray-800'
                    }`}>
                    {connectionStatus === 'connecting' && '🔄 Connecting to real-time data...'}
                    {connectionStatus === 'error' && '⚠️ Real-time connection failed. Retrying...'}
                    {connectionStatus === 'disconnected' && '🔌 Real-time data disconnected'}
                    {connectionStatus === 'failed' && '❌ Unable to connect to real-time data'}
                </div>
            )}

            {/* Sidebar */}
            <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

            {/* Main Content */}
            <div className={`transition-all duration-300 ${sidebarOpen ? 'lg:ml-64' : 'lg:ml-20'}`}>
                {/* Header */}
                <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />

                {/* Page Content */}
                <main className="p-6">
                    <div className="max-w-7xl mx-auto">
                        <Outlet />
                    </div>
                </main>
            </div>

            {/* Mobile Overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}
        </div>
    )
}

export default Layout 