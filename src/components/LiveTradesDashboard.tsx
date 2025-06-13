import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import { Refresh as RefreshIcon, TrendingUp, TrendingDown } from '@mui/icons-material';
import { format } from 'date-fns';

interface Trade {
  trade_id: string;
  user_id: string;
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percentage: number;
  timestamp: string;
  status: 'OPEN' | 'CLOSED';
}

interface UserMetrics {
  user_id: string;
  current_capital: number;
  opening_capital: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  open_trades: number;
  hard_stop_status: boolean;
}

const LiveTradesDashboard: React.FC = () => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [userMetrics, setUserMetrics] = useState<Record<string, UserMetrics>>({});
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      setLoading(true);
      // Fetch trades
      const tradesResponse = await fetch('/api/trades/live');
      const tradesData = await tradesResponse.json();
      setTrades(tradesData);

      // Fetch user metrics
      const metricsResponse = await fetch('/api/users/metrics');
      const metricsData = await metricsResponse.json();
      setUserMetrics(metricsData);

      setLastUpdated(new Date());
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Set up WebSocket connection for real-time updates
    const ws = new WebSocket(process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws');

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'TRADE_UPDATE') {
        setTrades(prevTrades => {
          const updatedTrades = [...prevTrades];
          const index = updatedTrades.findIndex(t => t.trade_id === data.trade.trade_id);
          if (index >= 0) {
            updatedTrades[index] = data.trade;
          } else {
            updatedTrades.push(data.trade);
          }
          return updatedTrades;
        });
      } else if (data.type === 'USER_METRICS_UPDATE') {
        setUserMetrics(prevMetrics => ({
          ...prevMetrics,
          [data.user_id]: data.metrics
        }));
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Live Trading Dashboard
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Last updated: {format(lastUpdated, 'HH:mm:ss')}
          </Typography>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchData} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* User Metrics Summary */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>User Performance Summary</Typography>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>User ID</TableCell>
                    <TableCell align="right">Current Capital</TableCell>
                    <TableCell align="right">Opening Capital</TableCell>
                    <TableCell align="right">Daily P&L</TableCell>
                    <TableCell align="right">Daily P&L %</TableCell>
                    <TableCell align="right">Open Trades</TableCell>
                    <TableCell align="center">Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(userMetrics).map(([userId, metrics]) => (
                    <TableRow key={userId}>
                      <TableCell>{userId}</TableCell>
                      <TableCell align="right">{formatCurrency(metrics.current_capital)}</TableCell>
                      <TableCell align="right">{formatCurrency(metrics.opening_capital)}</TableCell>
                      <TableCell 
                        align="right"
                        sx={{ 
                          color: metrics.daily_pnl >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 'bold'
                        }}
                      >
                        {formatCurrency(metrics.daily_pnl)}
                      </TableCell>
                      <TableCell 
                        align="right"
                        sx={{ 
                          color: metrics.daily_pnl_percentage >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 'bold'
                        }}
                      >
                        {formatPercentage(metrics.daily_pnl_percentage)}
                      </TableCell>
                      <TableCell align="right">{metrics.open_trades}</TableCell>
                      <TableCell align="center">
                        <Chip
                          label={metrics.hard_stop_status ? 'STOPPED' : 'ACTIVE'}
                          color={metrics.hard_stop_status ? 'error' : 'success'}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>

          {/* Live Trades Table */}
          <Box>
            <Typography variant="h6" sx={{ mb: 2 }}>Live Trades</Typography>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Trade ID</TableCell>
                    <TableCell>User ID</TableCell>
                    <TableCell>Symbol</TableCell>
                    <TableCell align="right">Quantity</TableCell>
                    <TableCell align="right">Entry Price</TableCell>
                    <TableCell align="right">Current Price</TableCell>
                    <TableCell align="right">P&L</TableCell>
                    <TableCell align="right">P&L %</TableCell>
                    <TableCell align="center">Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {trades.map((trade) => (
                    <TableRow key={trade.trade_id}>
                      <TableCell>{trade.trade_id}</TableCell>
                      <TableCell>{trade.user_id}</TableCell>
                      <TableCell>{trade.symbol}</TableCell>
                      <TableCell align="right">{trade.quantity}</TableCell>
                      <TableCell align="right">{formatCurrency(trade.entry_price)}</TableCell>
                      <TableCell align="right">{formatCurrency(trade.current_price)}</TableCell>
                      <TableCell 
                        align="right"
                        sx={{ 
                          color: trade.pnl >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 'bold'
                        }}
                      >
                        {formatCurrency(trade.pnl)}
                      </TableCell>
                      <TableCell 
                        align="right"
                        sx={{ 
                          color: trade.pnl_percentage >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 'bold'
                        }}
                      >
                        {formatPercentage(trade.pnl_percentage)}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={trade.status}
                          color={trade.status === 'OPEN' ? 'primary' : 'default'}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </>
      )}
    </Box>
  );
};

export default LiveTradesDashboard; 