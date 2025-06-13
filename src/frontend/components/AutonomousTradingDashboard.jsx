import {
    CheckCircle,
    Pause,
    PersonAdd,
    PlayArrow,
    Schedule,
    SmartToy,
    Stop,
    TrendingUp,
    Warning
} from '@mui/icons-material';
import {
    Alert,
    Avatar,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    Divider,
    Grid,
    LinearProgress,
    List,
    ListItem,
    ListItemAvatar,
    ListItemText,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';

import API_ENDPOINTS from '../api/config';
import BrokerUserSetup from './BrokerUserSetup';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const AutonomousTradingDashboard = ({ userInfo }) => {
    const [marketStatus, setMarketStatus] = useState(null);
    const [sessionStats, setSessionStats] = useState(null);
    const [activePositions, setActivePositions] = useState([]);
    const [schedulerStatus, setSchedulerStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [tradingStatus, setTradingStatus] = useState(null);
    const [brokerUsers, setBrokerUsers] = useState([]);
    const [showBrokerSetup, setShowBrokerSetup] = useState(false);
    const [controlLoading, setControlLoading] = useState(false);

    useEffect(() => {
        fetchAutonomousData();
        fetchTradingStatus();
        fetchBrokerUsers();
        // Auto-refresh every 2 minutes so the UI does not interrupt user interactions
        const interval = setInterval(() => {
            fetchAutonomousData();
            fetchTradingStatus();
        }, 120000); // 120 000 ms = 2 minutes
        return () => clearInterval(interval);
    }, []);

    const fetchAutonomousData = async () => {
        setLoading(true);
        try {
            // Get authentication token
            const token = localStorage.getItem('auth_token');
            const headers = {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` })
            };

            // Fetch real autonomous trading data from API
            const results = await Promise.allSettled([
                fetch(API_ENDPOINTS.SYSTEM_STATUS, { headers }),
                fetch(API_ENDPOINTS.SESSION_STATS, { headers }),
                fetch(API_ENDPOINTS.POSITIONS, { headers }),
                fetch(API_ENDPOINTS.SYSTEM_STATUS, { headers })   // Using status endpoint for scheduler
            ]);

            const [
                marketStatusRes,
                sessionStatsRes,
                positionsRes,
                schedulerRes
            ] = results;

            // Process market status
            if (marketStatusRes.status === 'fulfilled' && marketStatusRes.value.ok) {
                const marketData = await marketStatusRes.value.json();
                if (marketData.success) {
                    setMarketStatus(marketData.data);
                } else {
                    throw new Error('Failed to fetch market status');
                }
            } else {
                // Fallback market status
                setMarketStatus({
                    is_market_open: false,
                    time_to_close_seconds: 0,
                    session_type: 'CLOSED'
                });
            }

            // Process session stats
            if (sessionStatsRes.status === 'fulfilled' && sessionStatsRes.value.ok) {
                const sessionData = await sessionStatsRes.value.json();
                if (sessionData.success) {
                    setSessionStats(sessionData.data);
                } else {
                    throw new Error('Failed to fetch session stats');
                }
            } else {
                // Fallback session stats
                setSessionStats(null);
            }

            // Process active positions
            if (positionsRes.status === 'fulfilled' && positionsRes.value.ok) {
                const positionsData = await positionsRes.value.json();
                if (positionsData.success) {
                    setActivePositions(positionsData.data || []);
                } else {
                    throw new Error('Failed to fetch positions');
                }
            } else {
                setActivePositions([]);
            }

            // Process scheduler status
            if (schedulerRes.status === 'fulfilled' && schedulerRes.value.ok) {
                const schedulerData = await schedulerRes.value.json();
                if (schedulerData.success) {
                    setSchedulerStatus(schedulerData.data);
                } else {
                    throw new Error('Failed to fetch scheduler status');
                }
            } else {
                // Fallback scheduler status
                setSchedulerStatus(null);
            }

            setError(null);
        } catch (err) {
            console.error('Error fetching autonomous trading data:', err);
            setError('Failed to load autonomous trading data. Please check your connection.');

            // Set empty states in case of complete failure
            setMarketStatus(null);
            setSessionStats(null);
            setActivePositions([]);
            setSchedulerStatus(null);
        } finally {
            setLoading(false);
        }
    };

    const fetchTradingStatus = async () => {
        try {
            const response = await fetch(API_ENDPOINTS.BROKER_STATUS);
            const data = await response.json();
            if (data.success) {
                setTradingStatus(data);
            }
        } catch (err) {
            console.error('Error fetching trading status:', err);
        }
    };

    const fetchBrokerUsers = async () => {
        try {
            const response = await fetch(API_ENDPOINTS.USERS);
            const data = await response.json();
            if (data.success) {
                setBrokerUsers(data.users || []);
            }
        } catch (err) {
            console.error('Error fetching broker users:', err);
        }
    };

    const handleTradingControl = async (action) => {
        setControlLoading(true);
        try {
            const response = await fetch(API_ENDPOINTS.BROKER_CONNECT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: action,
                    paper_trading: true
                })
            });

            const data = await response.json();

            if (data.success) {
                alert(`Trading ${action}ed successfully!`);
                fetchTradingStatus();
                fetchAutonomousData();
            } else {
                alert(data.message || `Failed to ${action} trading`);
            }
        } catch (err) {
            console.error(`Error ${action}ing trading:`, err);
            alert(`Failed to ${action} trading. Please try again.`);
        } finally {
            setControlLoading(false);
        }
    };

    const handleUserAdded = (user) => {
        fetchBrokerUsers();
        fetchTradingStatus();
        // Optionally start trading automatically after adding user
        if (brokerUsers.length === 0) {
            handleTradingControl('start');
        }
    };

    const handleEmergencyStop = async () => {
        try {
            const token = localStorage.getItem('auth_token');
            const headers = {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` })
            };

            const response = await fetch(API_ENDPOINTS.BROKER_DISCONNECT, {
                method: 'POST',
                headers
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Emergency stop failed');
            }

            const data = await response.json();

            if (data.success) {
                alert('Emergency stop activated successfully - All autonomous trading has been halted');
                // Refresh the data to show updated status
                fetchAutonomousData();
            } else {
                throw new Error(data.message || 'Emergency stop failed');
            }
        } catch (err) {
            console.error('Emergency stop failed:', err);
            alert(`Emergency stop failed: ${err.message}`);
        }
    };

    const formatCurrency = (value) => `₹${value.toLocaleString()}`;
    const formatTime = (seconds) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    };

    if (loading) {
        return (
            <Box sx={{ p: 3 }}>
                <Typography variant="h6">Loading Autonomous Trading Data...</Typography>
                <LinearProgress sx={{ mt: 2 }} />
            </Box>
        );
    }

    return (
        <Grid container spacing={3}>
            {error && (
                <Grid item xs={12}>
                    <Alert severity="info">{error}</Alert>
                </Grid>
            )}

            {/* Trading Control Section */}
            <Grid item xs={12}>
                <Card>
                    <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                            <Typography variant="h6">
                                Trading Control Center
                            </Typography>
                            {brokerUsers.length === 0 && (
                                <Button
                                    variant="contained"
                                    startIcon={<PersonAdd />}
                                    onClick={() => setShowBrokerSetup(true)}
                                    color="primary"
                                >
                                    Add Broker User
                                </Button>
                            )}
                        </Box>

                        {brokerUsers.length === 0 ? (
                            <Alert severity="warning">
                                No broker users configured. Please add your Zerodha credentials to start paper trading.
                            </Alert>
                        ) : (
                            <Box>
                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    Active Broker Users: {brokerUsers.length}
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                                    {tradingStatus?.is_running ? (
                                        <Button
                                            variant="contained"
                                            color="error"
                                            startIcon={<Stop />}
                                            onClick={() => handleTradingControl('stop')}
                                            disabled={controlLoading}
                                        >
                                            Stop Trading
                                        </Button>
                                    ) : (
                                        <Button
                                            variant="contained"
                                            color="success"
                                            startIcon={<PlayArrow />}
                                            onClick={() => handleTradingControl('start')}
                                            disabled={controlLoading}
                                        >
                                            Start Trading
                                        </Button>
                                    )}
                                    <Chip
                                        label={tradingStatus?.is_running ? "Trading Active" : "Trading Stopped"}
                                        color={tradingStatus?.is_running ? "success" : "default"}
                                        variant="outlined"
                                    />
                                    {tradingStatus?.paper_trading && (
                                        <Chip
                                            label="Paper Trading Mode"
                                            color="info"
                                            variant="outlined"
                                        />
                                    )}
                                </Box>
                            </Box>
                        )}
                    </CardContent>
                </Card>
            </Grid>

            {/* Header Status */}
            <Grid item xs={12}>
                <Card sx={{ background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)', color: 'white' }}>
                    <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Box>
                                <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
                                    🤖 Autonomous Trading System
                                </Typography>
                                <Typography variant="subtitle1" sx={{ opacity: 0.9 }}>
                                    Zero Human Intervention • Market Open to Close Automation
                                </Typography>
                            </Box>
                            <Box sx={{ textAlign: 'right' }}>
                                <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                                    <Chip
                                        label={marketStatus?.is_market_open ? "Market OPEN" : "Market CLOSED"}
                                        color={marketStatus?.is_market_open ? "success" : "error"}
                                        variant="filled"
                                    />
                                    <Chip
                                        label={tradingStatus?.is_running ? "Auto Trading ACTIVE" : "Auto Trading STOPPED"}
                                        color={tradingStatus?.is_running ? "primary" : "default"}
                                        variant="filled"
                                    />
                                </Box>
                                <Typography variant="body2" sx={{ opacity: 0.8 }}>
                                    {marketStatus?.time_to_close_seconds &&
                                        `Market closes in ${formatTime(marketStatus.time_to_close_seconds)}`
                                    }
                                </Typography>
                            </Box>
                        </Box>
                    </CardContent>
                </Card>
            </Grid>

            {/* Session Performance */}
            <Grid item xs={12} md={6}>
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            <TrendingUp sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Session Performance
                        </Typography>
                        <Grid container spacing={2}>
                            <Grid item xs={6}>
                                <Typography variant="body2" color="text.secondary">Total Trades</Typography>
                                <Typography variant="h5">{sessionStats?.total_trades}</Typography>
                            </Grid>
                            <Grid item xs={6}>
                                <Typography variant="body2" color="text.secondary">Success Rate</Typography>
                                <Typography variant="h5" color="success.main">
                                    {sessionStats?.success_rate}%
                                </Typography>
                            </Grid>
                            <Grid item xs={6}>
                                <Typography variant="body2" color="text.secondary">Total P&L</Typography>
                                <Typography variant="h5" color="success.main">
                                    {formatCurrency(sessionStats?.total_pnl || 0)}
                                </Typography>
                            </Grid>
                            <Grid item xs={6}>
                                <Typography variant="body2" color="text.secondary">Max Drawdown</Typography>
                                <Typography variant="h5" color="warning.main">
                                    {sessionStats?.max_drawdown}%
                                </Typography>
                            </Grid>
                        </Grid>
                    </CardContent>
                </Card>
            </Grid>

            {/* Active Strategies */}
            <Grid item xs={12} md={6}>
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            <SmartToy sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Active Strategies
                        </Typography>
                        <List dense>
                            {Object.entries(sessionStats?.strategies_active || {}).map(([strategy, data], index) => (
                                <ListItem key={index} sx={{ px: 0 }}>
                                    <ListItemAvatar>
                                        <Avatar sx={{
                                            bgcolor: ['success.main', 'warning.main', 'info.main', 'secondary.main'][index % 4],
                                            width: 32, height: 32, fontSize: '0.875rem'
                                        }}>
                                            {strategy.split('_').map(word => word[0]).join('').toUpperCase()}
                                        </Avatar>
                                    </ListItemAvatar>
                                    <ListItemText
                                        primary={strategy.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                        secondary={`${data.trades} trades • ${formatCurrency(data.pnl)} P&L`}
                                    />
                                    <Chip label="ACTIVE" color="success" size="small" />
                                </ListItem>
                            ))}
                        </List>
                    </CardContent>
                </Card>
            </Grid>

            {/* Auto-Managed Positions */}
            <Grid item xs={12} md={6}>
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>Auto-Managed Positions</Typography>
                        <List dense>
                            {activePositions.map((position, index) => (
                                <ListItem key={index} sx={{ px: 0 }}>
                                    <ListItemAvatar>
                                        <Avatar sx={{ bgcolor: position.unrealized_pnl > 0 ? 'success.main' : 'error.main' }}>
                                            {position.symbol[0]}
                                        </Avatar>
                                    </ListItemAvatar>
                                    <ListItemText
                                        primary={position.symbol}
                                        secondary={
                                            <Box>
                                                <Typography variant="body2">
                                                    ₹{position.entry_price} → ₹{position.current_price}
                                                </Typography>
                                                <Typography
                                                    variant="body2"
                                                    color={position.unrealized_pnl > 0 ? 'success.main' : 'error.main'}
                                                >
                                                    P&L: {formatCurrency(position.unrealized_pnl)}
                                                    {position.trailing_stop && ' • Trailing Stop'}
                                                </Typography>
                                            </Box>
                                        }
                                    />
                                </ListItem>
                            ))}
                        </List>
                    </CardContent>
                </Card>
            </Grid>

            {/* Autonomous Actions */}
            <Grid item xs={12} md={6}>
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>Autonomous Actions</Typography>
                        <Grid container spacing={2}>
                            <Grid item xs={6}>
                                <Typography variant="body2" color="text.secondary">Opened</Typography>
                                <Typography variant="h6" color="primary.main">
                                    {sessionStats?.auto_actions?.positions_opened}
                                </Typography>
                            </Grid>
                            <Grid item xs={6}>
                                <Typography variant="body2" color="text.secondary">Closed</Typography>
                                <Typography variant="h6" color="secondary.main">
                                    {sessionStats?.auto_actions?.positions_closed}
                                </Typography>
                            </Grid>
                            <Grid item xs={6}>
                                <Typography variant="body2" color="text.secondary">Stop Losses</Typography>
                                <Typography variant="h6" color="error.main">
                                    {sessionStats?.auto_actions?.stop_losses_triggered}
                                </Typography>
                            </Grid>
                            <Grid item xs={6}>
                                <Typography variant="body2" color="text.secondary">Targets Hit</Typography>
                                <Typography variant="h6" color="success.main">
                                    {sessionStats?.auto_actions?.targets_hit}
                                </Typography>
                            </Grid>
                        </Grid>
                    </CardContent>
                </Card>
            </Grid>

            {/* Trading Scheduler */}
            <Grid item xs={12}>
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            <Schedule sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Autonomous Trading Scheduler
                        </Typography>

                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                            <Chip
                                label="Scheduler ACTIVE"
                                color="success"
                                icon={<CheckCircle />}
                            />
                            <Chip
                                label="Auto-Start ENABLED"
                                color="primary"
                                icon={<PlayArrow />}
                            />
                            <Chip
                                label="Auto-Stop ENABLED"
                                color="primary"
                                icon={<Stop />}
                            />
                        </Box>

                        <Typography variant="subtitle2" gutterBottom>Today's Schedule:</Typography>
                        <List dense>
                            {schedulerStatus?.scheduled_events?.map((event, index) => (
                                <ListItem key={index} sx={{ px: 0 }}>
                                    <ListItemAvatar>
                                        <Avatar sx={{
                                            bgcolor: event.status === 'COMPLETED' ? 'success.main' : 'grey.400',
                                            width: 32, height: 32
                                        }}>
                                            {event.status === 'COMPLETED' ? <CheckCircle sx={{ fontSize: 16 }} /> : <Schedule sx={{ fontSize: 16 }} />}
                                        </Avatar>
                                    </ListItemAvatar>
                                    <ListItemText
                                        primary={`${event.time} - ${event.event}`}
                                        secondary={`Status: ${event.status}`}
                                    />
                                </ListItem>
                            ))}
                        </List>

                        <Divider sx={{ my: 2 }} />

                        <Typography variant="subtitle2" gutterBottom>Emergency Controls:</Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            <Button
                                variant="outlined"
                                color="error"
                                size="small"
                                startIcon={<Warning />}
                                onClick={handleEmergencyStop}
                                disabled={!userInfo || userInfo.role !== 'admin'}
                            >
                                Emergency Stop
                            </Button>
                            <Button
                                variant="outlined"
                                color="warning"
                                size="small"
                                startIcon={<Pause />}
                                disabled={!userInfo || userInfo.role !== 'admin'}
                            >
                                Pause Trading
                            </Button>
                            <Button
                                variant="outlined"
                                size="small"
                                disabled={!userInfo || userInfo.role !== 'admin'}
                            >
                                View Logs
                            </Button>
                        </Box>

                        {(!userInfo || userInfo.role !== 'admin') && (
                            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                                Admin privileges required for system controls
                            </Typography>
                        )}
                    </CardContent>
                </Card>
            </Grid>

            {/* Broker User Setup Dialog */}
            <BrokerUserSetup
                open={showBrokerSetup}
                onClose={() => setShowBrokerSetup(false)}
                onUserAdded={handleUserAdded}
            />
        </Grid>
    );
};

export default AutonomousTradingDashboard; 