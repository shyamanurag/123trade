import {
    CheckCircle,
    Error,
    Memory,
    NetworkCheck,
    Storage,
    Warning
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Card,
    CardContent,
    Chip,
    Grid,
    LinearProgress,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const SystemHealthMonitor = () => {
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchHealthData = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/health/ready`);

            if (response.ok) {
                const data = await response.json();
                setHealthData(data);
                setError(null);
            } else {
                throw new Error('Failed to fetch health data');
            }
        } catch (err) {
            console.error('Health data fetch error:', err);
            setError('Unable to fetch system health data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHealthData();
        // Refresh health data every 2 minutes to reduce UI interruptions
        const interval = setInterval(fetchHealthData, 120000); // 120 000 ms = 2 minutes
        return () => clearInterval(interval);
    }, []);

    const getStatusIcon = (status) => {
        switch (status?.toLowerCase()) {
            case 'healthy':
            case 'pass':
                return <CheckCircle color="success" />;
            case 'warning':
            case 'partial':
                return <Warning color="warning" />;
            case 'unhealthy':
            case 'fail':
                return <Error color="error" />;
            default:
                return <Warning color="disabled" />;
        }
    };

    const getStatusColor = (status) => {
        switch (status?.toLowerCase()) {
            case 'healthy':
            case 'pass':
                return 'success';
            case 'warning':
            case 'partial':
                return 'warning';
            case 'unhealthy':
            case 'fail':
                return 'error';
            default:
                return 'default';
        }
    };

    if (loading) {
        return (
            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        System Health
                    </Typography>
                    <LinearProgress />
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        System Health
                    </Typography>
                    <Alert severity="error">{error}</Alert>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        System Health Monitor
                    </Typography>
                    <Chip
                        label={healthData?.status || 'Unknown'}
                        color={getStatusColor(healthData?.status)}
                        icon={getStatusIcon(healthData?.status)}
                        size="small"
                    />
                </Box>

                <Grid container spacing={2}>
                    {/* Overall System Status */}
                    <Grid item xs={12}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                            {getStatusIcon(healthData?.status)}
                            <Typography variant="body1" sx={{ ml: 1 }}>
                                Overall System: {healthData?.status || 'Unknown'}
                            </Typography>
                        </Box>
                    </Grid>

                    {/* Component Health */}
                    {healthData?.components && Object.entries(healthData.components).map(([component, data]) => (
                        <Grid item xs={12} sm={6} key={component}>
                            <Box sx={{ display: 'flex', alignItems: 'center', p: 1, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                                {getStatusIcon(data.status)}
                                <Box sx={{ ml: 1, flexGrow: 1 }}>
                                    <Typography variant="body2" fontWeight="bold">
                                        {component.replace('_', ' ').toUpperCase()}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {data.message || 'No details available'}
                                    </Typography>
                                </Box>
                                <Chip
                                    label={data.status}
                                    color={getStatusColor(data.status)}
                                    size="small"
                                />
                            </Box>
                        </Grid>
                    ))}

                    {/* System Metrics */}
                    {healthData?.metrics && (
                        <Grid item xs={12}>
                            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                                System Metrics
                            </Typography>
                            <Grid container spacing={1}>
                                {healthData.metrics.memory_usage && (
                                    <Grid item xs={4}>
                                        <Box sx={{ textAlign: 'center' }}>
                                            <Memory color="primary" />
                                            <Typography variant="caption" display="block">
                                                Memory: {healthData.metrics.memory_usage}%
                                            </Typography>
                                        </Box>
                                    </Grid>
                                )}
                                {healthData.metrics.disk_usage && (
                                    <Grid item xs={4}>
                                        <Box sx={{ textAlign: 'center' }}>
                                            <Storage color="primary" />
                                            <Typography variant="caption" display="block">
                                                Disk: {healthData.metrics.disk_usage}%
                                            </Typography>
                                        </Box>
                                    </Grid>
                                )}
                                {healthData.metrics.uptime && (
                                    <Grid item xs={4}>
                                        <Box sx={{ textAlign: 'center' }}>
                                            <NetworkCheck color="primary" />
                                            <Typography variant="caption" display="block">
                                                Uptime: {healthData.metrics.uptime}
                                            </Typography>
                                        </Box>
                                    </Grid>
                                )}
                            </Grid>
                        </Grid>
                    )}
                </Grid>

                <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                    Last updated: {new Date().toLocaleTimeString()}
                </Typography>
            </CardContent>
        </Card>
    );
};

export default SystemHealthMonitor;