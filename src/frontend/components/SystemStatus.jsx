import React from 'react';
import SystemHealthDashboard from './SystemHealthDashboard';
import SystemHealthMonitor from './SystemHealthMonitor';

const SystemStatus = () => {
    return (
        <div className="system-status-container">
            <h1>System Status</h1>
            <div className="system-status-content">
                <SystemHealthDashboard />
                <SystemHealthMonitor />
            </div>
        </div>
    );
};

export default SystemStatus; 