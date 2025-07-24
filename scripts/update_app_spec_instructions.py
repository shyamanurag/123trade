"""
Instructions for updating Digital Ocean App Spec
"""

def print_required_changes():
    """Print the required changes for the app spec"""
    
    print("📋 REQUIRED CHANGES TO DIGITAL OCEAN APP SPEC")
    print("=" * 60)
    
    print("\n1. ADD MISSING INGRESS RULES:")
    print("   Add these two rules to the ingress section:")
    print("""
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /ready
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /zerodha
""")
    
    print("\n2. UPDATE ROOT_PATH:")
    print("   Change:")
    print("   - key: ROOT_PATH")
    print("     scope: RUN_AND_BUILD_TIME")
    print("   To:")
    print("   - key: ROOT_PATH")
    print("     scope: RUN_AND_BUILD_TIME")
    print("     value: ''")
    
    print("\n3. TRUEDATA SANDBOX MODE (Optional):")
    print("   If you're testing and not using real money:")
    print("   Change:")
    print("   - key: TRUEDATA_IS_SANDBOX")
    print("     scope: RUN_AND_BUILD_TIME")
    print("     value: \"false\"")
    print("   To:")
    print("   - key: TRUEDATA_IS_SANDBOX")
    print("     scope: RUN_AND_BUILD_TIME")
    print("     value: \"true\"")
    
    print("\n4. VERIFY WEBSOCKET RULE EXISTS:")
    print("   Ensure this rule is present (it appears to be):")
    print("""
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /ws
""")
    
    print("\n" + "=" * 60)
    print("💡 HOW TO APPLY THESE CHANGES:")
    print("=" * 60)
    
    print("\n1. Go to https://cloud.digitalocean.com/apps")
    print("2. Click on 'algoauto'")
    print("3. Go to 'Settings' tab")
    print("4. Under 'App Spec', click 'Edit'")
    print("5. Make the changes listed above")
    print("6. Click 'Save' to trigger redeployment")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("- The WebSocket rule IS present but might not be working due to order")
    print("- Make sure the /ws rule comes BEFORE the / (frontend) rule")
    print("- The ingress rules are processed in order")
    print("- TRUEDATA_IS_SANDBOX should be 'true' for testing without real trading")

def generate_corrected_spec():
    """Generate the corrected ingress section"""
    
    print("\n" + "=" * 60)
    print("📄 CORRECTED INGRESS SECTION:")
    print("=" * 60)
    
    corrected_ingress = """ingress:
  rules:
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /api
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /health
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /ready
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /docs
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /auth
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /ws
  - component:
      name: api
      preserve_path_prefix: true
    match:
      path:
        prefix: /zerodha
  - component:
      name: frontend
    match:
      path:
        prefix: /"""
    
    print(corrected_ingress)
    
    print("\n✅ This ensures all API routes are handled before the catch-all frontend route")

if __name__ == "__main__":
    print_required_changes()
    generate_corrected_spec()
    
    print("\n" + "=" * 60)
    print("🚀 After making these changes:")
    print("=" * 60)
    print("1. Save the app spec in Digital Ocean")
    print("2. Wait for redeployment (5-10 minutes)")
    print("3. Run: python scripts/test_production_api.py")
    print("4. Check if WebSocket connects successfully")
    print("\n✅ Script complete!") 