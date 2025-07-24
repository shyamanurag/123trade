"""
Script to fix Digital Ocean routing issues comprehensively
This updates the app configuration to handle path stripping correctly
"""

import yaml
import os

def fix_app_yaml():
    """Fix the Digital Ocean app configuration"""
    
    # Read the current configuration
    with open('digital-ocean-app-fixed.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Update ingress rules to NOT use rewrite but use preserve_path_prefix
    # This is the correct approach based on the API structure
    new_ingress_rules = [
        {
            'component': {
                'name': 'api',
                'preserve_path_prefix': True
            },
            'match': {
                'path': {
                    'prefix': '/api'
                }
            }
        },
        {
            'component': {
                'name': 'api',
                'preserve_path_prefix': True
            },
            'match': {
                'path': {
                    'prefix': '/health'
                }
            }
        },
        {
            'component': {
                'name': 'api',
                'preserve_path_prefix': True
            },
            'match': {
                'path': {
                    'prefix': '/ready'
                }
            }
        },
        {
            'component': {
                'name': 'api',
                'preserve_path_prefix': True
            },
            'match': {
                'path': {
                    'prefix': '/docs'
                }
            }
        },
        {
            'component': {
                'name': 'api',
                'preserve_path_prefix': True
            },
            'match': {
                'path': {
                    'prefix': '/auth'
                }
            }
        },
        {
            'component': {
                'name': 'api',
                'preserve_path_prefix': True
            },
            'match': {
                'path': {
                    'prefix': '/ws'
                }
            }
        },
        {
            'component': {
                'name': 'api',
                'preserve_path_prefix': True
            },
            'match': {
                'path': {
                    'prefix': '/zerodha'
                }
            }
        },
        {
            'component': {
                'name': 'frontend'
            },
            'match': {
                'path': {
                    'prefix': '/'
                }
            }
        }
    ]
    
    # Update the configuration
    config['ingress']['rules'] = new_ingress_rules
    
    # Add ROOT_PATH environment variable to handle path stripping
    # This tells FastAPI to expect paths without leading slash
    for env in config['envs']:
        if env['key'] == 'ROOT_PATH':
            env['value'] = ''  # Empty ROOT_PATH
            break
    
    # Write the updated configuration
    with open('digital-ocean-app-ultimate-fix.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("✅ Created digital-ocean-app-ultimate-fix.yaml with comprehensive routing fixes")
    print("\n📋 Key changes made:")
    print("   1. Using preserve_path_prefix instead of rewrite for all API routes")
    print("   2. Added /zerodha route to ingress")
    print("   3. Set ROOT_PATH to empty string")
    print("\n🚀 Next steps:")
    print("   1. Review the digital-ocean-app-ultimate-fix.yaml file")
    print("   2. Deploy using: doctl apps update <app-id> --spec digital-ocean-app-ultimate-fix.yaml")
    print("   3. Or update manually in Digital Ocean dashboard")

def create_frontend_fixes():
    """Create fixes for frontend issues"""
    
    fixes = """
# Frontend Fixes Required

## 1. API Configuration (src/frontend/api/config.js)
- ✅ Already fixed: Added trailing slashes where needed
- ✅ Already fixed: Added broker users endpoint
- ✅ Already fixed: Added trading control endpoints

## 2. WebSocket Hook (src/frontend/hooks/useWebSocket.js)
- ✅ Already fixed: Changed from /ws/{userId} to /ws
- ✅ Already fixed: Send auth message after connection

## 3. Components to Update:
- ✅ UserManagementDashboard: Updated to use API_ENDPOINTS
- ✅ SystemHealthMonitor: Updated to use API_ENDPOINTS
- ✅ App.jsx: Added token validation on startup

## 4. Remaining Issues:
- WebSocket library compatibility issue (needs update)
- Some endpoints returning 404 due to routing
"""
    
    with open('frontend-fixes-summary.md', 'w', encoding='utf-8') as f:
        f.write(fixes)
    
    print("\n📝 Created frontend-fixes-summary.md")

def create_backend_fixes():
    """Create a script to fix backend routing issues"""
    
    backend_fix = '''"""
Backend routing fix for Digital Ocean deployment
Run this to update the API to handle path stripping correctly
"""

import os

# Update main.py to handle paths without leading slashes
def fix_main_py():
    """Add middleware to handle Digital Ocean path stripping"""
    
    middleware_code = """
# Middleware to fix Digital Ocean path stripping
@app.middleware("http")
async def fix_path_stripping(request: Request, call_next):
    # Log the original path
    original_path = request.url.path
    
    # If path doesn't start with /, add it
    if original_path and not original_path.startswith('/'):
        # Create a new URL with the leading slash
        from starlette.datastructures import URL
        new_url = URL(str(request.url).replace(original_path, f'/{original_path}', 1))
        request._url = new_url
        logger.info(f"Fixed path: {original_path} -> {new_url.path}")
    
    response = await call_next(request)
    return response
"""
    
    print("Add this middleware to main.py after the other middleware")
    print(middleware_code)

if __name__ == "__main__":
    fix_main_py()
'''
    
    with open('fix_backend_routing.py', 'w', encoding='utf-8') as f:
        f.write(backend_fix)
    
    print("📝 Created fix_backend_routing.py")

if __name__ == "__main__":
    print("🔧 Digital Ocean Routing Fix Script")
    print("=" * 50)
    
    # Create the fixed YAML
    fix_app_yaml()
    
    # Create frontend fixes summary
    create_frontend_fixes()
    
    # Create backend fixes
    create_backend_fixes()
    
    print("\n✅ All fix files created successfully!")
    print("\n⚠️  IMPORTANT: The main issue is that Digital Ocean is stripping")
    print("   the leading slash from paths even with preserve_path_prefix.")
    print("   The ultimate fix is to update the backend to handle both cases.") 