import {
    Alert,
    Box,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Container,
    Grid,
    List,
    ListItem,
    ListItemText,
    Paper,
    Typography
} from '@mui/material';
import axios from 'axios';
import React, { useEffect, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const TradingDashboard = () => {
    const [healthStatus, setHealthStatus] = useState(null);
    const [marketData, setMarketData] = useState([]);
    const [recommendations, setRecommendations] = useState([]);
    const [riskMetrics, setRiskMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);

                // Fetch health status
                const healthResponse = await axios.get(`${API_BASE_URL}/health`);
                setHealthStatus(healthResponse.data);

                // Fetch market data
                const marketResponse = await axios.get(`${API_BASE_URL}/api/market/data?symbol=AAPL`);
                if (marketResponse.data.success) {
                    setMarketData(marketResponse.data.data);
                }

                // Fetch recommendations
                const recommendationsResponse = await axios.get(`${API_BASE_URL}/api/recommendations/analysis?symbol=AAPL`);
                if (recommendationsResponse.data.success) {
                    setRecommendations([recommendationsResponse.data]);
                }

                // Fetch risk metrics
                const riskResponse = await axios.get(`${API_BASE_URL}/api/risk/metrics`);
                if (riskResponse.data.success) {
                    setRiskMetrics(riskResponse.data.data);
                }

                setError(null);
            } catch (err) {
                console.error('Error fetching data:', err);
                setError('Failed to fetch trading data');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        // Remove automatic refresh - data will be fetched on demand
    }, []);

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                <CircularProgress />
            </Box>
        );
    }

    const getHealthColor = (status) => {
        if (!status) return 'default';
        if (status.status === 'ok') return 'success';
        return 'error';
    };

    return (
        <Container maxWidth="xl" sx={{ mt: 2, mb: 2 }}>
            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
            )}

            {/* Header */}
            <Paper sx={{ p: 2, mb: 2 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} md={6}>
                        <Typography variant="h4" component="h1">
                            Trading System Dashboard
                        </Typography>
                        <Typography variant="subtitle1" color="text.secondary">
                            Real-time market analysis and recommendations
                        </Typography>
                    </Grid>
                    <Grid item xs={12} md={6} textAlign="right">
                        <Chip
                            label={healthStatus ? `System ${healthStatus.status}` : 'System Status Unknown'}
                            color={getHealthColor(healthStatus)}
                            sx={{ mr: 1 }}
                        />
                        {healthStatus && (
                            <Typography variant="caption" display="block">
                                Last updated: {new Date(healthStatus.timestamp).toLocaleTimeString()}
                            </Typography>
                        )}
                    </Grid>
                </Grid>
            </Paper>

            <Grid container spacing={3}>
                {/* Market Data Chart */}
                <Grid item xs={12} lg={8}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Market Data
                            </Typography>
                            {marketData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={300}>
                                    <LineChart data={marketData}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis dataKey="timestamp" />
                                        <YAxis />
                                        <Tooltip />
                                        <Line type="monotone" dataKey="price" stroke="#2196f3" strokeWidth={2} />
                                    </LineChart>
                                </ResponsiveContainer>
                            ) : (
                                <Box textAlign="center" py={4}>
                                    <Typography color="text.secondary">
                                        No market data available
                                    </Typography>
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Risk Metrics */}
                <Grid item xs={12} lg={4}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Risk Metrics
                            </Typography>
                            {riskMetrics ? (
                                <List dense>
                                    <ListItem>
                                        <ListItemText
                                            primary="Max Drawdown"
                                            secondary={`${(riskMetrics.max_drawdown * 100).toFixed(2)}%`}
                                        />
                                    </ListItem>
                                    <ListItem>
                                        <ListItemText
                                            primary="Risk Score"
                                            secondary={riskMetrics.risk_score}
                                        />
                                    </ListItem>
                                    <ListItem>
                                        <ListItemText
                                            primary="Position Size"
                                            secondary={`$${riskMetrics.position_size.toLocaleString()}`}
                                        />
                                    </ListItem>
                                </List>
                            ) : (
                                <Typography color="text.secondary">
                                    No risk data available
                                </Typography>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Recommendations */}
                <Grid item xs={12}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Trading Recommendations
                            </Typography>
                            {recommendations.length > 0 ? (
                                <Grid container spacing={2}>
                                    {recommendations.map((rec, index) => (
                                        <Grid item xs={12} md={4} key={index}>
                                            <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                                                <Typography variant="subtitle1" gutterBottom>
                                                    {rec.symbol}
                                                </Typography>
                                                <Chip
                                                    label={rec.recommendation}
                                                    color={rec.recommendation === 'BUY' ? 'success' :
                                                        rec.recommendation === 'SELL' ? 'error' : 'default'}
                                                    sx={{ mb: 1 }}
                                                />
                                                <Typography variant="body2" color="text.secondary">
                                                    Confidence: {(rec.confidence * 100).toFixed(1)}%
                                                </Typography>
                                                <Typography variant="body2" color="text.secondary">
                                                    {rec.analysis}
                                                </Typography>
                                            </Paper>
                                        </Grid>
                                    ))}
                                </Grid>
                            ) : (
                                <Typography color="text.secondary">
                                    No recommendations available
                                </Typography>
                            )}
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Container>
    );
};

export default TradingDashboard; 