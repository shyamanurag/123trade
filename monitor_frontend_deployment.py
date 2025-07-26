#!/usr/bin/env python3
"""
Frontend Deployment Monitor
Monitors when the React frontend becomes available instead of backend HTML
"""

import requests
import time
from datetime import datetime
import re

URL = "https://quantumcrypto-l43mb.ondigitalocean.app/"

def check_frontend_status():
    """Check if we're getting React frontend or backend HTML"""
    try:
        response = requests.get(URL, timeout=10)
        content = response.text
        
        # Check if it's the React frontend (should have script tags, React-specific content)
        is_react = any([
            'React' in content,
            'main.jsx' in content,
            'ShareKhan Trading Platform' in content and '<script' in content,
            'root' in content and 'script type="module"' in content
        ])
        
        # Check if it's the backend HTML (our previous status page)
        is_backend = any([
            'ShareKhan Trading System started successfully' in content,
            'System Status:' in content and 'Backend' in content,
            'Orchestrator: Initialized' in content
        ])
        
        return {
            'status_code': response.status_code,
            'is_react': is_react,
            'is_backend': is_backend,
            'content_type': response.headers.get('content-type', ''),
            'content_length': len(content),
            'has_javascript': '<script' in content,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def monitor_deployment():
    """Monitor the deployment progress"""
    print("🔍 MONITORING FRONTEND DEPLOYMENT")
    print(f"🌐 URL: {URL}")
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    consecutive_react = 0
    
    for i in range(60):  # Monitor for 30 minutes (30 checks every 30 seconds)
        result = check_frontend_status()
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            status = result['status_code']
            
            if result.get('is_react'):
                consecutive_react += 1
                print(f"✅ REACT FRONTEND DETECTED! (#{consecutive_react})")
                print(f"   Status: {status}")
                print(f"   Content-Type: {result.get('content_type', '')}")
                print(f"   Has JavaScript: {result.get('has_javascript', False)}")
                print(f"   Content Length: {result.get('content_length', 0)} chars")
                
                if consecutive_react >= 2:
                    print("\n🎉 FRONTEND DEPLOYMENT SUCCESSFUL!")
                    print("✅ React trading platform is now live!")
                    print("🚀 Your comprehensive trading frontend is ready!")
                    return True
                    
            elif result.get('is_backend'):
                consecutive_react = 0
                print(f"⏳ Still backend HTML (Status: {status})")
                print(f"   Content Length: {result.get('content_length', 0)} chars")
                
            else:
                consecutive_react = 0
                print(f"❓ Unknown content (Status: {status})")
                print(f"   Content Length: {result.get('content_length', 0)} chars")
        
        if i < 59:  # Don't wait after the last check
            print(f"   ⏱️ Waiting 30s... (Check {i+1}/60)")
            time.sleep(30)
        
        print("-" * 60)
    
    print("⏰ Monitoring timeout reached")
    print("💡 Deployment may still be in progress - check manually")
    return False

if __name__ == "__main__":
    try:
        success = monitor_deployment()
        if success:
            print("\n🎯 NEXT STEPS:")
            print("1. Visit: https://quantumcrypto-l43mb.ondigitalocean.app/")
            print("2. You should see the React trading platform")
            print("3. Login and access all trading features")
            print("4. Real-time data, analytics, user management available")
        else:
            print("\n🔧 If still seeing backend HTML:")
            print("1. Deployment may need more time")
            print("2. Check DigitalOcean build logs")
            print("3. Frontend build might need additional fixes")
    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user") 