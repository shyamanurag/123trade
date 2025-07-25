import React from 'react';

const LoadingSpinner = ({
    size = 'medium',
    color = 'primary',
    text = null,
    className = ''
}) => {
    const getSizeClass = () => {
        switch (size) {
            case 'small': return 'spinner-sm';
            case 'large': return 'spinner-lg';
            case 'xl': return 'spinner-xl';
            default: return '';
        }
    };

    const getColorClass = () => {
        switch (color) {
            case 'success': return 'spinner-success';
            case 'warning': return 'spinner-warning';
            case 'error': return 'spinner-error';
            case 'white': return 'spinner-white';
            default: return 'spinner-primary';
        }
    };

    return (
        <div className={`loading-spinner-container ${className}`}>
            <div className={`loading-spinner ${getSizeClass()} ${getColorClass()}`}></div>
            {text && <span className="loading-text">{text}</span>}
        </div>
    );
};

export default LoadingSpinner; 