"""
Complete deployment fix script for Digital Ocean
This script contains all the fixes needed for the production deployment
"""

import os
import subprocess
import sys

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}")
    print(f"   Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ Success")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
        else:
            print("   ❌ Failed")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        return False

def main():
    """Main deployment process"""
    print_header("COMPLETE DEPLOYMENT FIX FOR DIGITAL OCEAN")
    
    # Step 1: Commit all changes
    print_header("Step 1: Committing All Changes")
    
    commands = [
        ("git add -A", "Adding all files"),
        ('git commit -m "Complete fix for Digital Ocean deployment: routing, monitoring, and WebSocket"', "Committing changes"),
        ("git push origin main", "Pushing to GitHub")
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            print("\n⚠️  Git operation failed. You may need to:")
            print("   1. Check if you have uncommitted changes")
            print("   2. Pull latest changes: git pull origin main")
            print("   3. Resolve any conflicts")
            break
    
    # Step 2: Deploy configuration
    print_header("Step 2: Digital Ocean Configuration")
    
    print("\n📋 Configuration Summary:")
    print("   1. Backend fixes:")
    print("      - Added middleware to handle path stripping")
    print("      - Fixed monitoring endpoints (metrics, components)")
    print("      - Fixed auth endpoint status codes")
    print("   2. Frontend fixes:")
    print("      - WebSocket connection to /ws")
    print("      - Token validation on startup")
    print("      - API endpoint configurations")
    print("   3. Ingress rules:")
    print("      - Using preserve_path_prefix for all API routes")
    
    # Step 3: Show deployment options
    print_header("Step 3: Deployment Options")
    
    print("\n🚀 Option 1: Using doctl CLI")
    print("   doctl apps update <app-id> --spec digital-ocean-app-ultimate-fix.yaml")
    
    print("\n🚀 Option 2: Manual deployment in Digital Ocean dashboard")
    print("   1. Go to your app in Digital Ocean")
    print("   2. Click on 'Settings' tab")
    print("   3. Click 'Edit' on App Spec")
    print("   4. Replace with content from digital-ocean-app-ultimate-fix.yaml")
    print("   5. Click 'Save'")
    
    print("\n🚀 Option 3: Wait for automatic deployment")
    print("   Since we pushed to main branch, Digital Ocean will auto-deploy")
    print("   This usually takes 5-10 minutes")
    
    # Step 4: Post-deployment verification
    print_header("Step 4: Post-Deployment Verification")
    
    print("\n📝 After deployment completes, run these tests:")
    print("   1. python scripts/test_production_api.py")
    print("   2. Check the web UI at https://algoauto-9gx56.ondigitalocean.app")
    print("   3. Login with admin/admin123")
    print("   4. Verify WebSocket connection in browser console")
    
    # Step 5: Known issues
    print_header("Step 5: Remaining Known Issues")
    
    print("\n⚠️  These issues may still need attention:")
    print("   1. WebSocket 403 error - may need auth token in connection")
    print("   2. Daily P&L timeout - database query optimization needed")
    print("   3. Some routes returning 404 - Digital Ocean path stripping")
    
    print("\n✅ Deployment preparation complete!")
    print("   Monitor the deployment at: https://cloud.digitalocean.com/apps")

if __name__ == "__main__":
    main() 