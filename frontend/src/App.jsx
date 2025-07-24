import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [isConnected, setIsConnected] = useState(false)
  const [trades, setTrades] = useState([])
  const [userAnalytics, setUserAnalytics] = useState([])
  const [portfolioData, setPortfolioData] = useState(null)
  const [marketData, setMarketData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    console.log('Fetching data...');
    const fetchData = () => {
      fetch('http://localhost:8000/health').then(res => res.json()).then(() => setIsConnected(true)).catch(() => setIsConnected(false));
      fetch('http://localhost:8000/api/trades').then(res => res.json()).then(data => { console.log('Data fetched:', data); setTrades(data || []) }).catch(err => setError(err.message));
      fetch('http://localhost:8000/api/users/performance').then(res => res.json()).then(data => { console.log('Data fetched:', data); setUserAnalytics(data || []) }).catch(err => setError(err.message));
      fetch('http://localhost:8000/api/portfolio').then(res => res.json()).then(setPortfolioData).catch(err => setError(err.message));
      fetch('http://localhost:8000/api/market/data').then(res => res.json()).then(setMarketData).catch(err => setError(err.message));
    };
    fetchData();
    const interval = setInterval(fetchData, 30000); // Poll every 30s for live updates
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>🚀 Quantum Crypto Trading System</h1>
        <div className="status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '✅ Connected' : '❌ Disconnected'}
          </span>
        </div>
      </header>

      <main className="App-main">
        {error && <p style={{ color: 'red' }}>{error}</p>}

        <div className="dashboard-grid">
          <div className="card">
            <h2>Portfolio</h2>
            {portfolioData ? <pre>{JSON.stringify(portfolioData, null, 2)}</pre> : <p>Loading...</p>}
          </div>

          <div className="card">
            <h2>Market Data</h2>
            {marketData ? <pre>{JSON.stringify(marketData, null, 2)}</pre> : <p>Loading...</p>}
          </div>

          <div className="card">
            <h2>Strategies</h2>
            <p>Trading strategies loading...</p>
          </div>

          <div className="card">
            <h2>System Status</h2>
            <p>System health monitoring...</p>
          </div>
        </div>

        <section>
          <h2>Trade Details</h2>
          {trades.length ? (
            <table>
              <thead><tr><th>ID</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Status</th></tr></thead>
              <tbody>{trades.map(t => <tr key={t.trade_id}><td>{t.trade_id}</td><td>{t.symbol}</td><td>{t.side}</td><td>{t.quantity}</td><td>{t.price}</td><td>{t.status}</td></tr>)}</tbody>
            </table>
          ) : <p>No trades</p>}
        </section>
        <section>
          <h2>User Analytics</h2>
          {userAnalytics.length ? (
            <table>
              <thead><tr><th>User ID</th><th>Trades</th><th>Win %</th><th>PnL</th><th>Unrealized</th></tr></thead>
              <tbody>{userAnalytics.map(u => <tr key={u.user_id}><td>{u.user_id}</td><td>{u.total_trades_today}</td><td>{u.win_rate}%</td><td>{u.total_pnl}</td><td>{u.unrealized_pnl}</td></tr>)}</tbody>
            </table>
          ) : <p>No analytics</p>}
        </section>
      </main>
    </div>
  )
}

export default App 