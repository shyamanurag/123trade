import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { io } from 'socket.io-client'
import { useAuth } from './AuthContext'

const WebSocketContext = createContext()

export const useWebSocket = () => {
    const context = useContext(WebSocketContext)
    if (!context) {
        throw new Error('useWebSocket must be used within a WebSocketProvider')
    }
    return context
}

export const WebSocketProvider = ({ children }) => {
    const { authToken, user } = useAuth()
    const [socket, setSocket] = useState(null)
    const [isConnected, setIsConnected] = useState(false)
    const [marketData, setMarketData] = useState({})
    const [liveIndices, setLiveIndices] = useState([])
    const [tradingAlerts, setTradingAlerts] = useState([])
    const [connectionStatus, setConnectionStatus] = useState('disconnected')
    const reconnectAttempts = useRef(0)
    const maxReconnectAttempts = 5

    useEffect(() => {
        if (authToken && user) {
            initializeSocket()
        } else {
            disconnectSocket()
        }

        return () => {
            disconnectSocket()
        }
    }, [authToken, user])

    const initializeSocket = () => {
        try {
            const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

            const newSocket = io(wsUrl, {
                auth: {
                    token: authToken,
                    userId: user?.id
                },
                transports: ['websocket', 'polling'],
                timeout: 20000,
                reconnection: true,
                reconnectionAttempts: maxReconnectAttempts,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000
            })

            setupSocketListeners(newSocket)
            setSocket(newSocket)
            setConnectionStatus('connecting')
        } catch (error) {
            console.error('Socket initialization error:', error)
            setConnectionStatus('error')
        }
    }

    const setupSocketListeners = (socket) => {
        socket.on('connect', () => {
            console.log('WebSocket connected')
            setIsConnected(true)
            setConnectionStatus('connected')
            reconnectAttempts.current = 0

            // Subscribe to channels
            socket.emit('subscribe', {
                channels: ['market_data', 'live_indices', 'trading_alerts', 'user_notifications']
            })
        })

        socket.on('disconnect', (reason) => {
            console.log('WebSocket disconnected:', reason)
            setIsConnected(false)
            setConnectionStatus('disconnected')

            if (reason === 'io server disconnect') {
                // Manual disconnect, don't reconnect
                return
            }
        })

        socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error)
            setConnectionStatus('error')
            reconnectAttempts.current++

            if (reconnectAttempts.current >= maxReconnectAttempts) {
                toast.error('Failed to connect to real-time data. Please refresh the page.')
                setConnectionStatus('failed')
            }
        })

        socket.on('market_data', (data) => {
            setMarketData(prevData => ({
                ...prevData,
                [data.symbol]: {
                    ...data,
                    timestamp: new Date()
                }
            }))
        })

        socket.on('live_indices', (data) => {
            setLiveIndices(data)
        })

        socket.on('trading_alert', (alert) => {
            setTradingAlerts(prev => [alert, ...prev.slice(0, 99)]) // Keep last 100 alerts

            // Show toast notification for important alerts
            if (alert.priority === 'high') {
                toast.success(`Trading Alert: ${alert.message}`, {
                    duration: 6000
                })
            }
        })

        socket.on('user_notification', (notification) => {
            toast(notification.message, {
                icon: notification.type === 'success' ? '✅' :
                    notification.type === 'warning' ? '⚠️' :
                        notification.type === 'error' ? '❌' : 'ℹ️'
            })
        })

        socket.on('token_expired', () => {
            toast.error('Your session has expired. Please login again.')
            // The AuthContext will handle the logout
        })
    }

    const disconnectSocket = () => {
        if (socket) {
            socket.disconnect()
            setSocket(null)
            setIsConnected(false)
            setConnectionStatus('disconnected')
        }
    }

    const subscribeToSymbol = (symbol) => {
        if (socket && isConnected) {
            socket.emit('subscribe_symbol', { symbol })
        }
    }

    const unsubscribeFromSymbol = (symbol) => {
        if (socket && isConnected) {
            socket.emit('unsubscribe_symbol', { symbol })
        }
    }

    const sendMessage = (event, data) => {
        if (socket && isConnected) {
            socket.emit(event, data)
        } else {
            toast.error('No real-time connection available')
        }
    }

    const value = {
        socket,
        isConnected,
        connectionStatus,
        marketData,
        liveIndices,
        tradingAlerts,
        subscribeToSymbol,
        unsubscribeFromSymbol,
        sendMessage
    }

    return (
        <WebSocketContext.Provider value={value}>
            {children}
        </WebSocketContext.Provider>
    )
} 