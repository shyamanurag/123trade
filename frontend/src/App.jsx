import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [isConnected, setIsConnected] = useState(false)
  const [trades, setTrades] = useState([])
  const [userAnalytics, setUserAnalytics] = useState([])
  const [portfolioData, setPortfolioData] = useState(null)
  const [marketData, setMarketData] = useState(null)
  const [strategyPerformance, setStrategyPerformance] = useState([])
  const [dailyPnL, setDailyPnL] = useState([])
  const [activeTab, setActiveTab] = useState('dashboard')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    console.log('Fetching data...')
    const fetchData = () => {
      setLoading(true)

      // Health check
      fetch('http://localhost:8000/health')
        .then(res => res.json())
        .then(() => setIsConnected(true))
        .catch(() => setIsConnected(false))

      // Fetch trades
      fetch('http://localhost:8000/api/trades')
        .then(res => res.json())
        .then(data => {
          console.log('Trades fetched:', data)
          setTrades(data.data || data || [])
        })
        .catch(err => setError('Failed to load trades: ' + err.message))

      // Fetch user analytics
      fetch('http://localhost:8000/api/users/performance?user_id=1')
        .then(res => res.json())
        .then(data => {
          console.log('User analytics fetched:', data)
          setUserAnalytics(data.data ? [data.data] : [])
        })
        .catch(err => setError('Failed to load analytics: ' + err.message))

      // Fetch dashboard summary
      fetch('http://localhost:8000/api/dashboard/summary')
        .then(res => res.json())
        .then(data => {
          console.log('Dashboard data:', data)
          setPortfolioData(data.portfolio || data)
          setStrategyPerformance(data.strategies || [])
        })
        .catch(err => setError('Failed to load dashboard: ' + err.message))

      // Fetch daily P&L
      fetch('http://localhost:8000/api/monitoring/daily-pnl')
        .then(res => res.json())
        .then(data => {
          setDailyPnL(data.daily_pnl || [])
        })
        .catch(err => setError('Failed to load P&L: ' + err.message))

      setLoading(false)
    }

    fetchData()
    const interval = setInterval(fetchData, 30000) // Poll every 30s
    return () => clearInterval(interval)
  }, [])

  const renderDashboard = () => (
    <div className="dashboard-content">
      <div className="metrics-grid">
        <div className="metric-card">
          <h3>Total Trades</h3>
          <div className="metric-value">{trades.length}</div>
        </div>
        <div className="metric-card">
          <h3>Active Strategies</h3>
          <div className="metric-value">{strategyPerformance.length}</div>
        </div>
        <div className="metric-card">
          <h3>Daily P&L</h3>
          <div className="metric-value">
            ${dailyPnL.reduce((sum, day) => sum + (day.total_pnl || 0), 0).toFixed(2)}
          </div>
        </div>
        <div className="metric-card">
          <h3>Connection</h3>
          <div className={`metric-value ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? 'Live' : 'Offline'}
          </div>
        </div>
      </div>

      <div className="charts-section">
        <div className="chart-card">
          <h3>Daily P&L Trend</h3>
          {dailyPnL.length > 0 ? (
            <div className="pnl-chart">
              {dailyPnL.map((day, index) => (
                <div key={index} className="pnl-bar">
                  <div className="pnl-date">{day.date}</div>
                  <div className={`pnl-amount ${day.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                    ${day.total_pnl?.toFixed(2) || '0.00'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p>No P&L data available</p>
          )}
        </div>
      </div>
    </div>
  )

  const renderTradeDetails = () => (
    <div className="trade-details-content">
      <h2>Trade History</h2>
      {trades.length > 0 ? (
        <div className="table-container">
          <table className="trades-table">
            <thead>
              <tr>
                <th>Trade ID</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>P&L</th>
                <th>Status</th>
                <th>Strategy</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.map(trade => (
                <tr key={trade.trade_id || trade.id}>
                  <td>{trade.trade_id || trade.id}</td>
                  <td>{trade.symbol}</td>
                  <td className={`side ${trade.side?.toLowerCase()}`}>{trade.side}</td>
                  <td>{trade.quantity}</td>
                  <td>${trade.price?.toFixed(4) || '0.0000'}</td>
                  <td className={`pnl ${(trade.pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                    ${trade.pnl?.toFixed(2) || '0.00'}
                  </td>
                  <td className={`status ${trade.status?.toLowerCase()}`}>{trade.status}</td>
                  <td>{trade.strategy || 'Manual'}</td>
                  <td>{trade.executed_at || trade.created_at || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="no-data">
          <p>No trades found</p>
          <small>Trades will appear here as they are executed</small>
        </div>
      )}
    </div>
  )

  const renderAnalytics = () => (
    <div className="analytics-content">
      <h2>Performance Analytics</h2>

      <div className="analytics-grid">
        <div className="analytics-card">
          <h3>User Performance</h3>
          {userAnalytics.length > 0 ? (
            <div className="user-stats">
              {userAnalytics.map((user, index) => (
                <div key={index} className="user-row">
                  <div className="stat">
                    <label>Total Trades Today:</label>
                    <span>{user.total_trades_today}</span>
                  </div>
                  <div className="stat">
                    <label>Win Rate:</label>
                    <span>{user.win_rate}%</span>
                  </div>
                  <div className="stat">
                    <label>Total P&L:</label>
                    <span className={user.total_pnl >= 0 ? 'positive' : 'negative'}>
                      ${user.total_pnl?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                  <div className="stat">
                    <label>Unrealized P&L:</label>
                    <span className={user.unrealized_pnl >= 0 ? 'positive' : 'negative'}>
                      ${user.unrealized_pnl?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p>No user analytics available</p>
          )}
        </div>

        <div className="analytics-card">
          <h3>Strategy Performance</h3>
          {strategyPerformance.length > 0 ? (
            <div className="strategy-list">
              {strategyPerformance.map((strategy, index) => (
                <div key={index} className="strategy-item">
                  <div className="strategy-name">{strategy.name}</div>
                  <div className="strategy-metrics">
                    <span>P&L: ${strategy.pnl?.toFixed(2) || '0.00'}</span>
                    <span>Trades: {strategy.trades || 0}</span>
                    <span>Win Rate: {strategy.win_rate || 0}%</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p>No strategy data available</p>
          )}
        </div>
      </div>
    </div>
  )

  const renderPortfolio = () => (
    <div className="portfolio-content">
      <h2>Portfolio Overview</h2>
      {portfolioData ? (
        <div className="portfolio-details">
          <pre>{JSON.stringify(portfolioData, null, 2)}</pre>
        </div>
      ) : (
        <p>Loading portfolio data...</p>
      )}
    </div>
  )

  return (
    <div className="App">
      <header className="app-header">
        <h1>🚀 Quantum Crypto Trading System</h1>
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '✅ Connected' : '❌ Disconnected'}
          </span>
        </div>
      </header>

      <nav className="navigation">
        <button
          className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Dashboard
        </button>
        <button
          className={`nav-tab ${activeTab === 'trades' ? 'active' : ''}`}
          onClick={() => setActiveTab('trades')}
        >
          📋 Trade Details
        </button>
        <button
          className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          📈 Analytics
        </button>
        <button
          className={`nav-tab ${activeTab === 'portfolio' ? 'active' : ''}`}
          onClick={() => setActiveTab('portfolio')}
        >
          💼 Portfolio
        </button>
      </nav>

      <main className="app-main">
        {loading && <div className="loading">Loading...</div>}
        {error && <div className="error-message">{error}</div>}

        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'trades' && renderTradeDetails()}
        {activeTab === 'analytics' && renderAnalytics()}
        {activeTab === 'portfolio' && renderPortfolio()}
      </main>
    </div>
  )
}

export default App 