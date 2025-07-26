import React, { useEffect, useState } from 'react';
import MarketIndicesWidget from './MarketIndicesWidget';
import RealTimeTradingMonitor from './RealTimeTradingMonitor';

const MarketData = () => {
    const [marketData, setMarketData] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Load market data
        setLoading(false);
    }, []);

    return (
        <div className="market-data-container">
            <h1>Market Data</h1>
            <div className="market-widgets">
                <MarketIndicesWidget />
                <RealTimeTradingMonitor />
            </div>
        </div>
    );
};

export default MarketData; 