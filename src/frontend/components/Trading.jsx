import React, { useEffect, useState } from 'react';
import MarketDepth from './MarketDepth';
import OrderBook from './OrderBook';
import OrderForm from './OrderForm';
import PositionMonitor from './PositionMonitor';
import SymbolSearch from './SymbolSearch';
import TradingChart from './TradingChart';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app';

const Trading = () => {
    const [selectedSymbol, setSelectedSymbol] = useState('RELIANCE');
    const [symbolData, setSymbolData] = useState({
        symbol: 'RELIANCE',
        ltp: 2485.75,
        change: 12.50,
        changePercent: 0.51,
        volume: 1245678,
        high: 2495.00,
        low: 2465.50,
        open: 2475.25
    });
    const [positions, setPositions] = useState([]);
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(false);
    const [watchlist, setWatchlist] = useState([
        'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
        'BHARTIARTL', 'ITC', 'KOTAKBANK', 'LT', 'ASIANPAINT'
    ]);

    useEffect(() => {
        loadTradingData();

        // Set up real-time updates
        const interval = setInterval(loadTradingData, 5000);
        return () => clearInterval(interval);
    }, [selectedSymbol]);

    const loadTradingData = async () => {
        try {
            // Load symbol data, positions, and orders
            const [symbolRes, positionsRes, ordersRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/market-data/${selectedSymbol}`),
                fetch(`${API_BASE_URL}/api/portfolio/positions`),
                fetch(`${API_BASE_URL}/api/orders/active`)
            ]);

            if (symbolRes.ok) {
                const symbolData = await symbolRes.json();
                setSymbolData(symbolData);
            }

            if (positionsRes.ok) {
                const positionsData = await positionsRes.json();
                setPositions(positionsData);
            }

            if (ordersRes.ok) {
                const ordersData = await ordersRes.json();
                setOrders(ordersData);
            }
        } catch (error) {
            console.error('Failed to load trading data:', error);
        }
    };

    const handleSymbolSelect = (symbol) => {
        setSelectedSymbol(symbol);
    };

    const handleOrderPlace = async (orderData) => {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/orders/place`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(orderData)
            });

            if (response.ok) {
                const result = await response.json();
                // Refresh orders and positions
                loadTradingData();
                return { success: true, data: result };
            } else {
                const error = await response.json();
                return { success: false, error: error.message };
            }
        } catch (error) {
            console.error('Order placement failed:', error);
            return { success: false, error: 'Order placement failed' };
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="trading-terminal">
            {/* Header */}
            <div className="trading-header">
                <div className="symbol-info">
                    <h1 className="symbol-name">{symbolData.symbol}</h1>
                    <div className="symbol-price">
                        <span className="ltp">₹{symbolData.ltp.toFixed(2)}</span>
                        <span className={`change ${symbolData.change >= 0 ? 'positive' : 'negative'}`}>
                            {symbolData.change >= 0 ? '+' : ''}{symbolData.change.toFixed(2)}
                            ({symbolData.changePercent.toFixed(2)}%)
                        </span>
                    </div>
                    <div className="symbol-stats">
                        <span>Vol: {symbolData.volume.toLocaleString()}</span>
                        <span>High: ₹{symbolData.high.toFixed(2)}</span>
                        <span>Low: ₹{symbolData.low.toFixed(2)}</span>
                        <span>Open: ₹{symbolData.open.toFixed(2)}</span>
                    </div>
                </div>

                <div className="trading-actions">
                    <button className="btn btn-success btn-lg">
                        BUY ₹{symbolData.ltp.toFixed(2)}
                    </button>
                    <button className="btn btn-danger btn-lg">
                        SELL ₹{symbolData.ltp.toFixed(2)}
                    </button>
                </div>
            </div>

            {/* Main Trading Area */}
            <div className="trading-main">
                {/* Left Panel - Symbol Search & Chart */}
                <div className="trading-left">
                    <div className="card mb-lg">
                        <div className="card-header">
                            <h3 className="card-title">Symbol Search</h3>
                        </div>
                        <div className="card-body">
                            <SymbolSearch
                                selectedSymbol={selectedSymbol}
                                onSymbolSelect={handleSymbolSelect}
                                watchlist={watchlist}
                            />
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title">Price Chart</h3>
                            <div className="chart-controls">
                                <select className="form-select">
                                    <option value="1m">1 Min</option>
                                    <option value="5m">5 Min</option>
                                    <option value="15m">15 Min</option>
                                    <option value="1h">1 Hour</option>
                                    <option value="1d">1 Day</option>
                                </select>
                            </div>
                        </div>
                        <div className="card-body">
                            <TradingChart
                                symbol={selectedSymbol}
                                height={400}
                            />
                        </div>
                    </div>
                </div>

                {/* Center Panel - Order Form & Market Depth */}
                <div className="trading-center">
                    <div className="card mb-lg">
                        <div className="card-header">
                            <h3 className="card-title">Place Order</h3>
                        </div>
                        <div className="card-body">
                            <OrderForm
                                symbol={selectedSymbol}
                                symbolData={symbolData}
                                onOrderPlace={handleOrderPlace}
                                loading={loading}
                            />
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title">Market Depth</h3>
                        </div>
                        <div className="card-body">
                            <MarketDepth symbol={selectedSymbol} />
                        </div>
                    </div>
                </div>

                {/* Right Panel - Positions & Orders */}
                <div className="trading-right">
                    <div className="card mb-lg">
                        <div className="card-header">
                            <h3 className="card-title">Positions</h3>
                            <span className="badge">{positions.length}</span>
                        </div>
                        <div className="card-body">
                            <PositionMonitor
                                positions={positions}
                                onPositionSelect={(position) => setSelectedSymbol(position.symbol)}
                            />
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title">Active Orders</h3>
                            <span className="badge">{orders.length}</span>
                        </div>
                        <div className="card-body">
                            <OrderBook
                                orders={orders}
                                onOrderCancel={(orderId) => {
                                    // Handle order cancellation
                                    console.log('Cancel order:', orderId);
                                }}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Quick Actions Bar */}
            <div className="trading-footer">
                <div className="quick-actions">
                    <button className="action-btn">
                        <span className="action-icon">⚡</span>
                        <span>Market Order</span>
                    </button>
                    <button className="action-btn">
                        <span className="action-icon">📌</span>
                        <span>Stop Loss</span>
                    </button>
                    <button className="action-btn">
                        <span className="action-icon">🎯</span>
                        <span>Target</span>
                    </button>
                    <button className="action-btn">
                        <span className="action-icon">🔄</span>
                        <span>Convert</span>
                    </button>
                    <button className="action-btn">
                        <span className="action-icon">❌</span>
                        <span>Exit All</span>
                    </button>
                </div>

                <div className="margin-info">
                    <span>Available Margin: <strong>₹2,45,678</strong></span>
                    <span>Used Margin: <strong>₹54,322</strong></span>
                </div>
            </div>
        </div>
    );
};

export default Trading; 