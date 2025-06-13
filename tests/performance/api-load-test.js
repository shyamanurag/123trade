import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('error_rate');
const responseTimeTrend = new Trend('response_time_trend');

// Test configuration
export let options = {
  stages: [
    { duration: '2m', target: 10 }, // Ramp up to 10 users over 2 minutes
    { duration: '5m', target: 10 }, // Hold at 10 users for 5 minutes
    { duration: '2m', target: 20 }, // Ramp up to 20 users over 2 minutes
    { duration: '5m', target: 20 }, // Hold at 20 users for 5 minutes
    { duration: '2m', target: 0 },  // Ramp down to 0 users over 2 minutes
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should be below 2s
    http_req_failed: ['rate<0.05'],    // Error rate should be below 5%
    error_rate: ['rate<0.05'],         // Custom error rate should be below 5%
  },
};

// Environment variables
const BASE_URL = __ENV.K6_STAGING_URL || 'http://localhost:8000';
const API_TOKEN = __ENV.K6_API_TOKEN || '';

// Test data
const testSymbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'];

export default function () {
  // Test health endpoint
  testHealthEndpoint();
  
  // Test authentication
  const authToken = testAuthentication();
  
  if (authToken) {
    // Test trading endpoints
    testTradingEndpoints(authToken);
    
    // Test market data endpoints
    testMarketDataEndpoints(authToken);
    
    // Test recommendations endpoint
    testRecommendationsEndpoint(authToken);
  }
  
  sleep(1);
}

function testHealthEndpoint() {
  const response = http.get(`${BASE_URL}/health`);
  
  const success = check(response, {
    'health endpoint status is 200': (r) => r.status === 200,
    'health endpoint response time < 500ms': (r) => r.timings.duration < 500,
    'health endpoint returns valid JSON': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch (e) {
        return false;
      }
    },
  });
  
  errorRate.add(!success);
  responseTimeTrend.add(response.timings.duration);
}

function testAuthentication() {
  if (!API_TOKEN) {
    // Test login endpoint if no token provided
    const loginData = {
      username: 'test_user',
      password: 'test_password123',
    };
    
    const response = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify(loginData), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    const success = check(response, {
      'login status is 200 or 401': (r) => r.status === 200 || r.status === 401,
      'login response time < 1000ms': (r) => r.timings.duration < 1000,
    });
    
    errorRate.add(!success);
    responseTimeTrend.add(response.timings.duration);
    
    if (response.status === 200) {
      const body = JSON.parse(response.body);
      return body.access_token;
    }
  }
  
  return API_TOKEN;
}

function testTradingEndpoints(token) {
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Test positions endpoint
  const positionsResponse = http.get(`${BASE_URL}/api/v1/positions`, { headers });
  
  check(positionsResponse, {
    'positions endpoint status is 200': (r) => r.status === 200,
    'positions response time < 1000ms': (r) => r.timings.duration < 1000,
  });
  
  errorRate.add(positionsResponse.status !== 200);
  responseTimeTrend.add(positionsResponse.timings.duration);
  
  // Test orders endpoint
  const ordersResponse = http.get(`${BASE_URL}/api/v1/orders`, { headers });
  
  check(ordersResponse, {
    'orders endpoint status is 200': (r) => r.status === 200,
    'orders response time < 1000ms': (r) => r.timings.duration < 1000,
  });
  
  errorRate.add(ordersResponse.status !== 200);
  responseTimeTrend.add(ordersResponse.timings.duration);
  
  // Test portfolio endpoint
  const portfolioResponse = http.get(`${BASE_URL}/api/v1/portfolio`, { headers });
  
  check(portfolioResponse, {
    'portfolio endpoint status is 200': (r) => r.status === 200,
    'portfolio response time < 1500ms': (r) => r.timings.duration < 1500,
  });
  
  errorRate.add(portfolioResponse.status !== 200);
  responseTimeTrend.add(portfolioResponse.timings.duration);
}

function testMarketDataEndpoints(token) {
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Test market data for random symbol
  const symbol = testSymbols[Math.floor(Math.random() * testSymbols.length)];
  const marketDataResponse = http.get(`${BASE_URL}/api/v1/market-data/${symbol}`, { headers });
  
  check(marketDataResponse, {
    'market data endpoint status is 200': (r) => r.status === 200,
    'market data response time < 1000ms': (r) => r.timings.duration < 1000,
    'market data returns valid structure': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.symbol && data.price !== undefined;
      } catch (e) {
        return false;
      }
    },
  });
  
  errorRate.add(marketDataResponse.status !== 200);
  responseTimeTrend.add(marketDataResponse.timings.duration);
  
  // Test historical data endpoint
  const historicalResponse = http.get(
    `${BASE_URL}/api/v1/market-data/${symbol}/historical?period=1d`,
    { headers }
  );
  
  check(historicalResponse, {
    'historical data endpoint status is 200': (r) => r.status === 200,
    'historical data response time < 2000ms': (r) => r.timings.duration < 2000,
  });
  
  errorRate.add(historicalResponse.status !== 200);
  responseTimeTrend.add(historicalResponse.timings.duration);
}

function testRecommendationsEndpoint(token) {
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  // Test recommendations endpoint
  const recommendationsResponse = http.get(`${BASE_URL}/api/v1/recommendations`, { headers });
  
  check(recommendationsResponse, {
    'recommendations endpoint status is 200': (r) => r.status === 200,
    'recommendations response time < 2000ms': (r) => r.timings.duration < 2000,
    'recommendations returns array': (r) => {
      try {
        const data = JSON.parse(r.body);
        return Array.isArray(data);
      } catch (e) {
        return false;
      }
    },
  });
  
  errorRate.add(recommendationsResponse.status !== 200);
  responseTimeTrend.add(recommendationsResponse.timings.duration);
  
  // Test AI model status endpoint
  const modelStatusResponse = http.get(`${BASE_URL}/api/v1/models/status`, { headers });
  
  check(modelStatusResponse, {
    'model status endpoint status is 200': (r) => r.status === 200,
    'model status response time < 1000ms': (r) => r.timings.duration < 1000,
  });
  
  errorRate.add(modelStatusResponse.status !== 200);
  responseTimeTrend.add(modelStatusResponse.timings.duration);
}

export function handleSummary(data) {
  // Generate performance report
  const report = {
    timestamp: new Date().toISOString(),
    test_duration: data.metrics.iteration_duration.avg,
    total_requests: data.metrics.http_reqs.count,
    failed_requests: data.metrics.http_req_failed.rate,
    avg_response_time: data.metrics.http_req_duration.avg,
    p95_response_time: data.metrics['http_req_duration']['p(95)'],
    error_rate: data.metrics.error_rate ? data.metrics.error_rate.rate : 0,
    thresholds_passed: data.thresholds,
  };
  
  return {
    'performance-report.json': JSON.stringify(report, null, 2),
    'stdout': `
=== Performance Test Summary ===
Duration: ${data.metrics.iteration_duration.avg}ms
Total Requests: ${data.metrics.http_reqs.count}
Failed Requests: ${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%
Average Response Time: ${data.metrics.http_req_duration.avg}ms
95th Percentile: ${data.metrics['http_req_duration']['p(95)']}ms
Error Rate: ${data.metrics.error_rate ? (data.metrics.error_rate.rate * 100).toFixed(2) : 0}%

Thresholds: ${Object.entries(data.thresholds).map(([key, value]) => 
  `${key}: ${value.ok ? 'PASS' : 'FAIL'}`
).join(', ')}
`,
  };
} 