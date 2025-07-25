import React, { useEffect, useState } from 'react';
import Chart from './Chart';
import DataTable from './DataTable';
import LoadingSpinner from './LoadingSpinner';
import MetricCard from './MetricCard';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app';

const Analytics = () => {
    const [analyticsData, setAnalyticsData] = useState({
        performance: {
            totalReturn: 0,
            sharpeRatio: 0,
            maxDrawdown: 0,
            winRate: 0,
            avgProfit: 0,
            avgLoss: 0,
            totalTrades: 0
        },
        charts: {
            pnlChart: [],
            returnsChart: [],
            drawdownChart: [],
            volumeChart: []
        },
        trades: [],
        monthlyReturns: []
    });
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState('3M');
    const [activeChartTab, setActiveChartTab] = useState('pnl');

    useEffect(() => {
        loadAnalyticsData();
    }, [timeRange]);

    const loadAnalyticsData = async () => {
        try {
            setLoading(true);

            const [performanceRes, tradesRes, chartsRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/analytics/performance?range=${timeRange}`),
                fetch(`${API_BASE_URL}/api/analytics/trades?range=${timeRange}`),
                fetch(`${API_BASE_URL}/api/analytics/charts?range=${timeRange}`)
            ]);

            const performanceData = performanceRes.ok ? await performanceRes.json() : {};
            const tradesData = tradesRes.ok ? await tradesRes.json() : [];
            const chartsData = chartsRes.ok ? await chartsRes.json() : {};

            setAnalyticsData({
                performance: performanceData,
                trades: tradesData,
                charts: chartsData,
                monthlyReturns: generateMonthlyReturns() // Mock data for now
            });
        } catch (error) {
            console.error('Failed to load analytics data:', error);
        } finally {
            setLoading(false);
        }
    };

    const generateMonthlyReturns = () => {
        // Mock monthly returns data
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return months.map(month => ({
            month,
            return: (Math.random() - 0.5) * 20 // Random returns between -10% to +10%
        }));
    };

    const tradeColumns = [
        {
            key: 'date',
            label: 'Date',
            render: (value) => new Date(value).toLocaleDateString()
        },
        {
            key: 'symbol',
            label: 'Symbol',
            render: (value) => <strong>{value}</strong>
        },
        {
            key: 'type',
            label: 'Type',
            render: (value) => (
                <span className={`badge ${value === 'BUY' ? 'badge-success' : 'badge-danger'}`}>
                    {value}
                </span>
            )
        },
        {
            key: 'quantity',
            label: 'Qty',
            align: 'right'
        },
        {
            key: 'price',
            label: 'Price',
            align: 'right',
            render: (value) => `₹${value.toFixed(2)}`
        },
        {
            key: 'pnl',
            label: 'P&L',
            align: 'right',
            render: (value) => (
                <span className={value >= 0 ? 'text-success' : 'text-error'}>
                    ₹{value.toLocaleString('en-IN')}
                </span>
            )
        },
        {
            key: 'duration',
            label: 'Duration',
            render: (value) => value || 'Intraday'
        }
    ];

    const getChartData = () => {
        switch (activeChartTab) {
            case 'pnl':
                return analyticsData.charts.pnlChart || [];
            case 'returns':
                return analyticsData.charts.returnsChart || [];
            case 'drawdown':
                return analyticsData.charts.drawdownChart || [];
            case 'volume':
                return analyticsData.charts.volumeChart || [];
            default:
                return [];
        }
    };

    if (loading) {
        return (
            <div className="analytics-loading">
                <LoadingSpinner size="large" />
                <p>Loading Analytics...</p>
            </div>
        );
    }

    const { performance } = analyticsData;

    return (
        <div className="analytics">
            <div className="analytics-header">
                <h1>Trading Analytics</h1>
                <div className="analytics-controls">
                    <select
                        value={timeRange}
                        onChange={(e) => setTimeRange(e.target.value)}
                        className="form-select"
                    >
                        <option value="1M">1 Month</option>
                        <option value="3M">3 Months</option>
                        <option value="6M">6 Months</option>
                        <option value="1Y">1 Year</option>
                        <option value="ALL">All Time</option>
                    </select>
                    <button className="btn btn-primary">Export Report</button>
                </div>
            </div>

            {/* Key Performance Metrics */}
            <div className="grid grid-cols-4 mb-lg">
                <MetricCard
                    title="Total Return"
                    value={`${performance.totalReturn?.toFixed(2) || '0.00'}%`}
                    icon="📈"
                    variant={performance.totalReturn >= 0 ? 'success' : 'danger'}
                />
                <MetricCard
                    title="Sharpe Ratio"
                    value={performance.sharpeRatio?.toFixed(2) || '0.00'}
                    subValue="Risk-adjusted return"
                    icon="📊"
                />
                <MetricCard
                    title="Max Drawdown"
                    value={`${performance.maxDrawdown?.toFixed(2) || '0.00'}%`}
                    icon="📉"
                    variant="warning"
                />
                <MetricCard
                    title="Win Rate"
                    value={`${performance.winRate?.toFixed(1) || '0.0'}%`}
                    subValue={`${performance.totalTrades || 0} total trades`}
                    icon="🎯"
                />
            </div>

            {/* Advanced Metrics */}
            <div className="grid grid-cols-3 mb-lg">
                <MetricCard
                    title="Average Profit"
                    value={`₹${performance.avgProfit?.toLocaleString('en-IN') || '0'}`}
                    icon="💰"
                    variant="success"
                />
                <MetricCard
                    title="Average Loss"
                    value={`₹${Math.abs(performance.avgLoss || 0).toLocaleString('en-IN')}`}
                    icon="💸"
                    variant="danger"
                />
                <MetricCard
                    title="Profit Factor"
                    value={(Math.abs(performance.avgProfit || 0) / Math.abs(performance.avgLoss || 1)).toFixed(2)}
                    subValue="Profit/Loss ratio"
                    icon="⚖️"
                />
            </div>

            {/* Performance Charts */}
            <div className="card mb-lg">
                <div className="card-header">
                    <h3 className="card-title">Performance Charts</h3>
                    <div className="chart-tabs">
                        <button
                            className={`tab-btn ${activeChartTab === 'pnl' ? 'active' : ''}`}
                            onClick={() => setActiveChartTab('pnl')}
                        >
                            P&L Curve
                        </button>
                        <button
                            className={`tab-btn ${activeChartTab === 'returns' ? 'active' : ''}`}
                            onClick={() => setActiveChartTab('returns')}
                        >
                            Returns
                        </button>
                        <button
                            className={`tab-btn ${activeChartTab === 'drawdown' ? 'active' : ''}`}
                            onClick={() => setActiveChartTab('drawdown')}
                        >
                            Drawdown
                        </button>
                        <button
                            className={`tab-btn ${activeChartTab === 'volume' ? 'active' : ''}`}
                            onClick={() => setActiveChartTab('volume')}
                        >
                            Volume
                        </button>
                    </div>
                </div>
                <div className="card-body">
                    <Chart
                        data={getChartData()}
                        type={activeChartTab === 'volume' ? 'bar' : 'line'}
                        height={400}
                    />
                </div>
            </div>

            {/* Monthly Returns Heatmap */}
            <div className="grid grid-cols-2 mb-lg">
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Monthly Returns</h3>
                    </div>
                    <div className="card-body">
                        <div className="monthly-returns-grid">
                            {analyticsData.monthlyReturns.map((monthData, index) => (
                                <div
                                    key={index}
                                    className={`monthly-return-cell ${monthData.return >= 0 ? 'positive' : 'negative'}`}
                                    style={{
                                        backgroundColor: monthData.return >= 0
                                            ? `rgba(16, 185, 129, ${Math.abs(monthData.return) / 10})`
                                            : `rgba(239, 68, 68, ${Math.abs(monthData.return) / 10})`
                                    }}
                                >
                                    <div className="month-name">{monthData.month}</div>
                                    <div className="month-return">{monthData.return.toFixed(1)}%</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Risk Metrics</h3>
                    </div>
                    <div className="card-body">
                        <div className="risk-metrics">
                            <div className="risk-metric">
                                <span className="metric-label">Volatility</span>
                                <span className="metric-value">15.3%</span>
                            </div>
                            <div className="risk-metric">
                                <span className="metric-label">Beta</span>
                                <span className="metric-value">1.12</span>
                            </div>
                            <div className="risk-metric">
                                <span className="metric-label">Alpha</span>
                                <span className="metric-value">2.4%</span>
                            </div>
                            <div className="risk-metric">
                                <span className="metric-label">VaR (95%)</span>
                                <span className="metric-value">₹12,450</span>
                            </div>
                            <div className="risk-metric">
                                <span className="metric-label">Correlation (NIFTY)</span>
                                <span className="metric-value">0.85</span>
                            </div>
                            <div className="risk-metric">
                                <span className="metric-label">Information Ratio</span>
                                <span className="metric-value">1.23</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Trade Analysis */}
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Trade Analysis</h3>
                    <div className="trade-filters">
                        <select className="form-select">
                            <option value="all">All Trades</option>
                            <option value="winners">Winners Only</option>
                            <option value="losers">Losers Only</option>
                        </select>
                        <input
                            type="text"
                            placeholder="Search symbol..."
                            className="form-input"
                        />
                    </div>
                </div>
                <div className="card-body">
                    <DataTable
                        data={analyticsData.trades}
                        columns={tradeColumns}
                        emptyMessage="No trades found for selected period"
                    />
                </div>
            </div>
        </div>
    );
};

export default Analytics; 