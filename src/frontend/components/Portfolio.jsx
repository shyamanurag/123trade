import React, { useEffect, useState } from 'react';
import Chart from './Chart';
import DataTable from './DataTable';
import LoadingSpinner from './LoadingSpinner';
import MetricCard from './MetricCard';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app';

const Portfolio = () => {
    const [portfolioData, setPortfolioData] = useState({
        summary: {
            totalValue: 0,
            totalInvestment: 0,
            totalPnL: 0,
            totalPnLPercent: 0,
            dayPnL: 0,
            dayPnLPercent: 0,
            realizedPnL: 0,
            unrealizedPnL: 0
        },
        holdings: [],
        positions: [],
        performance: []
    });
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('holdings');
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

    useEffect(() => {
        loadPortfolioData();

        // Set up real-time updates
        const interval = setInterval(loadPortfolioData, 30000);
        return () => clearInterval(interval);
    }, []);

    const loadPortfolioData = async () => {
        try {
            const [summaryRes, holdingsRes, positionsRes, performanceRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/portfolio/summary`),
                fetch(`${API_BASE_URL}/api/portfolio/holdings`),
                fetch(`${API_BASE_URL}/api/portfolio/positions`),
                fetch(`${API_BASE_URL}/api/portfolio/performance`)
            ]);

            const summaryData = summaryRes.ok ? await summaryRes.json() : {};
            const holdingsData = holdingsRes.ok ? await holdingsRes.json() : [];
            const positionsData = positionsRes.ok ? await positionsRes.json() : [];
            const performanceData = performanceRes.ok ? await performanceRes.json() : [];

            setPortfolioData({
                summary: summaryData,
                holdings: holdingsData,
                positions: positionsData,
                performance: performanceData
            });
        } catch (error) {
            console.error('Failed to load portfolio data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const sortedData = React.useMemo(() => {
        const data = activeTab === 'holdings' ? portfolioData.holdings : portfolioData.positions;
        if (!sortConfig.key) return data;

        return [...data].sort((a, b) => {
            if (a[sortConfig.key] < b[sortConfig.key]) {
                return sortConfig.direction === 'asc' ? -1 : 1;
            }
            if (a[sortConfig.key] > b[sortConfig.key]) {
                return sortConfig.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }, [portfolioData, activeTab, sortConfig]);

    const holdingsColumns = [
        {
            key: 'symbol',
            label: 'Symbol',
            render: (value, row) => (
                <div className="symbol-cell">
                    <strong>{value}</strong>
                    <small>{row.exchange}</small>
                </div>
            )
        },
        {
            key: 'quantity',
            label: 'Qty',
            align: 'right'
        },
        {
            key: 'avgPrice',
            label: 'Avg Price',
            align: 'right',
            render: (value) => `₹${value.toFixed(2)}`
        },
        {
            key: 'ltp',
            label: 'LTP',
            align: 'right',
            render: (value) => `₹${value.toFixed(2)}`
        },
        {
            key: 'currentValue',
            label: 'Current Value',
            align: 'right',
            render: (value) => `₹${value.toLocaleString('en-IN')}`
        },
        {
            key: 'pnl',
            label: 'P&L',
            align: 'right',
            render: (value, row) => (
                <div className={`pnl-cell ${value >= 0 ? 'positive' : 'negative'}`}>
                    <div>₹{value.toLocaleString('en-IN')}</div>
                    <small>({row.pnlPercent.toFixed(2)}%)</small>
                </div>
            )
        }
    ];

    const positionsColumns = [
        {
            key: 'symbol',
            label: 'Symbol',
            render: (value, row) => (
                <div className="symbol-cell">
                    <strong>{value}</strong>
                    <small>{row.product}</small>
                </div>
            )
        },
        {
            key: 'quantity',
            label: 'Qty',
            align: 'right',
            render: (value, row) => (
                <span className={value > 0 ? 'text-success' : 'text-error'}>
                    {value > 0 ? '+' : ''}{value}
                </span>
            )
        },
        {
            key: 'avgPrice',
            label: 'Avg Price',
            align: 'right',
            render: (value) => `₹${value.toFixed(2)}`
        },
        {
            key: 'ltp',
            label: 'LTP',
            align: 'right',
            render: (value) => `₹${value.toFixed(2)}`
        },
        {
            key: 'pnl',
            label: 'P&L',
            align: 'right',
            render: (value, row) => (
                <div className={`pnl-cell ${value >= 0 ? 'positive' : 'negative'}`}>
                    <div>₹{value.toLocaleString('en-IN')}</div>
                    <small>({row.pnlPercent.toFixed(2)}%)</small>
                </div>
            )
        },
        {
            key: 'actions',
            label: 'Actions',
            render: (value, row) => (
                <div className="action-buttons">
                    <button className="btn btn-sm btn-success">BUY</button>
                    <button className="btn btn-sm btn-danger">SELL</button>
                </div>
            )
        }
    ];

    if (loading) {
        return (
            <div className="portfolio-loading">
                <LoadingSpinner size="large" />
                <p>Loading Portfolio...</p>
            </div>
        );
    }

    const { summary } = portfolioData;

    return (
        <div className="portfolio">
            {/* Portfolio Summary */}
            <div className="portfolio-header">
                <h1>Portfolio Overview</h1>
                <div className="summary-actions">
                    <button className="btn btn-primary">Export Report</button>
                    <button className="btn btn-secondary">Refresh</button>
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-4 mb-lg">
                <MetricCard
                    title="Total Value"
                    value={`₹${summary.totalValue?.toLocaleString('en-IN') || '0'}`}
                    subValue={`Investment: ₹${summary.totalInvestment?.toLocaleString('en-IN') || '0'}`}
                    icon="💰"
                />
                <MetricCard
                    title="Total P&L"
                    value={`₹${summary.totalPnL?.toLocaleString('en-IN') || '0'}`}
                    change={summary.totalPnL}
                    changePercent={summary.totalPnLPercent}
                    icon={summary.totalPnL >= 0 ? "📈" : "📉"}
                    variant={summary.totalPnL >= 0 ? "success" : "danger"}
                />
                <MetricCard
                    title="Day P&L"
                    value={`₹${summary.dayPnL?.toLocaleString('en-IN') || '0'}`}
                    change={summary.dayPnL}
                    changePercent={summary.dayPnLPercent}
                    icon={summary.dayPnL >= 0 ? "📈" : "📉"}
                    variant={summary.dayPnL >= 0 ? "success" : "danger"}
                />
                <MetricCard
                    title="Realized P&L"
                    value={`₹${summary.realizedPnL?.toLocaleString('en-IN') || '0'}`}
                    subValue={`Unrealized: ₹${summary.unrealizedPnL?.toLocaleString('en-IN') || '0'}`}
                    icon="💵"
                />
            </div>

            {/* Performance Chart */}
            <div className="card mb-lg">
                <div className="card-header">
                    <h3 className="card-title">Portfolio Performance</h3>
                    <div className="chart-controls">
                        <select className="form-select">
                            <option value="1M">1 Month</option>
                            <option value="3M">3 Months</option>
                            <option value="6M">6 Months</option>
                            <option value="1Y">1 Year</option>
                            <option value="ALL">All Time</option>
                        </select>
                    </div>
                </div>
                <div className="card-body">
                    <Chart
                        data={portfolioData.performance}
                        type="area"
                        height={300}
                    />
                </div>
            </div>

            {/* Holdings & Positions Tabs */}
            <div className="card">
                <div className="card-header">
                    <div className="tab-buttons">
                        <button
                            className={`tab-btn ${activeTab === 'holdings' ? 'active' : ''}`}
                            onClick={() => setActiveTab('holdings')}
                        >
                            Holdings ({portfolioData.holdings.length})
                        </button>
                        <button
                            className={`tab-btn ${activeTab === 'positions' ? 'active' : ''}`}
                            onClick={() => setActiveTab('positions')}
                        >
                            Positions ({portfolioData.positions.length})
                        </button>
                    </div>

                    <div className="table-actions">
                        <input
                            type="text"
                            placeholder="Search symbols..."
                            className="form-input"
                            style={{ width: '200px' }}
                        />
                    </div>
                </div>

                <div className="card-body">
                    <DataTable
                        data={sortedData}
                        columns={activeTab === 'holdings' ? holdingsColumns : positionsColumns}
                        onSort={handleSort}
                        sortConfig={sortConfig}
                        emptyMessage={`No ${activeTab} found`}
                    />
                </div>
            </div>

            {/* Portfolio Allocation */}
            <div className="grid grid-cols-2 mt-lg">
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Sector Allocation</h3>
                    </div>
                    <div className="card-body">
                        <Chart
                            data={[
                                { name: 'Banking', value: 35 },
                                { name: 'IT', value: 25 },
                                { name: 'Pharma', value: 15 },
                                { name: 'Auto', value: 12 },
                                { name: 'Energy', value: 8 },
                                { name: 'Others', value: 5 }
                            ]}
                            type="pie"
                            height={300}
                        />
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Top Performers</h3>
                    </div>
                    <div className="card-body">
                        <div className="top-performers">
                            {portfolioData.holdings
                                .sort((a, b) => b.pnlPercent - a.pnlPercent)
                                .slice(0, 5)
                                .map((stock, index) => (
                                    <div key={stock.symbol} className="performer-item">
                                        <div className="rank">#{index + 1}</div>
                                        <div className="symbol-info">
                                            <strong>{stock.symbol}</strong>
                                            <small>{stock.exchange}</small>
                                        </div>
                                        <div className={`performance ${stock.pnlPercent >= 0 ? 'positive' : 'negative'}`}>
                                            {stock.pnlPercent >= 0 ? '+' : ''}{stock.pnlPercent.toFixed(2)}%
                                        </div>
                                    </div>
                                ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Portfolio; 