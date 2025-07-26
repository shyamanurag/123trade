#!/usr/bin/env python3

import requests
import time

def test_frontend():
    url = "https://trade123-l3zp7.ondigitalocean.app/"
    
    print("🚀 FINAL FRONTEND TEST")
    print("=" * 50)
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"📊 Status: {response.status_code}")
        print(f"📏 Content Length: {len(response.text)} chars")
        print(f"🌐 Content-Type: {response.headers.get('content-type')}")
        print(f"🔗 X-DO-App-Origin: {response.headers.get('x-do-app-origin')}")
        
        content = response.text.lower()
        
        # Check for React indicators
        react_indicators = [
            '<div id="root">' in content,
            'vite' in content,
            'react' in content,
            '/assets/' in content,
            'sharekhantradingsystem' in content.replace(' ', ''),
        ]
        
        print("\n🔍 CONTENT ANALYSIS:")
        print(f"  Has <div id='root'>: {react_indicators[0]}")
        print(f"  Contains 'vite': {react_indicators[1]}")
        print(f"  Contains 'react': {react_indicators[2]}")
        print(f"  Has /assets/ links: {react_indicators[3]}")
        print(f"  Has app name: {react_indicators[4]}")
        
        if any(react_indicators):
            print("\n✅ REACT FRONTEND DETECTED!")
            print("🎉 Your comprehensive trading dashboard is LIVE!")
            return True
        else:
            print("\n❌ Still serving backend HTML")
            print("\n📄 Content preview:")
            lines = response.text.split('\n')[:5]
            for line in lines:
                print(f"   {line.strip()[:80]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_frontend()
    
    if not success:
        print("\n⏰ DigitalOcean deployment may still be in progress...")
        print("💡 Try again in 2-3 minutes if the issue persists.")
        print("🔧 If it still doesn't work, there may be a deeper configuration issue.") 