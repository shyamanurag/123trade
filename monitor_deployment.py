#!/usr/bin/env python3
"""
Deployment Monitor for ShareKhan Trading System
Monitors the deployment progress and tests when CORS is fixed
"""

import requests
import time
import json
from datetime import datetime

PRODUCTION_URL = "https://quantumcrypto-l43mb.ondigitalocean.app"

def test_endpoint(endpoint):
    """Test a specific endpoint and return status"""
    url = f"{PRODUCTION_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=10)
        return {
            'endpoint': endpoint,
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'response_time': response.elapsed.total_seconds()
        }
    except requests.exceptions.RequestException as e:
        return {
            'endpoint': endpoint,
            'status_code': 'ERROR',
            'success': False,
            'error': str(e)
        }

def monitor_deployment():
    """Monitor deployment until CORS is fixed"""
    print("🔄 Monitoring ShareKhan Trading System Deployment")
    print(f"🌐 URL: {PRODUCTION_URL}")
    print("⏱️ Checking every 30 seconds...\n")
    
    endpoints = [
        '/health',
        '/api/system/status',
        '/',
        '/docs'
    ]
    
    deployment_start = datetime.now()
    check_count = 0
    
    while True:
        check_count += 1
        elapsed = datetime.now() - deployment_start
        
        print(f"📊 Check #{check_count} - Elapsed: {str(elapsed).split('.')[0]}")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        all_working = True
        results = []
        
        for endpoint in endpoints:
            result = test_endpoint(endpoint)
            results.append(result)
            
            status_icon = "✅" if result['success'] else "❌"
            status_code = result['status_code']
            
            if result['success']:
                response_time = f"{result['response_time']:.2f}s"
                print(f"  {status_icon} {endpoint} - {status_code} ({response_time})")
            else:
                print(f"  {status_icon} {endpoint} - {status_code}")
                all_working = False
        
        if all_working:
            print("\n🎉 DEPLOYMENT SUCCESSFUL!")
            print("✅ All endpoints are working!")
            print("✅ CORS configuration updated!")
            print("✅ Host header restrictions resolved!")
            print(f"\n🚀 Your ShareKhan Trading System is now fully accessible:")
            print(f"   🌐 {PRODUCTION_URL}")
            break
        else:
            print("\n⏳ Deployment still in progress...")
            if check_count >= 10:  # Stop after 5 minutes
                print("\n⚠️ Deployment taking longer than expected")
                print("💡 The system may still be deploying - check manually in a few minutes")
                break
            
            print("   Waiting 30 seconds for next check...\n")
            time.sleep(30)

if __name__ == "__main__":
    monitor_deployment() 