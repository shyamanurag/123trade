import {
    Circle,
    Refresh
} from '@mui/icons-material';
import { Box, Chip, IconButton, Tooltip, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';

const WebSocketStatus = ({ userId }) => {
    const [wsStatus, setWsStatus] = useState('disconnected');
    const [ws, setWs] = useState(null);

    useEffect(() => {
        // Only connect if we have a valid userId (not 'default_user')
        if (!userId || userId === 'default_user') {
            setWsStatus('waiting');
            return;
        }

        const connectWebSocket = () => {
            try {
                const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/${userId}`;
                const websocket = new WebSocket(wsUrl);

                websocket.onopen = () => {
                    console.log('WebSocket connected');
                    setWsStatus('connected');
                };

                websocket.onclose = () => {
                    console.log('WebSocket disconnected');
                    setWsStatus('disconnected');
                    // Reconnect after 5 seconds
                    setTimeout(connectWebSocket, 5000);
                };

                websocket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    setWsStatus('error');
                };

                setWs(websocket);

                return () => {
                    websocket.close();
                };
            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                setWsStatus('error');
            }
        };

        const cleanup = connectWebSocket();
        return cleanup;
    }, [userId]);

    const getStatusColor = () => {
        switch (wsStatus) {
            case 'connected':
                return 'success';
            case 'disconnected':
                return 'error';
            case 'waiting':
                return 'warning';
            case 'error':
                return 'error';
            default:
                return 'default';
        }
    };

    const getStatusText = () => {
        switch (wsStatus) {
            case 'connected':
                return 'Live';
            case 'disconnected':
                return 'Offline';
            case 'waiting':
                return 'Waiting';
            case 'error':
                return 'Error';
            default:
                return 'Unknown';
        }
    };

    return (
        <Box sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            p: 1,
            borderRadius: 1,
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider'
        }}>
            <Circle
                sx={{
                    fontSize: 12,
                    color: getStatusColor() === 'success' ? 'success.main' : getStatusColor() === 'error' ? 'error.main' : 'warning.main',
                    animation: getStatusColor() === 'success' ? 'pulse 2s infinite' : 'none',
                    '@keyframes pulse': {
                        '0%': { opacity: 1 },
                        '50%': { opacity: 0.5 },
                        '100%': { opacity: 1 }
                    }
                }}
            />

            <Typography variant="body2" sx={{ minWidth: 100 }}>
                WebSocket
            </Typography>

            <Tooltip title={`WebSocket Status: ${getStatusText()}`}>
                <Chip
                    icon={<Circle />}
                    label={getStatusText()}
                    color={getStatusColor()}
                    size="small"
                    variant="filled"
                    sx={{
                        '& .MuiChip-icon': {
                            fontSize: 12,
                            marginLeft: 1
                        }
                    }}
                />
            </Tooltip>

            {getStatusColor() === 'error' && (
                <Tooltip title="Reconnect">
                    <IconButton
                        size="small"
                        onClick={() => {
                            // Implement reconnect logic here
                        }}
                        color="primary"
                    >
                        <Refresh />
                    </IconButton>
                </Tooltip>
            )}
        </Box>
    );
};

export default WebSocketStatus; 