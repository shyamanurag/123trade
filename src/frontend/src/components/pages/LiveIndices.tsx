import { ArrowDownIcon, ArrowTrendingDownIcon, ArrowTrendingUpIcon, ArrowUpIcon } from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface MarketIndex {
    symbol: string;
    name: string;
    ltp: number;
    change: number;
    change_percent: number;
    high: number;
    low: number;
    open: number;
    volume: number;
}

export default function LiveIndices() {
    const { data: indices, isLoading, error } = useQuery<MarketIndex[]>({
        queryKey: ['market-indices'],
        queryFn: async () => {
            const response = await axios.get('/api/indices');
            return response.data.data;
        },
        refetchInterval: 5000, // Refresh every 5 seconds
    });

    const formatNumber = (value: number) => {
        return new Intl.NumberFormat('en-IN').format(value);
    };

    const formatPercentage = (value: number) => {
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    };

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h2 className="text-red-800 font-medium">Error loading market data</h2>
                <p className="text-red-600 text-sm mt-1">Please check your connection and try again.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Live Market Indices</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Real-time market data updated every 5 seconds
                    </p>
                </div>
                <div className="text-sm text-gray-500">
                    Last updated: {new Date().toLocaleTimeString()}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {indices?.map((index) => (
                    <div key={index.symbol} className="bg-white rounded-lg shadow-lg p-6 border-l-4 border-blue-500">
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900">{index.symbol}</h3>
                                <p className="text-sm text-gray-600">{index.name}</p>
                            </div>
                            <div className="flex items-center">
                                {index.change_percent >= 0 ? (
                                    <ArrowTrendingUpIcon className="h-6 w-6 text-green-500" />
                                ) : (
                                    <ArrowTrendingDownIcon className="h-6 w-6 text-red-500" />
                                )}
                            </div>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-baseline">
                                <span className="text-3xl font-bold text-gray-900">
                                    {formatNumber(index.ltp)}
                                </span>
                                <div className={`ml-3 flex items-center ${index.change >= 0 ? 'text-green-600' : 'text-red-600'
                                    }`}>
                                    {index.change >= 0 ? (
                                        <ArrowUpIcon className="h-4 w-4 mr-1" />
                                    ) : (
                                        <ArrowDownIcon className="h-4 w-4 mr-1" />
                                    )}
                                    <span className="font-medium">
                                        {formatNumber(Math.abs(index.change))}
                                    </span>
                                    <span className="ml-1 text-sm">
                                        ({formatPercentage(index.change_percent)})
                                    </span>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-gray-500">Open:</span>
                                    <span className="ml-2 font-medium">{formatNumber(index.open)}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500">High:</span>
                                    <span className="ml-2 font-medium text-green-600">{formatNumber(index.high)}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500">Low:</span>
                                    <span className="ml-2 font-medium text-red-600">{formatNumber(index.low)}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500">Volume:</span>
                                    <span className="ml-2 font-medium">{formatNumber(index.volume)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Market Status */}
            <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Market Status</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                        <div className="text-green-600 font-semibold">Market Open</div>
                        <div className="text-sm text-gray-600 mt-1">9:15 AM - 3:30 PM IST</div>
                    </div>
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                        <div className="text-blue-600 font-semibold">Next Update</div>
                        <div className="text-sm text-gray-600 mt-1">5 seconds</div>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                        <div className="text-purple-600 font-semibold">Total Indices</div>
                        <div className="text-sm text-gray-600 mt-1">{indices?.length || 0} indices</div>
                    </div>
                </div>
            </div>
        </div>
    );
} 