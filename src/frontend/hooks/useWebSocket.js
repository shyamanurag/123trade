import { useCallback, useEffect, useRef, useState } from 'react';

// WebSocket and API configuration
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'wss://quantumcrypto-l43mb.ondigitalocean.app/ws';
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app';

// ELIMINATED: Default symbols removed - no hardcoded symbols allowed
// Original violation: DEFAULT_SYMBOLS = ['RELIANCE', 'TCS', 'NIFTY', 'BANKNIFTY', 'INFY', 'HDFCBANK']
// This could be used to generate fake market data for these symbols
// All symbols must come from real market data sources

const useWebSocket = (url) => {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const [error, setError] = useState(null);
    const [connectionType, setConnectionType] = useState(null); // 'websocket' or 'sse'

    const wsRef = useRef(null);
    const sseRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const reconnectAttemptsRef = useRef(0);
    const maxReconnectAttempts = 5;
    const reconnectDelay = 3000; // 3 seconds

    // Use the provided URL or default to WS_BASE_URL
    const wsUrl = url || WS_BASE_URL;

    // SSE URL - replace wss:// with https:// and /ws with /ws/sse
    const sseUrl = wsUrl.replace('wss://', 'https://').replace('ws://', 'http://').replace(/\/ws$/, '/ws/sse');

    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        try {
            console.log(`Attempting WebSocket connection to: ${wsUrl}`);
            wsRef.current = new WebSocket(wsUrl);

            wsRef.current.onopen = () => {
                console.log('WebSocket connected successfully');
                setIsConnected(true);
                setConnectionType('websocket');
                setError(null);
                reconnectAttemptsRef.current = 0;

                // Subscribe to default symbols
                // DEFAULT_SYMBOLS.forEach(symbol => { // This line is removed
                //     sendMessage({
                //         type: 'subscribe',
                //         symbol: symbol
                //     });
                // });
            };

            wsRef.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setLastMessage(data);
                } catch (err) {
                    console.error('Error parsing WebSocket message:', err);
                }
            };

            wsRef.current.onerror = (event) => {
                console.error('WebSocket error:', event);
                setError('WebSocket connection error');

                // If WebSocket fails, try SSE
                if (!sseRef.current) {
                    console.log('WebSocket failed, attempting SSE fallback...');
                    connectSSE();
                }
            };

            wsRef.current.onclose = (event) => {
                console.log('WebSocket disconnected');
                setIsConnected(false);
                setConnectionType(null);
                wsRef.current = null;

                // Try SSE if WebSocket closed unexpectedly
                if (event.code !== 1000 && !sseRef.current) {
                    console.log('WebSocket closed unexpectedly, attempting SSE fallback...');
                    connectSSE();
                }
            };

        } catch (err) {
            console.error('Error creating WebSocket:', err);
            setError(err.message);

            // Try SSE as fallback
            connectSSE();
        }
    }, [wsUrl]);

    const connectSSE = useCallback(() => {
        if (sseRef.current) {
            console.log('SSE already connected');
            return;
        }

        try {
            console.log(`Attempting SSE connection to: ${sseUrl}`);
            sseRef.current = new EventSource(sseUrl);

            sseRef.current.onopen = () => {
                console.log('SSE connected successfully');
                setIsConnected(true);
                setConnectionType('sse');
                setError(null);
                reconnectAttemptsRef.current = 0;
            };

            sseRef.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setLastMessage(data);
                } catch (err) {
                    console.error('Error parsing SSE message:', err);
                }
            };

            sseRef.current.onerror = (event) => {
                console.error('SSE error:', event);
                setError('SSE connection error');

                if (sseRef.current?.readyState === EventSource.CLOSED) {
                    console.log('SSE connection closed');
                    setIsConnected(false);
                    setConnectionType(null);
                    sseRef.current = null;

                    // Schedule reconnection
                    scheduleReconnect();
                }
            };

        } catch (err) {
            console.error('Error creating SSE connection:', err);
            setError(err.message);
            scheduleReconnect();
        }
    }, [sseUrl]);

    const scheduleReconnect = useCallback(() => {
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            reconnectAttemptsRef.current += 1;
            console.log(`Scheduling reconnection attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts} in ${reconnectDelay}ms`);

            reconnectTimeoutRef.current = setTimeout(() => {
                // Try WebSocket first, then SSE as fallback
                connectWebSocket();
            }, reconnectDelay);
        } else {
            console.error('Max reconnection attempts reached');
            setError('Unable to establish connection after multiple attempts');
        }
    }, [connectWebSocket]);

    const disconnect = useCallback(() => {
        // Clear any reconnection timeout
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        // Close WebSocket
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        // Close SSE
        if (sseRef.current) {
            sseRef.current.close();
            sseRef.current = null;
        }

        setIsConnected(false);
        setConnectionType(null);
        setError(null);
        reconnectAttemptsRef.current = 0;
    }, []);

    const sendMessage = useCallback((message) => {
        if (connectionType === 'websocket' && wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
        } else if (connectionType === 'sse') {
            // SSE is receive-only, so we need to use a regular HTTP request for sending
            console.log('SSE is receive-only. Use HTTP API for sending messages.');
            // You could make an HTTP POST request here if needed
        } else {
            console.error('No active connection to send message');
        }
    }, [connectionType]);

    // Connect on mount
    useEffect(() => {
        connectWebSocket();

        // Cleanup on unmount
        return () => {
            disconnect();
        };
    }, [connectWebSocket, disconnect]);

    // Heartbeat to keep connection alive
    useEffect(() => {
        if (!isConnected) return;

        const heartbeatInterval = setInterval(() => {
            if (connectionType === 'websocket') {
                sendMessage({ type: 'heartbeat' });
            }
            // SSE doesn't need client-side heartbeat
        }, 30000); // Every 30 seconds

        return () => clearInterval(heartbeatInterval);
    }, [isConnected, connectionType, sendMessage]);

    return {
        isConnected,
        lastMessage,
        error,
        sendMessage,
        disconnect,
        reconnect: connectWebSocket,
        connectionType
    };
};

export default useWebSocket; 