import { ArrowTrendingDownIcon, ArrowTrendingUpIcon, ChartBarIcon, CurrencyDollarIcon } from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useState } from 'react';

interface UserMetrics {
    user_id: string;
    username: string;
    total_pnl: number;
    daily_pnl: number;
    weekly_pnl: number;
    monthly_pnl: number;
    win_rate: number;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    avg_win_amount: number;
    avg_loss_amount: number;
    largest_win: number;
    largest_loss: number;
    current_positions: number;
    available_margin: number;
    used_margin: number;
    portfolio_value: number;
}

interface Position {
    symbol: string;
    quantity: number;
    avg_price: number;
    current_price: number;
    pnl: number;
    pnl_percentage: number;
    position_type: 'LONG' | 'SHORT';
    exchange: string;
}

interface Trade {
    trade_id: string;
    symbol: string;
    side: 'BUY' | 'SELL';
    quantity: number;
    price: number;
    executed_at: string;
    pnl: number;
    status: string;
}

export default function UserAnalytics() {
    const [selectedUser, setSelectedUser] = useState<string>('');
    const [timeFrame, setTimeFrame] = useState<string>('daily');

    // Fetch users - ONLY REAL USERS FROM DATABASE
    const { data: users, error: usersError } = useQuery<{ id: string; username: string; }[]>({
        queryKey: ['users'],
        queryFn: async () => {
            const response = await axios.get('/api/users');
            if (!response.data.success) {
                throw new Error('Failed to fetch users');
            }
            return response.data.data;
        },
    });

    // Fetch user metrics - ONLY REAL SHAREKHAN DATA
    const { data: userMetrics, isLoading: metricsLoading, error: metricsError } = useQuery<UserMetrics>({
        queryKey: ['user-metrics', selectedUser, timeFrame],
        queryFn: async () => {
            const response = await axios.get(`/api/v1/analytics/user/${selectedUser}/metrics`, {
                params: { timeframe: timeFrame }
            });
            if (!response.data.success) {
                throw new Error('Failed to fetch user metrics');
            }
            return response.data.data;
        },
        enabled: !!selectedUser,
    });

    // Fetch user positions from ShareKhan - ONLY REAL POSITIONS
    const { data: positions, error: positionsError } = useQuery<Position[]>({
        queryKey: ['user-positions', selectedUser],
        queryFn: async () => {
            const response = await axios.get(`/api/sharekhan/portfolio/positions`, {
                params: { user_id: selectedUser }
            });
            if (!response.data.success) {
                throw new Error('Failed to fetch ShareKhan positions');
            }
            return response.data.data;
        },
        enabled: !!selectedUser,
        refetchInterval: 10000, // Refresh every 10 seconds for live data
    });

    // Fetch recent trades - ONLY REAL SHAREKHAN TRADES
    const { data: recentTrades, error: tradesError } = useQuery<Trade[]>({
        queryKey: ['user-trades', selectedUser],
        queryFn: async () => {
            const response = await axios.get(`/api/sharekhan/trades/history`, {
                params: { user_id: selectedUser, limit: 20 }
            });
            if (!response.data.success) {
                throw new Error('Failed to fetch ShareKhan trades');
            }
            return response.data.data;
        },
        enabled: !!selectedUser,
    });

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

    // Error handling for critical failures
    if (usersError) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h2 className="text-red-800 font-medium">Database Connection Error</h2>
                <p className="text-red-600 text-sm mt-1">Cannot connect to user database. Please check system configuration.</p>
            </div>
        );
    }

    if (metricsError) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h2 className="text-red-800 font-medium">ShareKhan API Error</h2>
                <p className="text-red-600 text-sm mt-1">Cannot fetch user metrics from ShareKhan API.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">ShareKhan User Analytics</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Real-time ShareKhan trading analytics and P&L data - LIVE DATA ONLY
                    </p>
                </div>
            </div>

            {/* User Selection */}
            <div className="bg-white rounded-lg shadow p-6">
                <div className="flex space-x-4 items-end">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Select User (Database Users Only)
                        </label>
                        <select
                            value={selectedUser}
                            onChange={(e) => setSelectedUser(e.target.value)}
                            className="w-full border border-gray-300 rounded-md px-3 py-2"
                        >
                            <option value="">Choose a real user...</option>
                            {users?.map((user) => (
                                <option key={user.id} value={user.id}>
                                    {user.username}
                                </option>
                            ))}
                        </select>
                        {users?.length === 0 && (
                            <p className="text-sm text-red-600 mt-2">No users found in database</p>
                        )}
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Time Frame
                        </label>
                        <select
                            value={timeFrame}
                            onChange={(e) => setTimeFrame(e.target.value)}
                            className="border border-gray-300 rounded-md px-3 py-2"
                        >
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                            <option value="yearly">Yearly</option>
                        </select>
                    </div>
                </div>
            </div>

            {selectedUser && (
                <>
                    {/* Key Metrics - ONLY REAL DATA */}
                    {metricsLoading ? (
                        <div className="bg-white rounded-lg shadow p-6 text-center">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="mt-2 text-gray-600">Loading real ShareKhan data...</p>
                        </div>
                    ) : userMetrics ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center">
                                    <CurrencyDollarIcon className="h-8 w-8 text-green-500" />
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Total P&L (ShareKhan)</p>
                                        <p className={`text-2xl font-bold ${userMetrics.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                            }`}>
                                            {formatCurrency(userMetrics.total_pnl)}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center">
                                    <ArrowTrendingUpIcon className="h-8 w-8 text-blue-500" />
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Daily P&L (ShareKhan)</p>
                                        <p className={`text-2xl font-bold ${userMetrics.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                            }`}>
                                            {formatCurrency(userMetrics.daily_pnl)}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center">
                                    <ChartBarIcon className="h-8 w-8 text-purple-500" />
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Win Rate</p>
                                        <p className="text-2xl font-bold text-gray-900">
                                            {formatPercentage(userMetrics.win_rate)}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            {userMetrics.winning_trades}/{userMetrics.total_trades} real trades
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center">
                                    <ArrowTrendingDownIcon className="h-8 w-8 text-orange-500" />
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Portfolio Value</p>
                                        <p className="text-2xl font-bold text-gray-900">
                                            {formatCurrency(userMetrics.portfolio_value)}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            Available: {formatCurrency(userMetrics.available_margin)}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                            <h2 className="text-yellow-800 font-medium">No ShareKhan Data Available</h2>
                            <p className="text-yellow-700 text-sm mt-1">No metrics found for this user in ShareKhan API.</p>
                        </div>
                    )}

                    {/* Current Positions - ONLY REAL SHAREKHAN POSITIONS */}
                    <div className="bg-white rounded-lg shadow">
                        <div className="px-6 py-4 border-b border-gray-200">
                            <h2 className="text-lg font-medium text-gray-900">Live ShareKhan Positions (Real Data Only)</h2>
                        </div>
                        {positionsError ? (
                            <div className="p-6 bg-red-50">
                                <p className="text-red-600">Error loading ShareKhan positions</p>
                            </div>
                        ) : positions && positions.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Price</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current Price</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {positions.map((position, index) => (
                                            <tr key={index}>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                    {position.symbol}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                    {position.quantity}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                    {formatCurrency(position.avg_price)}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                    {formatCurrency(position.current_price)}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                    <span className={`font-medium ${position.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                                        }`}>
                                                        {formatCurrency(position.pnl)}
                                                        <span className="ml-1">({formatPercentage(position.pnl_percentage)})</span>
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${position.position_type === 'LONG'
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-red-100 text-red-800'
                                                        }`}>
                                                        {position.position_type}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="p-6 text-center text-gray-500">
                                No live positions found in ShareKhan account
                            </div>
                        )}
                    </div>

                    {/* Recent Trades - ONLY REAL SHAREKHAN TRADES */}
                    <div className="bg-white rounded-lg shadow">
                        <div className="px-6 py-4 border-b border-gray-200">
                            <h2 className="text-lg font-medium text-gray-900">Recent ShareKhan Trades (Real Executions Only)</h2>
                        </div>
                        {tradesError ? (
                            <div className="p-6 bg-red-50">
                                <p className="text-red-600">Error loading ShareKhan trades</p>
                            </div>
                        ) : recentTrades && recentTrades.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Side</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantity</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {recentTrades.map((trade) => (
                                            <tr key={trade.trade_id}>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                    {trade.symbol}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${trade.side === 'BUY'
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-red-100 text-red-800'
                                                        }`}>
                                                        {trade.side}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                    {trade.quantity}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                    {formatCurrency(trade.price)}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                                    <span className={`font-medium ${trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                                        }`}>
                                                        {formatCurrency(trade.pnl)}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {new Date(trade.executed_at).toLocaleString()}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {trade.status}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="p-6 text-center text-gray-500">
                                No recent trades found in ShareKhan account
                            </div>
                        )}
                    </div>
                </>
            )}

            {!selectedUser && (
                <div className="bg-white rounded-lg shadow p-12 text-center">
                    <ChartBarIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h2 className="text-lg font-medium text-gray-900 mb-2">Select a Real User</h2>
                    <p className="text-gray-600">Choose a user from the database to view their live ShareKhan trading analytics</p>
                </div>
            )}
        </div>
    );
} 