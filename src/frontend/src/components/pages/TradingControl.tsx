import { AdjustmentsVerticalIcon, ExclamationTriangleIcon, PlayIcon, StopIcon } from '@heroicons/react/24/outline';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useState } from 'react';
import toast from 'react-hot-toast';

interface TradingStrategy {
    id: string;
    name: string;
    description: string;
    status: 'active' | 'inactive' | 'paused';
    risk_level: 'low' | 'medium' | 'high';
    max_position_size: number;
    stop_loss_percentage: number;
    take_profit_percentage: number;
    active_trades: number;
    total_pnl: number;
}

interface RiskSettings {
    max_daily_loss: number;
    max_position_size: number;
    max_open_positions: number;
    trading_enabled: boolean;
    hard_stop_enabled: boolean;
}

interface SystemControl {
    orchestrator_status: 'running' | 'stopped' | 'error';
    auto_trading_enabled: boolean;
    manual_override: boolean;
    last_heartbeat: string;
}

export default function TradingControl() {
    const [selectedStrategy, setSelectedStrategy] = useState<string>('');
    const queryClient = useQueryClient();

    // Fetch trading strategies
    const { data: strategies, isLoading: strategiesLoading } = useQuery<TradingStrategy[]>({
        queryKey: ['trading-strategies'],
        queryFn: async () => {
            const response = await axios.get('/api/strategies');
            if (!response.data.success) {
                throw new Error('Failed to fetch strategies');
            }
            return response.data.data;
        },
        refetchInterval: 10000,
    });

    // Fetch risk settings
    const { data: riskSettings } = useQuery<RiskSettings>({
        queryKey: ['risk-settings'],
        queryFn: async () => {
            const response = await axios.get('/api/risk/settings');
            if (!response.data.success) {
                throw new Error('Failed to fetch risk settings');
            }
            return response.data.data;
        },
    });

    // Fetch system control status
    const { data: systemControl } = useQuery<SystemControl>({
        queryKey: ['system-control'],
        queryFn: async () => {
            const response = await axios.get('/api/system/control');
            if (!response.data.success) {
                throw new Error('Failed to fetch system control');
            }
            return response.data.data;
        },
        refetchInterval: 5000,
    });

    // Start strategy mutation
    const startStrategyMutation = useMutation({
        mutationFn: async (strategyId: string) => {
            const response = await axios.post(`/api/strategies/${strategyId}/start`);
            if (!response.data.success) {
                throw new Error('Failed to start strategy');
            }
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['trading-strategies'] });
            toast.success('Strategy started successfully');
        },
        onError: (error: any) => {
            toast.error(`Failed to start strategy: ${error.message}`);
        },
    });

    // Stop strategy mutation
    const stopStrategyMutation = useMutation({
        mutationFn: async (strategyId: string) => {
            const response = await axios.post(`/api/strategies/${strategyId}/stop`);
            if (!response.data.success) {
                throw new Error('Failed to stop strategy');
            }
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['trading-strategies'] });
            toast.success('Strategy stopped successfully');
        },
        onError: (error: any) => {
            toast.error(`Failed to stop strategy: ${error.message}`);
        },
    });

    // Emergency stop all mutation
    const emergencyStopMutation = useMutation({
        mutationFn: async () => {
            const response = await axios.post('/api/trading/emergency-stop');
            if (!response.data.success) {
                throw new Error('Failed to execute emergency stop');
            }
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['trading-strategies'] });
            queryClient.invalidateQueries({ queryKey: ['system-control'] });
            toast.success('Emergency stop executed');
        },
        onError: (error: any) => {
            toast.error(`Emergency stop failed: ${error.message}`);
        },
    });

    // Toggle auto trading mutation
    const toggleAutoTradingMutation = useMutation({
        mutationFn: async (enabled: boolean) => {
            const response = await axios.post('/api/trading/auto-toggle', { enabled });
            if (!response.data.success) {
                throw new Error('Failed to toggle auto trading');
            }
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['system-control'] });
            toast.success('Auto trading setting updated');
        },
        onError: (error: any) => {
            toast.error(`Failed to update auto trading: ${error.message}`);
        },
    });

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
        }).format(value);
    };

    const getRiskBadgeColor = (risk: string) => {
        switch (risk) {
            case 'low': return 'bg-green-100 text-green-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'high': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusBadgeColor = (status: string) => {
        switch (status) {
            case 'active': return 'bg-green-100 text-green-800';
            case 'inactive': return 'bg-red-100 text-red-800';
            case 'paused': return 'bg-yellow-100 text-yellow-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Trading Control Center</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Manage ShareKhan trading strategies and risk controls - Live system
                    </p>
                </div>
            </div>

            {/* System Status */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Orchestrator Status</h3>
                    <div className="flex items-center">
                        <div className={`h-3 w-3 rounded-full mr-2 ${systemControl?.orchestrator_status === 'running' ? 'bg-green-500' :
                                systemControl?.orchestrator_status === 'error' ? 'bg-red-500' : 'bg-gray-500'
                            }`}></div>
                        <span className="text-lg font-semibold capitalize">
                            {systemControl?.orchestrator_status || 'Unknown'}
                        </span>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Auto Trading</h3>
                    <div className="flex items-center justify-between">
                        <span className={`text-lg font-semibold ${systemControl?.auto_trading_enabled ? 'text-green-600' : 'text-red-600'
                            }`}>
                            {systemControl?.auto_trading_enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <button
                            onClick={() => toggleAutoTradingMutation.mutate(!systemControl?.auto_trading_enabled)}
                            className={`px-3 py-1 rounded text-sm font-medium ${systemControl?.auto_trading_enabled
                                    ? 'bg-red-100 text-red-700 hover:bg-red-200'
                                    : 'bg-green-100 text-green-700 hover:bg-green-200'
                                }`}
                        >
                            {systemControl?.auto_trading_enabled ? 'Disable' : 'Enable'}
                        </button>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Emergency Controls</h3>
                    <button
                        onClick={() => {
                            if (window.confirm('Are you sure you want to execute emergency stop? This will halt all trading immediately.')) {
                                emergencyStopMutation.mutate();
                            }
                        }}
                        className="w-full bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 flex items-center justify-center"
                    >
                        <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
                        Emergency Stop All
                    </button>
                </div>
            </div>

            {/* Risk Settings */}
            {riskSettings && (
                <div className="bg-white rounded-lg shadow p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Risk Management Settings</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="bg-gray-50 p-4 rounded-lg">
                            <h4 className="font-medium text-gray-900">Max Daily Loss</h4>
                            <p className="text-2xl font-bold text-red-600">{formatCurrency(riskSettings.max_daily_loss)}</p>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                            <h4 className="font-medium text-gray-900">Max Position Size</h4>
                            <p className="text-2xl font-bold text-blue-600">{formatCurrency(riskSettings.max_position_size)}</p>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                            <h4 className="font-medium text-gray-900">Max Open Positions</h4>
                            <p className="text-2xl font-bold text-purple-600">{riskSettings.max_open_positions}</p>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                            <h4 className="font-medium text-gray-900">Hard Stop</h4>
                            <p className={`text-2xl font-bold ${riskSettings.hard_stop_enabled ? 'text-red-600' : 'text-gray-600'}`}>
                                {riskSettings.hard_stop_enabled ? 'Enabled' : 'Disabled'}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Trading Strategies */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium text-gray-900">Active Trading Strategies</h2>
                </div>

                {strategiesLoading ? (
                    <div className="p-6 text-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                        <p className="mt-2 text-gray-600">Loading strategies...</p>
                    </div>
                ) : strategies && strategies.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Strategy</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Level</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Active Trades</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total P&L</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {strategies.map((strategy) => (
                                    <tr key={strategy.id}>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div>
                                                <div className="text-sm font-medium text-gray-900">{strategy.name}</div>
                                                <div className="text-sm text-gray-500">{strategy.description}</div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadgeColor(strategy.status)}`}>
                                                {strategy.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRiskBadgeColor(strategy.risk_level)}`}>
                                                {strategy.risk_level}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {strategy.active_trades}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            <span className={`font-medium ${strategy.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                                }`}>
                                                {formatCurrency(strategy.total_pnl)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                                            {strategy.status === 'active' ? (
                                                <button
                                                    onClick={() => stopStrategyMutation.mutate(strategy.id)}
                                                    className="text-red-600 hover:text-red-900 flex items-center"
                                                    disabled={stopStrategyMutation.isLoading}
                                                >
                                                    <StopIcon className="h-4 w-4 mr-1" />
                                                    Stop
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={() => startStrategyMutation.mutate(strategy.id)}
                                                    className="text-green-600 hover:text-green-900 flex items-center"
                                                    disabled={startStrategyMutation.isLoading}
                                                >
                                                    <PlayIcon className="h-4 w-4 mr-1" />
                                                    Start
                                                </button>
                                            )}
                                            <button
                                                className="text-blue-600 hover:text-blue-900 flex items-center"
                                            >
                                                <AdjustmentsVerticalIcon className="h-4 w-4 mr-1" />
                                                Configure
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="p-6 text-center text-gray-500">
                        No trading strategies configured
                    </div>
                )}
            </div>
        </div>
    );
} 