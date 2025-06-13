import React, { useState, useEffect } from 'react';
import EliteTradeCard from './EliteTradeCard';
import './EliteDashboard.css';

const EliteDashboard = () => {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastScanTime, setLastScanTime] = useState(null);

    const fetchRecommendations = async () => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch('/api/elite-recommendations', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch recommendations');
            }

            const data = await response.json();
            setRecommendations(data.recommendations);
            setLastScanTime(new Date(data.scan_timestamp));
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRecommendations();
    }, []);

    return (
        <div className="elite-dashboard">
            <div className="dashboard-header">
                <h1>Elite Trade Recommendations</h1>
                <p className="subtitle">10/10 Perfect Setup Opportunities Only</p>
                
                <div className="scan-controls">
                    <button 
                        className="scan-button"
                        onClick={fetchRecommendations}
                        disabled={loading}
                    >
                        {loading ? 'Scanning...' : 'Scan for Elite Trades'}
                    </button>
                    {lastScanTime && (
                        <span className="last-scan">
                            Last scan: {lastScanTime.toLocaleString()}
                        </span>
                    )}
                </div>
            </div>

            {error && (
                <div className="error-message">
                    Error: {error}
                </div>
            )}

            {!loading && recommendations.length === 0 && (
                <div className="no-recommendations">
                    <div className="empty-state">
                        <h2>No Elite Trades Found</h2>
                        <p>Perfect 10/10 setups are rare. Here's what we're looking for:</p>
                        <ul>
                            <li>Perfect technical alignment across all timeframes</li>
                            <li>Strong volume confirmation with institutional activity</li>
                            <li>Clear pattern completion with high historical reliability</li>
                            <li>Optimal market regime conditions</li>
                            <li>Momentum alignment across timeframes</li>
                            <li>Smart money confirmation via options flow</li>
                        </ul>
                        <p>Try scanning again later or adjust your criteria.</p>
                    </div>
                </div>
            )}

            <div className="elite-trades-container">
                {recommendations.map((trade) => (
                    <EliteTradeCard key={trade.recommendation_id} trade={trade} />
                ))}
            </div>
        </div>
    );
};

export default EliteDashboard; 