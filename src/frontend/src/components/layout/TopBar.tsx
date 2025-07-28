import { BellIcon, PowerIcon } from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useState } from 'react';

interface SystemStatus {
    orchestrator_health: string;
    active_users: number;
    total_trades_today: number;
    system_uptime: string;
}

export default function TopBar() {
    const [orchestratorEnabled, setOrchestratorEnabled] = useState(false);

    const { data: systemStatus } = useQuery<SystemStatus>({
        queryKey: ['system-status'],
        queryFn: async () => {
            const response = await axios.get('/api/system/status');
            return response.data.data;
        },
        refetchInterval: 5000, // Refresh every 5 seconds
    });

    const toggleOrchestrator = async () => {
        try {
            const action = orchestratorEnabled ? 'stop' : 'start';
            await axios.post('/api/autonomous/control', { action });
            setOrchestratorEnabled(!orchestratorEnabled);
        } catch (error) {
            console.error('Failed to toggle orchestrator:', error);
        }
    };

    return (
        <header className="bg-white shadow-sm border-b border-gray-200">
            <div className="flex items-center justify-between px-6 py-4">
                <div className="flex items-center space-x-6">
                    <h1 className="text-2xl font-bold text-gray-900">ShareKhan Trading System</h1>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                        <div className="flex items-center">
                            <div className={`h-2 w-2 rounded-full mr-2 ${systemStatus?.orchestrator_health === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                                }`}></div>
                            <span>Orchestrator: {systemStatus?.orchestrator_health || 'Unknown'}</span>
                        </div>
                        <div>Active Users: {systemStatus?.active_users || 0}</div>
                        <div>Today's Trades: {systemStatus?.total_trades_today || 0}</div>
                    </div>
                </div>

                <div className="flex items-center space-x-4">
                    {/* Orchestrator Toggle */}
                    <button
                        onClick={toggleOrchestrator}
                        className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors ${orchestratorEnabled
                            ? 'bg-red-100 text-red-700 hover:bg-red-200'
                            : 'bg-green-100 text-green-700 hover:bg-green-200'
                            }`}
                    >
                        <PowerIcon className="h-4 w-4 mr-2" />
                        {orchestratorEnabled ? 'Stop Orchestrator' : 'Start Orchestrator'}
                    </button>

                    {/* Notifications */}
                    <button className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg">
                        <BellIcon className="h-6 w-6" />
                    </button>

                    {/* System Time */}
                    <div className="text-sm text-gray-600">
                        {new Date().toLocaleTimeString('en-IN', {
                            timeZone: 'Asia/Kolkata',
                            hour12: false
                        })} IST
                    </div>
                </div>
            </div>
        </header>
    );
} 