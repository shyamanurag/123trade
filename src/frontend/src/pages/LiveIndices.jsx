import { motion } from 'framer-motion'
import {
    Activity,
    BarChart3,
    Filter,
    RefreshCw,
    Search,
    TrendingDown,
    TrendingUp
} from 'lucide-react'
import React, { useState } from 'react'
import { useQuery } from 'react-query'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { useWebSocket } from '../context/WebSocketContext'
import { apiService } from '../services/apiService'

const LiveIndices = () => {
    const { isConnected, liveIndices, marketData, subscribeToSymbol, unsubscribeFromSymbol } = useWebSocket()
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedFilter, setSelectedFilter] = useState('all')
    const [subscribedSymbols, setSubscribedSymbols] = useState(new Set())

    const { data: indicesData, isLoading, refetch } = useQuery(
        'live-indices',
        apiService.getLiveIndices,
        {
            refetchInterval: isConnected ? 5000 : 30000,
            staleTime: 2000
        }
    )

    const indices = liveIndices.length > 0 ? liveIndices : (indicesData || [])

    const filteredIndices = indices.filter(index => {
        const matchesSearch = index.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
            index.name?.toLowerCase().includes(searchTerm.toLowerCase())

        const matchesFilter = selectedFilter === 'all' ||
            (selectedFilter === 'gainers' && index.change >= 0) ||
            (selectedFilter === 'losers' && index.change < 0) ||
            (selectedFilter === 'high-volume' && index.volume > 1000000)

        return matchesSearch && matchesFilter
    })

    const handleSubscribe = (symbol) => {
        if (subscribedSymbols.has(symbol)) {
            unsubscribeFromSymbol(symbol)
            setSubscribedSymbols(prev => {
                const newSet = new Set(prev)
                newSet.delete(symbol)
                return newSet
            })
        } else {
            subscribeToSymbol(symbol)
            setSubscribedSymbols(prev => new Set(prev).add(symbol))
        }
    }

    const getChangeColor = (change) => {
        if (change > 0) return 'text-success-600'
        if (change < 0) return 'text-danger-600'
        return 'text-gray-600'
    }

    const getChangeIcon = (change) => {
        if (change > 0) return <TrendingUp className="w-4 h-4" />
        if (change < 0) return <TrendingDown className="w-4 h-4" />
        return <Activity className="w-4 h-4" />
    }

    if (isLoading) {
        return (
            <div className="min-h-96 flex items-center justify-center">
                <LoadingSpinner size="large" text="Loading live indices..." />
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Live Market Indices</h1>
                    <p className="text-gray-600 mt-1">
                        Real-time market data and index performance
                    </p>
                </div>

                <div className="flex items-center space-x-3 mt-4 sm:mt-0">
                    <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg ${isConnected ? 'bg-success-50 text-success-700' : 'bg-gray-50 text-gray-600'
                        }`}>
                        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success-500 animate-pulse' : 'bg-gray-400'
                            }`} />
                        <span className="text-sm font-medium">
                            {isConnected ? 'Live' : 'Delayed'}
                        </span>
                    </div>

                    <button
                        onClick={() => refetch()}
                        className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                        <RefreshCw className="w-5 h-5 text-gray-600" />
                    </button>
                </div>
            </div>

            {/* Controls */}
            <div className="flex flex-col sm:flex-row gap-4">
                {/* Search */}
                <div className="flex-1">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="Search indices by symbol or name..."
                            className="input-field pl-10"
                        />
                    </div>
                </div>

                {/* Filter */}
                <div className="flex items-center space-x-2">
                    <Filter className="w-5 h-5 text-gray-400" />
                    <select
                        value={selectedFilter}
                        onChange={(e) => setSelectedFilter(e.target.value)}
                        className="input-field min-w-32"
                    >
                        <option value="all">All Indices</option>
                        <option value="gainers">Gainers</option>
                        <option value="losers">Losers</option>
                        <option value="high-volume">High Volume</option>
                    </select>
                </div>
            </div>

            {/* Indices Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredIndices.map((index, i) => (
                    <motion.div
                        key={index.symbol}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="card hover:shadow-md transition-shadow duration-200"
                    >
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex-1">
                                <div className="flex items-center space-x-2">
                                    <h3 className="text-lg font-semibold text-gray-900">
                                        {index.symbol}
                                    </h3>
                                    <button
                                        onClick={() => handleSubscribe(index.symbol)}
                                        className={`p-1 rounded transition-colors ${subscribedSymbols.has(index.symbol)
                                                ? 'bg-primary-100 text-primary-600'
                                                : 'bg-gray-100 text-gray-400 hover:text-gray-600'
                                            }`}
                                    >
                                        <BarChart3 className="w-4 h-4" />
                                    </button>
                                </div>

                                {index.name && (
                                    <p className="text-sm text-gray-500 mt-1">{index.name}</p>
                                )}
                            </div>

                            <div className={`px-2 py-1 rounded-full text-xs font-medium ${isConnected && marketData[index.symbol]
                                    ? 'bg-success-100 text-success-700'
                                    : 'bg-gray-100 text-gray-600'
                                }`}>
                                {isConnected && marketData[index.symbol] ? 'LIVE' : 'DELAYED'}
                            </div>
                        </div>

                        <div className="space-y-3">
                            {/* Price */}
                            <div className="flex items-center justify-between">
                                <span className="text-2xl font-bold text-gray-900">
                                    ₹{(marketData[index.symbol]?.price || index.price || 0).toLocaleString()}
                                </span>
                                <div className={`flex items-center space-x-1 ${getChangeColor(marketData[index.symbol]?.change || index.change || 0)
                                    }`}>
                                    {getChangeIcon(marketData[index.symbol]?.change || index.change || 0)}
                                    <span className="font-medium">
                                        {Math.abs(marketData[index.symbol]?.change || index.change || 0).toFixed(2)}
                                    </span>
                                </div>
                            </div>

                            {/* Change Percentage */}
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-600">Change %</span>
                                <span className={`font-medium ${getChangeColor(marketData[index.symbol]?.change_percent || index.change_percent || 0)
                                    }`}>
                                    {(marketData[index.symbol]?.change_percent || index.change_percent || 0) >= 0 ? '+' : ''}
                                    {(marketData[index.symbol]?.change_percent || index.change_percent || 0).toFixed(2)}%
                                </span>
                            </div>

                            {/* Volume */}
                            {(marketData[index.symbol]?.volume || index.volume) && (
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">Volume</span>
                                    <span className="text-sm font-medium text-gray-900">
                                        {(marketData[index.symbol]?.volume || index.volume || 0).toLocaleString()}
                                    </span>
                                </div>
                            )}

                            {/* High/Low */}
                            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-100">
                                <div className="text-center">
                                    <p className="text-xs text-gray-500">High</p>
                                    <p className="font-medium text-success-600">
                                        ₹{(marketData[index.symbol]?.high || index.high || 0).toLocaleString()}
                                    </p>
                                </div>
                                <div className="text-center">
                                    <p className="text-xs text-gray-500">Low</p>
                                    <p className="font-medium text-danger-600">
                                        ₹{(marketData[index.symbol]?.low || index.low || 0).toLocaleString()}
                                    </p>
                                </div>
                            </div>

                            {/* Last Updated */}
                            <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
                                Last updated: {
                                    marketData[index.symbol]?.timestamp
                                        ? new Date(marketData[index.symbol].timestamp).toLocaleTimeString()
                                        : 'N/A'
                                }
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* No Results */}
            {filteredIndices.length === 0 && (
                <div className="text-center py-12">
                    <BarChart3 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No indices found</h3>
                    <p className="text-gray-600">
                        {searchTerm ? 'Try adjusting your search terms' : 'No indices available at the moment'}
                    </p>
                </div>
            )}
        </div>
    )
}

export default LiveIndices 