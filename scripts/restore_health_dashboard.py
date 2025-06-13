#!/usr/bin/env python3
"""
🏥 HEALTH MONITORING DASHBOARD RESTORATION
==========================================

This script restores the missing health monitoring system on the dashboard
and verifies all monitoring components are working correctly.
"""

import os
import sys
import json
import requests
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def restore_health_dashboard_component():
    """Restore the health monitoring component to the dashboard"""
    
    health_component_code = '''import React, { useState, useEffect } from 'react';
import {
    Card,
    CardContent,
    Typography,
    Grid,
    Chip,
    Box,
    LinearProgress,
    Alert
} from '@mui/material';
import {
    CheckCircle,
    Error,
    Warning,
    Memory,
    Storage,
    NetworkCheck
} from '@mui/icons-material';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const SystemHealthMonitor = () => {
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchHealthData = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/health`);
            
            if (response.ok) {
                const data = await response.json();
                setHealthData(data);
                setError(null);
            } else {
                throw new Error('Failed to fetch health data');
            }
        } catch (err) {
            console.error('Health data fetch error:', err);
            setError('Unable to fetch system health data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHealthData();
        const interval = setInterval(fetchHealthData, 30000); // Update every 30 seconds
        return () => clearInterval(interval);
    }, []);

    const getStatusIcon = (status) => {
        switch (status?.toLowerCase()) {
            case 'healthy':
            case 'pass':
                return <CheckCircle color="success" />;
            case 'warning':
            case 'partial':
                return <Warning color="warning" />;
            case 'unhealthy':
            case 'fail':
                return <Error color="error" />;
            default:
                return <Warning color="disabled" />;
        }
    };

    const getStatusColor = (status) => {
        switch (status?.toLowerCase()) {
            case 'healthy':
            case 'pass':
                return 'success';
            case 'warning':
            case 'partial':
                return 'warning';
            case 'unhealthy':
            case 'fail':
                return 'error';
            default:
                return 'default';
        }
    };

    if (loading) {
        return (
            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        System Health
                    </Typography>
                    <LinearProgress />
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        System Health
                    </Typography>
                    <Alert severity="error">{error}</Alert>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        System Health Monitor
                    </Typography>
                    <Chip
                        label={healthData?.status || 'Unknown'}
                        color={getStatusColor(healthData?.status)}
                        icon={getStatusIcon(healthData?.status)}
                        size="small"
                    />
                </Box>

                <Grid container spacing={2}>
                    {/* Overall System Status */}
                    <Grid item xs={12}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                            {getStatusIcon(healthData?.status)}
                            <Typography variant="body1" sx={{ ml: 1 }}>
                                Overall System: {healthData?.status || 'Unknown'}
                            </Typography>
                        </Box>
                    </Grid>

                    {/* Component Health */}
                    {healthData?.components && Object.entries(healthData.components).map(([component, data]) => (
                        <Grid item xs={12} sm={6} key={component}>
                            <Box sx={{ display: 'flex', alignItems: 'center', p: 1, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                                {getStatusIcon(data.status)}
                                <Box sx={{ ml: 1, flexGrow: 1 }}>
                                    <Typography variant="body2" fontWeight="bold">
                                        {component.replace('_', ' ').toUpperCase()}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {data.message || 'No details available'}
                                    </Typography>
                                </Box>
                                <Chip
                                    label={data.status}
                                    color={getStatusColor(data.status)}
                                    size="small"
                                />
                            </Box>
                        </Grid>
                    ))}

                    {/* System Metrics */}
                    {healthData?.metrics && (
                        <Grid item xs={12}>
                            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                                System Metrics
                            </Typography>
                            <Grid container spacing={1}>
                                {healthData.metrics.memory_usage && (
                                    <Grid item xs={4}>
                                        <Box sx={{ textAlign: 'center' }}>
                                            <Memory color="primary" />
                                            <Typography variant="caption" display="block">
                                                Memory: {healthData.metrics.memory_usage}%
                                            </Typography>
                                        </Box>
                                    </Grid>
                                )}
                                {healthData.metrics.disk_usage && (
                                    <Grid item xs={4}>
                                        <Box sx={{ textAlign: 'center' }}>
                                            <Storage color="primary" />
                                            <Typography variant="caption" display="block">
                                                Disk: {healthData.metrics.disk_usage}%
                                            </Typography>
                                        </Box>
                                    </Grid>
                                )}
                                {healthData.metrics.uptime && (
                                    <Grid item xs={4}>
                                        <Box sx={{ textAlign: 'center' }}>
                                            <NetworkCheck color="primary" />
                                            <Typography variant="caption" display="block">
                                                Uptime: {healthData.metrics.uptime}
                                            </Typography>
                                        </Box>
                                    </Grid>
                                )}
                            </Grid>
                        </Grid>
                    )}
                </Grid>

                <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                    Last updated: {new Date().toLocaleTimeString()}
                </Typography>
            </CardContent>
        </Card>
    );
};

export default SystemHealthMonitor;'''

    # Write the health component
    component_path = "src/frontend/components/SystemHealthMonitor.jsx"
    
    try:
        os.makedirs(os.path.dirname(component_path), exist_ok=True)
        with open(component_path, 'w', encoding='utf-8') as f:
            f.write(health_component_code)
        
        print("✅ SystemHealthMonitor component created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create SystemHealthMonitor component: {e}")
        return False

def add_health_monitor_to_dashboard():
    """Add the health monitor to the main dashboard"""
    
    dashboard_files = [
        "src/frontend/components/ComprehensiveTradingDashboard.jsx",
        "src/frontend/components/AutonomousTradingDashboard.jsx"
    ]
    
    import_statement = "import SystemHealthMonitor from './SystemHealthMonitor';"
    component_usage = """
                    {/* System Health Monitor */}
                    <Grid item xs={12} md={6}>
                        <SystemHealthMonitor />
                    </Grid>"""
    
    for dashboard_file in dashboard_files:
        if os.path.exists(dashboard_file):
            try:
                with open(dashboard_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add import if not present
                if "SystemHealthMonitor" not in content:
                    # Find the import section and add our import
                    import_section = content.find("import React")
                    if import_section != -1:
                        # Find the end of imports
                        import_end = content.find("const ", import_section)
                        if import_end != -1:
                            content = content[:import_end] + import_statement + "\n\n" + content[import_end:]
                    
                    # Add component to the grid (look for existing Grid containers)
                    grid_pattern = "<Grid container spacing={3}>"
                    grid_pos = content.find(grid_pattern)
                    if grid_pos != -1:
                        # Find the end of the first grid item and add our component
                        next_grid = content.find("</Grid>", grid_pos + len(grid_pattern))
                        if next_grid != -1:
                            content = content[:next_grid] + component_usage + "\n" + content[next_grid:]
                    
                    # Write back the modified content
                    with open(dashboard_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"✅ Added SystemHealthMonitor to {dashboard_file}")
                else:
                    print(f"ℹ️ SystemHealthMonitor already present in {dashboard_file}")
                    
            except Exception as e:
                print(f"❌ Failed to modify {dashboard_file}: {e}")

def test_health_endpoints():
    """Test health monitoring endpoints"""
    print("🔍 Testing health monitoring endpoints...")
    
    endpoints = [
        "/health",
        "/api/monitoring/system-stats",
        "/api/monitoring/trading-status",
        "/api/monitoring/connections"
    ]
    
    base_url = "http://localhost:8000"
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint}: Working")
            else:
                print(f"⚠️ {endpoint}: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint}: Connection failed - {e}")

def main():
    """Main restoration function"""
    print("🏥 RESTORING HEALTH MONITORING DASHBOARD")
    print("=" * 50)
    
    # Step 1: Create the health monitor component
    print("1. Creating SystemHealthMonitor component...")
    if restore_health_dashboard_component():
        print("   ✅ Component created successfully")
    else:
        print("   ❌ Failed to create component")
        return False
    
    # Step 2: Add to dashboards
    print("2. Adding health monitor to dashboards...")
    add_health_monitor_to_dashboard()
    
    # Step 3: Test endpoints
    print("3. Testing health endpoints...")
    test_health_endpoints()
    
    print("\n🎉 Health monitoring dashboard restoration complete!")
    print("📝 Next steps:")
    print("   1. Rebuild the frontend: cd src/frontend && npm run build")
    print("   2. Restart the application")
    print("   3. Check the dashboard for the new Health Monitor component")
    
    return True

if __name__ == "__main__":
    main() 