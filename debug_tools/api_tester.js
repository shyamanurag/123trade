/**
 * Comprehensive API Testing and Debugging Tool
 * For AlgoAuto Trading System
 */

const https = require('https');
const http = require('http');
const { performance } = require('perf_hooks');
const fs = require('fs');
const path = require('path');

class ApiTester {
    constructor(baseUrl = 'https://trade123-l3zp7.ondigitalocean.app') {
        this.baseUrl = baseUrl;
        this.authToken = null;
        this.testResults = [];
        this.logFile = `debug_tools/api_test_log_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    }

    // Color codes for console output
    colors = {
        reset: '\x1b[0m',
        bright: '\x1b[1m',
        red: '\x1b[31m',
        green: '\x1b[32m',
        yellow: '\x1b[33m',
        blue: '\x1b[34m',
        magenta: '\x1b[35m',
        cyan: '\x1b[36m'
    };

    log(message, color = 'reset') {
        console.log(`${this.colors[color]}${message}${this.colors.reset}`);
    }

    async makeRequest(endpoint, options = {}) {
        const {
            method = 'GET',
            data = null,
            headers = {},
            timeout = 10000,
            expectedStatus = [200, 201, 202]
        } = options;

        const url = new URL(endpoint, this.baseUrl);
        const isHttps = url.protocol === 'https:';
        const requestModule = isHttps ? https : http;

        const requestOptions = {
            hostname: url.hostname,
            port: url.port || (isHttps ? 443 : 80),
            path: url.pathname + url.search,
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'AlgoAuto-Debug-Tool/1.0',
                'Accept': 'application/json',
                ...headers
            },
            timeout: timeout
        };

        if (this.authToken) {
            requestOptions.headers['Authorization'] = `Bearer ${this.authToken}`;
        }

        if (data) {
            const jsonData = JSON.stringify(data);
            requestOptions.headers['Content-Length'] = Buffer.byteLength(jsonData);
        }

        return new Promise((resolve, reject) => {
            const startTime = performance.now();

            const req = requestModule.request(requestOptions, (res) => {
                let responseData = '';

                res.on('data', (chunk) => {
                    responseData += chunk;
                });

                res.on('end', () => {
                    const endTime = performance.now();
                    const responseTime = Math.round(endTime - startTime);

                    let parsedData = null;
                    let parseError = null;

                    try {
                        parsedData = JSON.parse(responseData);
                    } catch (e) {
                        parseError = e.message;
                        parsedData = responseData;
                    }

                    const result = {
                        endpoint,
                        method,
                        statusCode: res.statusCode,
                        success: expectedStatus.includes(res.statusCode),
                        responseTime,
                        headers: res.headers,
                        data: parsedData,
                        rawData: responseData,
                        parseError,
                        timestamp: new Date().toISOString()
                    };

                    this.testResults.push(result);
                    resolve(result);
                });
            });

            req.on('error', (error) => {
                const endTime = performance.now();
                const responseTime = Math.round(endTime - startTime);

                const result = {
                    endpoint,
                    method,
                    success: false,
                    error: error.message,
                    responseTime,
                    timestamp: new Date().toISOString()
                };

                this.testResults.push(result);
                reject(result);
            });

            req.on('timeout', () => {
                req.destroy();
                const result = {
                    endpoint,
                    method,
                    success: false,
                    error: 'Request timeout',
                    responseTime: timeout,
                    timestamp: new Date().toISOString()
                };

                this.testResults.push(result);
                reject(result);
            });

            if (data) {
                req.write(JSON.stringify(data));
            }

            req.end();
        });
    }

    async testEndpoint(name, endpoint, options = {}) {
        this.log(`\n🔍 Testing: ${name}`, 'cyan');
        this.log(`   Endpoint: ${endpoint}`, 'blue');

        try {
            const result = await this.makeRequest(endpoint, options);

            if (result.success) {
                this.log(`   ✅ SUCCESS - ${result.statusCode} (${result.responseTime}ms)`, 'green');

                // Log useful data based on endpoint type
                if (result.data && typeof result.data === 'object') {
                    this.logEndpointSpecificData(endpoint, result.data);
                }
            } else {
                this.log(`   ❌ FAILED - ${result.statusCode} (${result.responseTime}ms)`, 'red');
                if (result.data && result.data.detail) {
                    this.log(`   Error: ${result.data.detail}`, 'red');
                }
            }

            return result;

        } catch (error) {
            this.log(`   💥 ERROR - ${error.error} (${error.responseTime || '?'}ms)`, 'red');
            return error;
        }
    }

    logEndpointSpecificData(endpoint, data) {
        if (endpoint.includes('autonomous/status') && data.data) {
            this.log(`   📊 Trading Active: ${data.data.is_active}`, 'yellow');
            if (data.data.session_stats) {
                this.log(`   📈 Total Trades: ${data.data.session_stats.total_trades || 0}`, 'yellow');
            }
        }

        if (endpoint.includes('positions') && data.positions) {
            this.log(`   📊 Active Positions: ${data.positions.length}`, 'yellow');
        }

        if (endpoint.includes('orders') && data.orders) {
            this.log(`   📋 Orders: ${data.orders.length}`, 'yellow');
        }

        if (endpoint.includes('market/indices') && data.data?.indices) {
            this.log(`   📈 Market Indices: ${data.data.indices.length}`, 'yellow');
        }

        if (endpoint.includes('elite') && data.recommendations) {
            this.log(`   ⭐ Recommendations: ${data.recommendations.length}`, 'yellow');
        }
    }

    // Comprehensive test suite
    async runComprehensiveTests() {
        this.log('🚀 Starting Comprehensive API Test Suite', 'bright');
        this.log(`Target: ${this.baseUrl}`, 'cyan');
        this.log(`Time: ${new Date().toISOString()}`, 'cyan');

        // Core health tests
        await this.testHealthEndpoints();

        // Authentication tests
        await this.testAuthenticationEndpoints();

        // Trading system tests
        await this.testTradingEndpoints();

        // Market data tests
        await this.testMarketDataEndpoints();

        // Dashboard and monitoring tests
        await this.testDashboardEndpoints();

        // Advanced feature tests
        await this.testAdvancedFeatures();

        // Performance tests
        await this.testPerformance();

        // Generate final report
        this.generateReport();
        this.saveResults();
    }

    async testHealthEndpoints() {
        this.log('\n🏥 === HEALTH & INFRASTRUCTURE TESTS ===', 'bright');

        await this.testEndpoint('Health Check', '/health');
        await this.testEndpoint('Readiness Probe', '/ready');
        await this.testEndpoint('API Routes', '/api/routes');
        await this.testEndpoint('Root Endpoint', '/');
        await this.testEndpoint('API Root', '/api');
    }

    async testAuthenticationEndpoints() {
        this.log('\n🔐 === AUTHENTICATION TESTS ===', 'bright');

        await this.testEndpoint('Auth Me (No Token)', '/auth/me', { expectedStatus: [200, 401, 403] });
        await this.testEndpoint('Zerodha Auth Status', '/auth/zerodha/status', { expectedStatus: [200, 404] });
    }

    async testTradingEndpoints() {
        this.log('\n💹 === TRADING SYSTEM TESTS ===', 'bright');

        await this.testEndpoint('Autonomous Trading Status', '/api/v1/autonomous/status');
        await this.testEndpoint('Positions', '/api/v1/positions');
        await this.testEndpoint('Orders', '/api/v1/orders');
        await this.testEndpoint('Elite Recommendations', '/api/v1/elite');
        await this.testEndpoint('Intelligent Symbols', '/api/v1/intelligent-symbols');
    }

    async testMarketDataEndpoints() {
        this.log('\n📊 === MARKET DATA TESTS ===', 'bright');

        await this.testEndpoint('Market Indices', '/api/market/indices');
        await this.testEndpoint('Market Status', '/api/market/market-status');
        await this.testEndpoint('Market Data NIFTY', '/api/v1/market-data/NIFTY', { expectedStatus: [200, 404] });
    }

    async testDashboardEndpoints() {
        this.log('\n📈 === DASHBOARD & MONITORING TESTS ===', 'bright');

        await this.testEndpoint('Dashboard Summary', '/api/v1/dashboard/summary');
        await this.testEndpoint('System Status', '/api/v1/monitoring/system-status');
        await this.testEndpoint('Daily PnL', '/api/v1/monitoring/daily-pnl', { expectedStatus: [200, 404] });
    }

    async testAdvancedFeatures() {
        this.log('\n🔬 === ADVANCED FEATURES TESTS ===', 'bright');

        // Search functionality
        await this.testEndpoint('Search Autocomplete', '/api/v1/search/autocomplete?query=NIFTY&category=symbols&limit=5', { expectedStatus: [200, 404] });
        await this.testEndpoint('Global Search', '/api/v1/search/global?query=NIFTY&limit=10', { expectedStatus: [200, 404] });

        // Database health
        await this.testEndpoint('Database Health', '/api/v1/db-health/status', { expectedStatus: [200, 404] });
    }

    async testPerformance() {
        this.log('\n⚡ === PERFORMANCE TESTS ===', 'bright');

        const performanceTests = [
            { name: 'Health Check (5x)', endpoint: '/health', count: 5 },
            { name: 'Autonomous Status (3x)', endpoint: '/api/v1/autonomous/status', count: 3 },
            { name: 'Market Indices (3x)', endpoint: '/api/market/indices', count: 3 }
        ];

        for (const test of performanceTests) {
            this.log(`\n🔄 Running ${test.name}...`, 'yellow');
            const times = [];

            for (let i = 0; i < test.count; i++) {
                try {
                    const result = await this.makeRequest(test.endpoint);
                    times.push(result.responseTime);
                    await new Promise(resolve => setTimeout(resolve, 100)); // Small delay
                } catch (error) {
                    times.push(error.responseTime || 9999);
                }
            }

            const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
            const minTime = Math.min(...times);
            const maxTime = Math.max(...times);

            this.log(`   📊 Avg: ${Math.round(avgTime)}ms | Min: ${minTime}ms | Max: ${maxTime}ms`, 'cyan');
        }
    }

    generateReport() {
        this.log('\n📋 === FINAL TEST REPORT ===', 'bright');

        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(r => r.success).length;
        const failedTests = totalTests - passedTests;
        const successRate = ((passedTests / totalTests) * 100).toFixed(1);

        this.log(`\n📊 SUMMARY:`, 'bright');
        this.log(`   Total Tests: ${totalTests}`, 'cyan');
        this.log(`   ✅ Passed: ${passedTests}`, 'green');
        this.log(`   ❌ Failed: ${failedTests}`, 'red');
        this.log(`   📈 Success Rate: ${successRate}%`, 'bright');

        // Calculate average response time
        const responseTimes = this.testResults
            .filter(r => r.responseTime)
            .map(r => r.responseTime);

        if (responseTimes.length > 0) {
            const avgResponse = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
            this.log(`   ⚡ Avg Response: ${Math.round(avgResponse)}ms`, 'cyan');
        }

        // Health assessment
        if (successRate >= 90) {
            this.log(`\n🎉 SYSTEM STATUS: EXCELLENT`, 'green');
        } else if (successRate >= 75) {
            this.log(`\n👍 SYSTEM STATUS: GOOD`, 'blue');
        } else if (successRate >= 50) {
            this.log(`\n⚠️  SYSTEM STATUS: NEEDS ATTENTION`, 'yellow');
        } else {
            this.log(`\n🚨 SYSTEM STATUS: CRITICAL`, 'red');
        }

        // Failed endpoints
        const failed = this.testResults.filter(r => !r.success);
        if (failed.length > 0) {
            this.log(`\n❌ FAILED ENDPOINTS:`, 'red');
            failed.forEach(result => {
                this.log(`   • ${result.endpoint}: ${result.error || result.data?.detail || 'Unknown error'}`, 'red');
            });
        }
    }

    saveResults() {
        try {
            // Ensure debug_tools directory exists
            const dir = path.dirname(this.logFile);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }

            const report = {
                timestamp: new Date().toISOString(),
                baseUrl: this.baseUrl,
                totalTests: this.testResults.length,
                passed: this.testResults.filter(r => r.success).length,
                failed: this.testResults.filter(r => !r.success).length,
                results: this.testResults
            };

            fs.writeFileSync(this.logFile, JSON.stringify(report, null, 2));
            this.log(`\n💾 Results saved to: ${this.logFile}`, 'cyan');

        } catch (error) {
            this.log(`\n❌ Failed to save results: ${error.message}`, 'red');
        }
    }

    // Quick test for specific endpoint
    async quickTest(endpoint, options = {}) {
        this.log(`🔍 Quick Test: ${endpoint}`, 'cyan');
        return await this.testEndpoint(`Quick Test`, endpoint, options);
    }

    // Test with authentication
    setAuthToken(token) {
        this.authToken = token;
        this.log(`🔐 Auth token set`, 'green');
    }

    clearAuthToken() {
        this.authToken = null;
        this.log(`🔓 Auth token cleared`, 'yellow');
    }
}

// CLI interface
if (require.main === module) {
    const args = process.argv.slice(2);
    const tester = new ApiTester();

    if (args.length === 0) {
        // Run full test suite
        tester.runComprehensiveTests().catch(console.error);
    } else if (args[0] === 'quick' && args[1]) {
        // Quick test specific endpoint
        tester.quickTest(args[1]).catch(console.error);
    } else {
        console.log('Usage:');
        console.log('  node api_tester.js                    # Run full test suite');
        console.log('  node api_tester.js quick /health      # Quick test specific endpoint');
    }
}

module.exports = ApiTester; 