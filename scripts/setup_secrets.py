#!/usr/bin/env python3
"""
Secure Secret Configuration Script
Helps configure API secrets without exposing them in version control
"""

import os
import sys
from pathlib import Path
import getpass

def setup_production_secrets():
    """Interactive script to securely configure production secrets"""
    
    print("🔐 SECURE SECRET CONFIGURATION")
    print("=" * 50)
    print("This script will help you configure API secrets securely.")
    print("Secrets will be saved to config/production.env (which is in .gitignore)")
    print()
    
    # Read current production.env
    env_file = Path("config/production.env")
    if not env_file.exists():
        print("❌ Error: config/production.env not found!")
        return False
        
    # Read current content
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Define secrets to configure
    secrets = {
        'ZERODHA_API_SECRET': {
            'description': 'Zerodha API Secret (from Kite Connect Dashboard)',
            'current': 'your_real_zerodha_api_secret_here',
            'required': True
        },
        'TELEGRAM_BOT_TOKEN': {
            'description': 'Telegram Bot Token (optional)',
            'current': 'your_telegram_bot_token_here',
            'required': False
        },
        'EMAIL_PASSWORD': {
            'description': 'Email App Password (optional)',
            'current': 'your_email_app_password_here',
            'required': False
        },
        'N8N_API_KEY': {
            'description': 'N8N API Key (optional)',
            'current': 'n8n_api_key_production_secure_token_here',
            'required': False
        }
    }
    
    # Configure each secret
    updated_lines = lines.copy()
    
    for secret_name, config in secrets.items():
        print(f"\n🔑 Configuring {secret_name}")
        print(f"   Description: {config['description']}")
        
        if config['required']:
            print("   ⚠️  REQUIRED for trading functionality")
        else:
            print("   ℹ️  Optional (can skip)")
            
        # Ask user if they want to configure this secret
        if config['required']:
            configure = True
        else:
            response = input(f"   Configure {secret_name}? (y/n): ").lower()
            configure = response in ['y', 'yes']
            
        if configure:
            # Get secret value securely
            secret_value = getpass.getpass(f"   Enter {secret_name}: ")
            
            if secret_value.strip():
                # Update the line in the file
                for i, line in enumerate(updated_lines):
                    if line.strip().startswith(f"{secret_name}="):
                        updated_lines[i] = f"{secret_name}={secret_value.strip()}\n"
                        print(f"   ✅ {secret_name} configured")
                        break
            else:
                print(f"   ⏭️  Skipped {secret_name}")
        else:
            print(f"   ⏭️  Skipped {secret_name}")
    
    # Write updated content back to file
    try:
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)
        
        print("\n" + "=" * 50)
        print("✅ SECRETS CONFIGURED SUCCESSFULLY!")
        print()
        print("📋 Next Steps:")
        print("1. Run validation: python validate_production_readiness.py")
        print("2. Test locally: python start_production_optimized.py")
        print("3. Deploy to DigitalOcean")
        print()
        print("🔒 Security Notes:")
        print("• Secrets are stored in config/production.env (not in Git)")
        print("• For production, use DigitalOcean environment variables")
        print("• Never commit secrets to version control")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving secrets: {str(e)}")
        return False

def create_digitalocean_env_vars():
    """Display instructions for DigitalOcean environment variables"""
    
    print("\n🌊 DIGITALOCEAN ENVIRONMENT VARIABLES SETUP")
    print("=" * 60)
    print()
    print("For production deployment, configure these in DigitalOcean:")
    print()
    print("1. Go to: https://cloud.digitalocean.com/apps")
    print("2. Select your app → Settings → Environment Variables")
    print("3. Click 'Add Variable' and add these (set as 'Encrypted'):")
    print()
    
    env_vars = [
        "ZERODHA_API_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "EMAIL_PASSWORD", 
        "N8N_API_KEY",
        "DATA_PROVIDER_AUTH_TOKEN"
    ]
    
    for var in env_vars:
        print(f"   • {var}")
    
    print()
    print("4. Click 'Save' and redeploy your app")
    print()
    print("🔗 Direct link to your app settings:")
    print("   https://cloud.digitalocean.com/apps/clownfish-app-7rqhp/settings")
    print()

def main():
    """Main function"""
    print("🔐 TRADING SYSTEM SECRET CONFIGURATION")
    print()
    print("Choose configuration method:")
    print("1. Configure secrets for local development")
    print("2. Show DigitalOcean environment variables setup")
    print("3. Both")
    print()
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        success = setup_production_secrets()
        if not success:
            return 1
    
    if choice in ['2', '3']:
        create_digitalocean_env_vars()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Configuration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Configuration failed: {str(e)}")
        sys.exit(1) 