import React from 'react';

const MetricCard = ({
    title,
    value,
    subValue,
    change,
    changePercent,
    icon,
    variant = 'default',
    onClick,
    loading = false
}) => {
    const getVariantClass = () => {
        switch (variant) {
            case 'success': return 'metric-card-success';
            case 'danger': return 'metric-card-danger';
            case 'warning': return 'metric-card-warning';
            case 'info': return 'metric-card-info';
            default: return '';
        }
    };

    const getChangeColor = () => {
        if (change === undefined || change === null) return '';
        return change >= 0 ? 'text-success' : 'text-error';
    };

    return (
        <div
            className={`metric-card ${getVariantClass()} ${onClick ? 'clickable' : ''}`}
            onClick={onClick}
        >
            <div className="metric-header">
                <div className="metric-icon">{icon}</div>
                <div className="metric-title">{title}</div>
            </div>

            <div className="metric-body">
                {loading ? (
                    <div className="metric-loading">
                        <div className="loading-spinner"></div>
                    </div>
                ) : (
                    <>
                        <div className="metric-value">{value}</div>

                        {subValue && (
                            <div className="metric-subvalue">{subValue}</div>
                        )}

                        {(change !== undefined || changePercent !== undefined) && (
                            <div className={`metric-change ${getChangeColor()}`}>
                                {change !== undefined && (
                                    <span className="change-amount">
                                        {change >= 0 ? '+' : ''}
                                        {typeof change === 'number' ? change.toLocaleString('en-IN') : change}
                                    </span>
                                )}
                                {changePercent !== undefined && (
                                    <span className="change-percent">
                                        ({changePercent >= 0 ? '+' : ''}
                                        {typeof changePercent === 'number' ? changePercent.toFixed(2) : changePercent}%)
                                    </span>
                                )}
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

export default MetricCard; 