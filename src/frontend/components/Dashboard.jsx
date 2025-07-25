import React, { useEffect, useState } from 'react';
import Chart from './Chart';
import LoadingSpinner from './LoadingSpinner';
import MarketOverview from './MarketOverview';
import MetricCard from './MetricCard';
import NewsPanel from './NewsPanel';
import PositionSummary from './PositionSummary';
import QuickActions from './QuickActions';
import RecentTrades from './RecentTrades';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app';

const Dashboard = () => {
    const [dashboardData, setDashboardData] = useState({
        portfolio: {
            totalValue: 0,
            dayPnL: 0,
            dayPnLPercent: 0,
            totalPnL: 0,
            totalPnLPercent: 0,
            availableMargin: 0,
            usedMargin: 0
        },
        positions: [],
        recentTrades: [],
        marketData: {},
        performance: {
            chart: [],
            metrics: {}
        }
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdate, setLastUpdate] = useState(new Date());

    useEffect(() => {
        loadDashboardData();

        // Set up real-time updates
        const interval = setInterval(() => {
            loadDashboardData(false); // Don't show loading for updates
        }, 10000); // Update every 10 seconds

        return () => clearInterval(interval);
    }, []);

    const loadDashboardData = async (showLoading = true) => {
        try {
            if (showLoading) setLoading(true);
            setError(null);

            // Fetch all dashboard data in parallel
            const [portfolioRes, positionsRes, tradesRes, performanceRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/portfolio/summary`),
                fetch(`${API_BASE_URL}/api/portfolio/positions`),
                fetch(`${API_BASE_URL}/api/orders/recent`),
                fetch(`${API_BASE_URL}/api/performance/metrics`)
            ]);

            const portfolioData = portfolioRes.ok ? await portfolioRes.json() : {};
            const positionsData = positionsRes.ok ? await positionsRes.json() : [];
            const tradesData = tradesRes.ok ? await tradesRes.json() : [];
            const performanceData = performanceRes.ok ? await performanceRes.json() : {};

            setDashboardData({
                portfolio: {
                    totalValue: portfolioData.totalValue || 0,
                    dayPnL: portfolioData.dayPnL || 0,
                    dayPnLPercent: portfolioData.dayPnLPercent || 0,
                    totalPnL: portfolioData.totalPnL || 0,
                    totalPnLPercent: portfolioData.totalPnLPercent || 0,
                    availableMargin: portfolioData.availableMargin || 0,
                    usedMargin: portfolioData.usedMargin || 0
                },
                positions: Array.isArray(positionsData) ? positionsData.slice(0, 10) : [],
                recentTrades: Array.isArray(tradesData) ? tradesData.slice(0, 10) : [],
                performance: performanceData.data || { chart: [], metrics: {} }
            });

            setLastUpdate(new Date());
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            setError('Failed to load dashboard data');
        } finally {
            if (showLoading) setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="dashboard-loading">
                <LoadingSpinner size="large" />
                <p>Loading Dashboard...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="dashboard-error">
                <h3>Dashboard Error</h3>
                <p>{error}</p>
                <button className="btn btn-primary" onClick={() => loadDashboardData()}>
                    Retry
                </button>
            </div>
        );
    }

    const { portfolio, positions, recentTrades, performance } = dashboardData;

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <div>
                    <h1>Trading Dashboard</h1>
                    <p className="text-secondary">
                        Last updated: {lastUpdate.toLocaleTimeString()}
                    </p>
                </div>
                <QuickActions />
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-4 mb-lg">
                <MetricCard
                    title="Portfolio Value"
                    value={`₹${portfolio.totalValue.toLocaleString('en-IN')}`}
                    change={portfolio.totalPnL}
                    changePercent={portfolio.totalPnLPercent}
                    icon="💰"
                />
                <MetricCard
                    title="Day P&L"
                    value={`₹${portfolio.dayPnL.toLocaleString('en-IN')}`}
                    change={portfolio.dayPnL}
                    changePercent={portfolio.dayPnLPercent}
                    icon={portfolio.dayPnL >= 0 ? "📈" : "📉"}
                    variant={portfolio.dayPnL >= 0 ? "success" : "danger"}
                />
                <MetricCard
                    title="Available Margin"
                    value={`₹${portfolio.availableMargin.toLocaleString('en-IN')}`}
                    subValue={`Used: ₹${portfolio.usedMargin.toLocaleString('en-IN')}`}
                    icon="💳"
                />
                <MetricCard
                    title="Active Positions"
                    value={positions.length.toString()}
                    subValue={`${positions.filter(p => p.pnl > 0).length} profitable`}
                    icon="📊"
                />
            </div>

            {/* Charts and Market Overview */}
            <div className="grid grid-cols-3 mb-lg">
                <div className="col-span-2">
                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title">Portfolio Performance</h3>
                            <div className="chart-controls">
                                <select className="form-select">
                                    <option value="1D">1 Day</option>
                                    <option value="1W">1 Week</option>
                                    <option value="1M">1 Month</option>
                                    <option value="3M">3 Months</option>
                                    <option value="1Y">1 Year</option>
                                </select>
                            </div>
                        </div>
                        <div className="card-body">
                            <Chart
                                data={performance.chart}
                                type="line"
                                height={300}
                            />
                        </div>
                    </div>
                </div>

                <div>
                    <MarketOverview />
                </div>
            </div>

            {/* Positions and Recent Trades */}
            <div className="grid grid-cols-2 mb-lg">
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Top Positions</h3>
                        <a href="/portfolio" className="text-primary">View All</a>
                    </div>
                    <div className="card-body">
                        <PositionSummary positions={positions} />
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Recent Trades</h3>
                        <a href="/orders" className="text-primary">View All</a>
                    </div>
                    <div className="card-body">
                        <RecentTrades trades={recentTrades} />
                    </div>
                </div>
            </div>

            {/* News and Alerts */}
            <div className="grid grid-cols-3">
                <div className="col-span-2">
                    <NewsPanel />
                </div>

                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Trading Alerts</h3>
                    </div>
                    <div className="card-body">
                        <div className="alerts-list">
                            <div className="alert alert-success">
                                <strong>RELIANCE</strong> - Target achieved: ₹2,500
                            </div>
                            <div className="alert alert-warning">
                                <strong>TATASTEEL</strong> - Stop loss triggered
                            </div>
                            <div className="alert alert-info">
                                <strong>INFY</strong> - Earnings announcement today
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard; 