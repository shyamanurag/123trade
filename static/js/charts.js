// Trading Platform Charts using Chart.js
class TradingCharts {
    constructor() {
        this.charts = {};
        this.initCharts();
    }

    initCharts() {
        this.createPerformanceChart();
        this.createAnalyticsChart();
    }

    createPerformanceChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;

        // Sample performance data
        const performanceData = {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
            datasets: [{
                label: 'Portfolio Value (₹)',
                data: [100000, 102000, 98000, 105000, 108000, 112000, 115000],
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }, {
                label: 'Benchmark (NIFTY)',
                data: [100000, 101000, 99000, 103000, 106000, 109000, 111000],
                borderColor: '#2196F3',
                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.4
            }]
        };

        this.charts.performance = new Chart(ctx, {
            type: 'line',
            data: performanceData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Portfolio Performance vs Benchmark',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function (context) {
                                return context.dataset.label + ': ₹' +
                                    context.parsed.y.toLocaleString('en-IN');
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Month'
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Value (₹)'
                        },
                        ticks: {
                            callback: function (value) {
                                return '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    createAnalyticsChart() {
        const ctx = document.getElementById('analyticsChart');
        if (!ctx) return;

        // Sample analytics data
        const analyticsData = {
            labels: ['Equity', 'Options', 'Futures', 'Commodities', 'Currency'],
            datasets: [{
                label: 'Trading Volume Distribution',
                data: [45, 25, 15, 10, 5],
                backgroundColor: [
                    '#4CAF50',
                    '#2196F3',
                    '#FF9800',
                    '#F44336',
                    '#9C27B0'
                ],
                borderColor: [
                    '#45a049',
                    '#1976D2',
                    '#F57C00',
                    '#D32F2F',
                    '#7B1FA2'
                ],
                borderWidth: 2,
                hoverOffset: 10
            }]
        };

        this.charts.analytics = new Chart(ctx, {
            type: 'doughnut',
            data: analyticsData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Trading Volume by Asset Class',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return context.label + ': ' + context.parsed + '%';
                            }
                        }
                    }
                },
                cutout: '50%',
                animation: {
                    animateRotate: true,
                    animateScale: true
                }
            }
        });
    }

    // Update charts with new data
    updatePerformanceChart(newData) {
        if (this.charts.performance) {
            this.charts.performance.data = newData;
            this.charts.performance.update();
        }
    }

    updateAnalyticsChart(newData) {
        if (this.charts.analytics) {
            this.charts.analytics.data = newData;
            this.charts.analytics.update();
        }
    }

    // Create live price chart for a symbol
    createPriceChart(containerId, symbol) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return;

        // Generate sample price data
        const priceData = this.generatePriceData(symbol);

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: priceData.labels,
                datasets: [{
                    label: `${symbol} Price`,
                    data: priceData.prices,
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${symbol} - Live Price Chart`,
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        type: 'time',
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        }
                    },
                    y: {
                        display: true,
                        ticks: {
                            callback: function (value) {
                                return '₹' + value.toFixed(2);
                            }
                        }
                    }
                }
            }
        });

        return chart;
    }

    // Generate sample price data
    generatePriceData(symbol) {
        const now = new Date();
        const labels = [];
        const prices = [];
        let basePrice = 1000; // Base price

        // Generate last 30 data points (30 minutes)
        for (let i = 29; i >= 0; i--) {
            const time = new Date(now.getTime() - i * 60000); // 1 minute intervals
            labels.push(time);

            // Generate realistic price movement
            const change = (Math.random() - 0.5) * 10; // Random change up to ±5
            basePrice += change;
            prices.push(Math.max(basePrice, 1)); // Ensure price doesn't go below 1
        }

        return { labels, prices };
    }

    // Create volume chart
    createVolumeChart(containerId, data) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Volume',
                    data: data.volumes,
                    backgroundColor: 'rgba(33, 150, 243, 0.7)',
                    borderColor: '#2196F3',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Trading Volume',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: true
                    },
                    y: {
                        display: true,
                        ticks: {
                            callback: function (value) {
                                return value.toLocaleString('en-IN');
                            }
                        }
                    }
                }
            }
        });

        return chart;
    }

    // Create P&L chart
    createPnLChart(containerId, data) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'P&L',
                    data: data.pnl,
                    backgroundColor: function (context) {
                        const value = context.parsed.y;
                        return value >= 0 ? 'rgba(76, 175, 80, 0.7)' : 'rgba(244, 67, 54, 0.7)';
                    },
                    borderColor: function (context) {
                        const value = context.parsed.y;
                        return value >= 0 ? '#4CAF50' : '#F44336';
                    },
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Daily P&L',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed.y;
                                const sign = value >= 0 ? '+' : '';
                                return 'P&L: ' + sign + '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true
                    },
                    y: {
                        display: true,
                        ticks: {
                            callback: function (value) {
                                const sign = value >= 0 ? '+' : '';
                                return sign + '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                }
            }
        });

        return chart;
    }

    // Destroy a chart
    destroyChart(chartName) {
        if (this.charts[chartName]) {
            this.charts[chartName].destroy();
            delete this.charts[chartName];
        }
    }

    // Destroy all charts
    destroyAllCharts() {
        Object.keys(this.charts).forEach(chartName => {
            this.destroyChart(chartName);
        });
    }

    // Resize all charts
    resizeCharts() {
        Object.values(this.charts).forEach(chart => {
            chart.resize();
        });
    }
}

// Initialize charts when DOM is loaded
let tradingCharts;

document.addEventListener('DOMContentLoaded', function () {
    // Wait a bit for the platform to initialize
    setTimeout(() => {
        tradingCharts = new TradingCharts();
    }, 1000);
});

// Handle window resize
window.addEventListener('resize', function () {
    if (tradingCharts) {
        tradingCharts.resizeCharts();
    }
}); 