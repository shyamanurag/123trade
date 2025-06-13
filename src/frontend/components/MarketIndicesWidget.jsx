import {
    AccessTime,
    Refresh,
    TrendingDown,
    TrendingUp
} from '@mui/icons-material';
import {
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    Grid,
    IconButton,
    LinearProgress,
    Tooltip,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const MarketIndicesWidget = () => {
    const [indices, setIndices] = useState([]);
    const [marketStatus, setMarketStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [lastUpdate, setLastUpdate] = useState(null);
    const [error, setError] = useState(null);

    const fetchMarketData = async () => {
        try {
            setError(null);
            // Don't set loading to true on refresh to avoid flicker
            if (indices.length === 0) {
                setLoading(true);
            }

            // Fetch indices data
            const indicesResponse = await fetch(`${API_BASE_URL}/market/indices`);
            const indicesData = await indicesResponse.json();

            // Fetch market status
            const statusResponse = await fetch(`${API_BASE_URL}/market/market-status`);
            const statusData = await statusResponse.json();

            if (indicesData.success) {
                setIndices(indicesData.indices || []);
            } else {
                setError('Unable to fetch market data');
            }

            if (statusData.success) {
                setMarketStatus(statusData);
            }

            setLastUpdate(new Date());
        } catch (error) {
            console.error('Error fetching market data:', error);
            setError('Failed to connect to market data service');
            // Don't set any mock data - keep indices empty
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMarketData();
        // Auto-refresh every 2 minutes to reduce strain and avoid interrupting user actions
        const interval = setInterval(fetchMarketData, 120000); // 120 000 ms = 2 minutes
        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status) => {
        switch (status) {
            case 'OPEN': return 'success';
            case 'PRE_OPEN': return 'warning';
            case 'CLOSED': return 'error';
            default: return 'default';
        }
    };

    const formatNumber = (num) => {
        return new Intl.NumberFormat('en-IN').format(num);
    };

    const formatPercent = (num) => {
        const sign = num >= 0 ? '+' : '';
        return `${sign}${num.toFixed(2)}%`;
    };

    return (
        <Card sx={{ height: '100%', position: 'relative' }}>
            <CardContent>
                {/* Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Box>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            Market Indices
                        </Typography>
                        {marketStatus && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                                <Chip
                                    label={marketStatus.market_status}
                                    color={getStatusColor(marketStatus.market_status)}
                                    size="small"
                                />
                                <Typography variant="caption" color="text.secondary">
                                    {marketStatus.current_time}
                                </Typography>
                            </Box>
                        )}
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {lastUpdate && (
                            <Tooltip title={`Last updated: ${lastUpdate.toLocaleTimeString()}`}>
                                <AccessTime sx={{ fontSize: 16, color: 'text.secondary' }} />
                            </Tooltip>
                        )}
                        <IconButton size="small" onClick={fetchMarketData} disabled={loading}>
                            <Refresh />
                        </IconButton>
                    </Box>
                </Box>

                {/* Loading State */}
                {loading && indices.length === 0 && (
                    <Box sx={{ py: 4 }}>
                        <LinearProgress />
                        <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 2 }}>
                            Loading market data...
                        </Typography>
                    </Box>
                )}

                {/* Error State */}
                {error && !loading && (
                    <Box sx={{ py: 2, textAlign: 'center' }}>
                        <Typography variant="body2" color="error" sx={{ mb: 1 }}>
                            {error}
                        </Typography>
                        <Button size="small" onClick={fetchMarketData} startIcon={<Refresh />}>
                            Retry
                        </Button>
                    </Box>
                )}

                {/* Indices Grid */}
                <Grid container spacing={2}>
                    {indices.map((index) => (
                        <Grid item xs={12} key={index.symbol}>
                            <Box
                                sx={{
                                    p: 2,
                                    borderRadius: 2,
                                    bgcolor: 'background.default',
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    transition: 'all 0.3s ease',
                                    '&:hover': {
                                        borderColor: 'primary.main',
                                        transform: 'translateY(-2px)',
                                        boxShadow: 1
                                    }
                                }}
                            >
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                                    <Box>
                                        <Typography variant="subtitle2" color="text.secondary">
                                            {index.name}
                                        </Typography>
                                        <Typography variant="h5" sx={{ fontWeight: 600, mt: 0.5 }}>
                                            {formatNumber(index.last_price)}
                                        </Typography>
                                    </Box>
                                    <Box sx={{ textAlign: 'right' }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                            {index.change >= 0 ? (
                                                <TrendingUp sx={{ color: 'success.main', fontSize: 20 }} />
                                            ) : (
                                                <TrendingDown sx={{ color: 'error.main', fontSize: 20 }} />
                                            )}
                                            <Typography
                                                variant="body1"
                                                sx={{
                                                    fontWeight: 600,
                                                    color: index.change >= 0 ? 'success.main' : 'error.main'
                                                }}
                                            >
                                                {formatNumber(Math.abs(index.change))}
                                            </Typography>
                                        </Box>
                                        <Typography
                                            variant="body2"
                                            sx={{
                                                color: index.change >= 0 ? 'success.main' : 'error.main'
                                            }}
                                        >
                                            {formatPercent(index.change_percent)}
                                        </Typography>
                                    </Box>
                                </Box>

                                {/* Mini Stats */}
                                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">
                                            Open
                                        </Typography>
                                        <Typography variant="body2">
                                            {formatNumber(index.open)}
                                        </Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">
                                            High
                                        </Typography>
                                        <Typography variant="body2" color="success.main">
                                            {formatNumber(index.high)}
                                        </Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">
                                            Low
                                        </Typography>
                                        <Typography variant="body2" color="error.main">
                                            {formatNumber(index.low)}
                                        </Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">
                                            Volume
                                        </Typography>
                                        <Typography variant="body2">
                                            {(index.volume / 10000000).toFixed(1)}Cr
                                        </Typography>
                                    </Box>
                                </Box>
                            </Box>
                        </Grid>
                    ))}
                </Grid>

                {/* Market Status Footer */}
                {marketStatus && marketStatus.data_provider && (
                    <Box sx={{ mt: 3, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="caption" color="text.secondary">
                                Data Provider: {marketStatus.data_provider.name}
                            </Typography>
                            <Chip
                                label={marketStatus.data_provider.status}
                                color={marketStatus.data_provider.status === 'CONNECTED' ? 'success' : 'default'}
                                size="small"
                                variant="outlined"
                            />
                        </Box>
                    </Box>
                )}
            </CardContent>
        </Card>
    );
};

export default MarketIndicesWidget; 