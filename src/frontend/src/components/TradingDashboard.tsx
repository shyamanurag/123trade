import axios from 'axios';
import React, { useEffect, useState } from 'react';

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

interface MarketIndex {
    symbol: string;
    ltp: number;
    change_percent: number;
}

const TradingDashboard: React.FC = () => {
    const [trades, setTrades] = useState<Trade[]>([]);
    const [userMetrics, setUserMetrics] = useState<Record<string, UserMetrics>>({});
    const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([]);
    const [loading, setLoading] = useState(true);
    const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

    const fetchData = async () => {
        try {
            setLoading(true);

            // Fetch live trades
            const tradesResponse = await axios.get('/api/trades/live');
            setTrades(tradesResponse.data.data || []);

            // Fetch user metrics
            const metricsResponse = await axios.get('/api/users/metrics');
            setUserMetrics(metricsResponse.data.data || {});

            // Fetch market indices
            const indicesResponse = await axios.get('/api/indices');
            setMarketIndices(indicesResponse.data.data || []);

            setLastUpdated(new Date());
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000); // Update every 5 seconds
        return () => clearInterval(interval);
    }, []);

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 2,
        }).format(value);
    };

    const formatPercentage = (value: number) => {
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    };

    return (
        <div className="min-h-screen bg-gray-100 p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex justify-between items-center">
                        <h1 className="text-3xl font-bold text-gray-800">ShareKhan Trading Dashboard</h1>
                        <div className="flex items-center space-x-4">
                            <button
                                onClick={fetchData}
                                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                                disabled={loading}
                            >
                                {loading ? 'Refreshing...' : 'Refresh'}
                            </button>
                            <span className="text-sm text-gray-600">
                                Last updated: {lastUpdated.toLocaleTimeString()}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Market Indices */}
                <div className="mb-8">
                    <h2 className="text-xl font-semibold text-gray-800 mb-4">Market Indices</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {marketIndices.map((index) => (
                            <div key={index.symbol} className="bg-white rounded-lg shadow p-6">
                                <h3 className="text-lg font-medium text-gray-800">{index.symbol}</h3>
                                <div className="mt-2">
                                    <span className="text-2xl font-bold text-gray-900">{index.ltp.toLocaleString()}</span>
                                    <span className={`ml-2 text-sm font-medium ${index.change_percent >= 0 ? 'text-green-600' : 'text-red-600'
                                        }`}>
                                        {formatPercentage(index.change_percent)}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* User Metrics */}
                <div className="mb-8">
                    <h2 className="text-xl font-semibold text-gray-800 mb-4">User Metrics</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {Object.values(userMetrics).map((metrics) => (
                            <div key={metrics.user_id} className="bg-white rounded-lg shadow p-6">
                                <h3 className="text-lg font-medium text-gray-800 mb-2">{metrics.user_id}</h3>
                                <div className="space-y-2">
                                    <div>
                                        <span className="text-sm text-gray-600">Current Capital</span>
                                        <div className="text-xl font-bold text-gray-900">
                                            {formatCurrency(metrics.current_capital)}
                                        </div>
                                    </div>
                                    <div>
                                        <span className="text-sm text-gray-600">Daily P&L</span>
                                        <div className={`text-lg font-semibold ${metrics.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                            }`}>
                                            {formatCurrency(metrics.daily_pnl)}
                                            <span className="ml-1 text-sm">
                                                ({formatPercentage(metrics.daily_pnl_percentage)})
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-sm text-gray-600">Open Trades: {metrics.open_trades}</span>
                                        {metrics.hard_stop_status && (
                                            <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">
                                                HARD STOP
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Live Trades */}
                <div>
                    <h2 className="text-xl font-semibold text-gray-800 mb-4">Live Trades</h2>
                    <div className="bg-white rounded-lg shadow overflow-hidden">
                        {loading ? (
                            <div className="flex justify-center items-center h-32">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                            </div>
                        ) : trades.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">
                                No active trades
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Symbol
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                User
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Quantity
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Entry Price
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Current Price
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                P&L
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Status
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Time
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {trades.map((trade) => (
                                            <tr key={trade.trade_id} className="hover:bg-gray-50">
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                    {trade.symbol}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {trade.user_id}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {trade.quantity}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {formatCurrency(trade.entry_price)}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {formatCurrency(trade.current_price)}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                    <span className={`font-medium ${trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                                        }`}>
                                                        {formatCurrency(trade.pnl)}
                                                        <span className="ml-1">({formatPercentage(trade.pnl_percentage)})</span>
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${trade.status === 'OPEN'
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-gray-100 text-gray-800'
                                                        }`}>
                                                        {trade.status}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {new Date(trade.timestamp).toLocaleTimeString()}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TradingDashboard; 