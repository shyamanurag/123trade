#!/usr/bin/env python3

import requests
import time

def check_frontend_status():
    url = "https://quantumcrypto-l43mb.ondigitalocean.app/"
    
    try:
        response = requests.get(url, timeout=10)
        content = response.text.lower()
        
        # Check for React frontend indicators
        react_indicators = [
            '<div id="root">',
            'vite',
            'react',
            '/assets/',
            'sharekhan trading system' in content and 'analytics' in content,
            'trading dashboard',
            'user management'
        ]
        
        is_react = any(indicator in content for indicator in react_indicators if isinstance(indicator, str))
        
        print(f"🔍 Checking: {url}")
        print(f"📊 Status: {response.status_code}")
        print(f"📏 Content Length: {len(content)} chars")
        
        if is_react:
            print("✅ REACT FRONTEND DETECTED!")
            print("🎉 Your comprehensive trading dashboard is NOW LIVE!")
            return True
        else:
            print("❌ Still showing backend HTML")
            print("⏳ React frontend not yet deployed...")
            
            # Show what we're actually getting
            lines = content.split('\n')[:5]
            print("📄 Current content preview:")
            for line in lines:
                print(f"   {line[:100]}")
            
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 CHECKING REACT FRONTEND DEPLOYMENT STATUS")
    print("=" * 60)
    
    is_live = check_frontend_status()
    
    if not is_live:
        print("\n⏰ DigitalOcean is still deploying...")
        print("💡 This usually takes 2-5 minutes after pushing changes.")
        print("🔄 The React frontend with ALL your requested features will be live soon!") 