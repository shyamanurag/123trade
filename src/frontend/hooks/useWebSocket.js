import { useCallback, useEffect, useRef, useState } from 'react';

// Use production WebSocket URL from environment variable
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'wss://algoauto-ua2iq.ondigitalocean.app';

export const useWebSocket = (userId = 'default_user') => {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const [connectionStats, setConnectionStats] = useState({
        connected: false,
        reconnectAttempts: 0,
        lastError: null
    });

    const ws = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const reconnectAttemptsRef = useRef(0);
    const maxReconnectAttempts = 5;
    const reconnectDelay = 5000; // 5 seconds
    const mountedRef = useRef(true);

    const sendMessage = useCallback((message) => {
        if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(message));
            console.log('Message sent:', message);
        } else {
            console.error('WebSocket is not connected');
        }
    }, []);

    const connect = useCallback(() => {
        // Don't connect if already connected or connecting
        if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
            console.log('WebSocket already connected or connecting');
            return;
        }

        // Don't connect if component is unmounted
        if (!mountedRef.current) {
            return;
        }

        try {
            const wsUrl = `${WS_BASE_URL}/ws/${userId}`;
            console.log('Connecting to WebSocket:', wsUrl);

            const newWs = new WebSocket(wsUrl);

            newWs.onopen = () => {
                console.log('WebSocket connected');
                ws.current = newWs;
                setIsConnected(true);
                reconnectAttemptsRef.current = 0;
                setConnectionStats({
                    connected: true,
                    reconnectAttempts: 0,
                    lastError: null
                });

                // Subscribe to market data after connection
                setTimeout(() => {
                    sendMessage({
                        type: 'subscribe',
                        room: 'market_data_NIFTY'
                    });
                }, 100);
            };

            newWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('WebSocket message received:', data);
                    setLastMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            newWs.onerror = (error) => {
                console.error('WebSocket error:', error);
                setConnectionStats(prev => ({
                    ...prev,
                    lastError: 'Connection error'
                }));
            };

            newWs.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                ws.current = null;
                setIsConnected(false);
                setConnectionStats(prev => ({
                    ...prev,
                    connected: false
                }));

                // Only reconnect if component is still mounted and we haven't exceeded attempts
                if (mountedRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
                    reconnectAttemptsRef.current++;
                    console.log(`Will reconnect in ${reconnectDelay / 1000}s... Attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`);

                    // Clear any existing timeout
                    if (reconnectTimeoutRef.current) {
                        clearTimeout(reconnectTimeoutRef.current);
                    }

                    reconnectTimeoutRef.current = setTimeout(() => {
                        if (mountedRef.current) {
                            connect();
                        }
                    }, reconnectDelay);
                } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
                    console.error('Max reconnection attempts reached');
                    setConnectionStats(prev => ({
                        ...prev,
                        lastError: 'Max reconnection attempts reached'
                    }));
                }
            };

        } catch (error) {
            console.error('Error creating WebSocket connection:', error);
            setConnectionStats(prev => ({
                ...prev,
                lastError: error.message
            }));
        }
    }, [userId, sendMessage]);

    const disconnect = useCallback(() => {
        console.log('Disconnecting WebSocket');

        // Clear reconnect timeout
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        // Close WebSocket connection
        if (ws.current) {
            ws.current.close();
            ws.current = null;
        }

        setIsConnected(false);
        reconnectAttemptsRef.current = 0;
    }, []);

    const subscribe = useCallback((symbol, provider = 'ALL') => {
        sendMessage({
            type: 'subscribe',
            room: `market_data_${symbol}`
        });
    }, [sendMessage]);

    const unsubscribe = useCallback((symbol, provider = 'ALL') => {
        sendMessage({
            type: 'unsubscribe',
            room: `market_data_${symbol}`
        });
    }, [sendMessage]);

    // Connect on mount
    useEffect(() => {
        mountedRef.current = true;
        connect();

        // Cleanup on unmount
        return () => {
            mountedRef.current = false;
            disconnect();
        };
    }, []); // Empty deps - only run on mount/unmount

    // Heartbeat
    useEffect(() => {
        const heartbeatInterval = setInterval(() => {
            if (isConnected && ws.current?.readyState === WebSocket.OPEN) {
                sendMessage({ type: 'heartbeat' });
            }
        }, 30000);

        return () => clearInterval(heartbeatInterval);
    }, [isConnected, sendMessage]);

    return {
        isConnected,
        lastMessage,
        connectionStats,
        sendMessage,
        subscribe,
        unsubscribe,
        reconnect: connect,
        disconnect
    };
}; 