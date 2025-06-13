import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import './EliteDashboard.css';

interface Trade {
  id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  timestamp: string;
  status: 'OPEN' | 'CLOSED';
  pnl?: number;
}

interface MarketData {
  symbol: string;
  price: number;
  change: number;
  volume: number;
  timestamp: string;
}

const EliteDashboard: React.FC = () => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [marketData, setMarketData] = useState<MarketData[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const { send, subscribe, isConnected: wsConnected } = useWebSocket({
    onConnect: () => setIsConnected(true),
    onDisconnect: () => setIsConnected(false),
    onError: (error) => console.error('WebSocket error:', error),
    onMessage: (message) => {
      switch (message.type) {
        case 'trade_update':
          handleTradeUpdate(message.data);
          break;
        case 'market_data':
          handleMarketData(message.data);
          break;
        default:
          console.log('Unknown message type:', message.type);
      }
    }
  });

  useEffect(() => {
    // Subscribe to trade updates
    const unsubscribeTrade = subscribe('message:trade_update', (data) => {
      handleTradeUpdate(data);
    });

    // Subscribe to market data updates
    const unsubscribeMarket = subscribe('message:market_data', (data) => {
      handleMarketData(data);
    });

    return () => {
      unsubscribeTrade();
      unsubscribeMarket();
    };
  }, [subscribe]);

  const handleTradeUpdate = (data: Trade) => {
    setTrades(prevTrades => {
      const index = prevTrades.findIndex(t => t.id === data.id);
      if (index >= 0) {
        const newTrades = [...prevTrades];
        newTrades[index] = data;
        return newTrades;
      }
      return [...prevTrades, data];
    });
  };

  const handleMarketData = (data: MarketData) => {
    setMarketData(prevData => {
      const index = prevData.findIndex(d => d.symbol === data.symbol);
      if (index >= 0) {
        const newData = [...prevData];
        newData[index] = data;
        return newData;
      }
      return [...prevData, data];
    });
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(price);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="elite-dashboard">
      <div className="dashboard-header">
        <h1>Elite Trading Dashboard</h1>
        <div className="connection-status">
          Status: {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="market-data-section">
          <h2>Market Data</h2>
          <div className="market-data-grid">
            {marketData.map(data => (
              <div key={data.symbol} className="market-data-card">
                <h3>{data.symbol}</h3>
                <div className="price">{formatPrice(data.price)}</div>
                <div className={`change ${data.change >= 0 ? 'positive' : 'negative'}`}>
                  {data.change >= 0 ? '+' : ''}{data.change.toFixed(2)}%
                </div>
                <div className="volume">Vol: {data.volume.toLocaleString()}</div>
                <div className="timestamp">{formatTimestamp(data.timestamp)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="trades-section">
          <h2>Active Trades</h2>
          <div className="trades-grid">
            {trades.filter(trade => trade.status === 'OPEN').map(trade => (
              <div key={trade.id} className="trade-card">
                <div className="trade-header">
                  <h3>{trade.symbol}</h3>
                  <span className={`trade-type ${trade.type.toLowerCase()}`}>
                    {trade.type}
                  </span>
                </div>
                <div className="trade-details">
                  <div>Quantity: {trade.quantity}</div>
                  <div>Price: {formatPrice(trade.price)}</div>
                  <div>Time: {formatTimestamp(trade.timestamp)}</div>
                  {trade.pnl !== undefined && (
                    <div className={`pnl ${trade.pnl >= 0 ? 'positive' : 'negative'}`}>
                      P&L: {formatPrice(trade.pnl)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EliteDashboard; 