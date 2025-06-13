import React, { useState } from 'react';
import './EliteTradeCard.css';

const EliteTradeCard = ({ trade }) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div className={`elite-trade-card ${trade.direction.toLowerCase()}`}>
            <div className="card-header">
                <div className="symbol-info">
                    <h2>{trade.symbol}</h2>
                    <span className="direction-badge">{trade.direction}</span>
                </div>
                <div className="timestamp">
                    <div className="generated-time">
                        Generated: {new Date(trade.timestamp).toLocaleString()}
                    </div>
                    <div className={`validity ${new Date() > new Date(trade.valid_until) ? 'expired' : ''}`}>
                        Valid until: {new Date(trade.valid_until).toLocaleString()}
                    </div>
                </div>
            </div>

            <div className="trade-levels">
                <div className="level-group">
                    <label>Entry</label>
                    <span className="price entry">₹{trade.entry_price.toFixed(2)}</span>
                </div>
                <div className="level-group">
                    <label>Stop Loss</label>
                    <span className="price stop-loss">₹{trade.stop_loss.toFixed(2)}</span>
                </div>
                <div className="level-group">
                    <label>Targets</label>
                    <div className="targets">
                        <span className="price target">T1: ₹{trade.primary_target.toFixed(2)}</span>
                        <span className="price target">T2: ₹{trade.secondary_target.toFixed(2)}</span>
                        <span className="price target">T3: ₹{trade.tertiary_target.toFixed(2)}</span>
                    </div>
                </div>
                <div className="level-group">
                    <label>Risk/Reward</label>
                    <span className="risk-reward">
                        1:{trade.risk_metrics.risk_reward_ratio.toFixed(1)}
                    </span>
                </div>
            </div>

            <div className="confluence-summary">
                <h3>Perfect Confluence Factors ({trade.confluence_factors.length})</h3>
                <div className="factor-pills">
                    {trade.confluence_factors.slice(0, 5).map((factor, idx) => (
                        <span key={idx} className="factor-pill">{factor}</span>
                    ))}
                    {trade.confluence_factors.length > 5 && (
                        <span className="more-factors">
                            +{trade.confluence_factors.length - 5} more
                        </span>
                    )}
                </div>
            </div>

            <div className="entry-conditions">
                <h4>Entry Conditions</h4>
                <ul>
                    {trade.entry_conditions.map((condition, idx) => (
                        <li key={idx}>{condition}</li>
                    ))}
                </ul>
            </div>

            <div className="trade-management">
                <div className="position-sizing">
                    <h4>Position Sizing</h4>
                    <div className="sizing-info">
                        <span>Recommended: {trade.position_sizing.recommended_percent}%</span>
                        <span>Range: {trade.position_sizing.minimum_percent}% - {trade.position_sizing.maximum_percent}%</span>
                    </div>
                </div>

                <div className="scaling-plan">
                    <h4>Scaling Strategy</h4>
                    <div className="scaling-details">
                        <div>Entry: {trade.scaling_plan.entry_allocation.join('/')}%</div>
                        <div>Exit: {trade.scaling_plan.exit_allocation.join('/')}% at T1/T2/T3</div>
                    </div>
                </div>
            </div>

            <button 
                className="expand-button"
                onClick={() => setExpanded(!expanded)}
            >
                {expanded ? 'Show Less' : 'Show Full Analysis'}
            </button>

            {expanded && (
                <div className="expanded-details">
                    <div className="score-breakdown">
                        <h4>Perfect Score Breakdown</h4>
                        <div className="score-grid">
                            <div className="score-item">
                                <label>Technical</label>
                                <span className="score">{trade.technical_score.toFixed(1)}/10</span>
                            </div>
                            <div className="score-item">
                                <label>Volume</label>
                                <span className="score">{trade.volume_score.toFixed(1)}/10</span>
                            </div>
                            <div className="score-item">
                                <label>Pattern</label>
                                <span className="score">{trade.pattern_score.toFixed(1)}/10</span>
                            </div>
                            <div className="score-item">
                                <label>Regime</label>
                                <span className="score">{trade.regime_score.toFixed(1)}/10</span>
                            </div>
                            <div className="score-item">
                                <label>Momentum</label>
                                <span className="score">{trade.momentum_score.toFixed(1)}/10</span>
                            </div>
                            <div className="score-item">
                                <label>Smart Money</label>
                                <span className="score">{trade.smart_money_score.toFixed(1)}/10</span>
                            </div>
                        </div>
                    </div>

                    <div className="key-levels">
                        <h4>Key Price Levels</h4>
                        <table>
                            <tbody>
                                <tr>
                                    <td>Support</td>
                                    <td>₹{trade.key_levels.support.toFixed(2)}</td>
                                </tr>
                                <tr>
                                    <td>Resistance</td>
                                    <td>₹{trade.key_levels.resistance.toFixed(2)}</td>
                                </tr>
                                <tr>
                                    <td>Pivot</td>
                                    <td>₹{trade.key_levels.pivot.toFixed(2)}</td>
                                </tr>
                                <tr>
                                    <td>VWAP</td>
                                    <td>₹{trade.key_levels.vwap.toFixed(2)}</td>
                                </tr>
                                <tr>
                                    <td>POC</td>
                                    <td>₹{trade.key_levels.poc.toFixed(2)}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div className="invalidation-conditions">
                        <h4>Setup Invalidation</h4>
                        <ul className="warning-list">
                            {trade.invalidation_conditions.map((condition, idx) => (
                                <li key={idx}>{condition}</li>
                            ))}
                        </ul>
                    </div>

                    <div className="trade-summary">
                        <pre>{trade.generate_summary()}</pre>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EliteTradeCard; 