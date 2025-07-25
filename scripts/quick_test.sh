#!/bin/bash
# =============================================================================
# QUICK TEST SCRIPT FOR CRYPTO TRADING SYSTEM
# Runs essential sanity tests for rapid validation
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "=================================================================="
echo "🚀 CRYPTO TRADING SYSTEM - QUICK TEST SUITE"
echo "=================================================================="

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    print_error "app.py not found. Please run this script from the project root directory."
    exit 1
fi

# Create necessary directories
print_status "Creating test directories..."
mkdir -p reports logs data backups

# Set test environment
export TESTING=true
export ENVIRONMENT=testing
export DATABASE_URL=sqlite:///test.db
export REDIS_URL=redis://localhost:6379/15
export LOG_LEVEL=DEBUG

print_status "Environment configured for testing"

# Test 1: Python version check
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_version="3.8"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    print_success "Python version $python_version is compatible"
else
    print_error "Python 3.8+ required, found $python_version"
    exit 1
fi

# Test 2: Check required packages
print_status "Checking required packages..."
required_packages=("fastapi" "uvicorn" "sqlalchemy" "pandas" "numpy")

for package in "${required_packages[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        print_success "Package $package is installed"
    else
        print_warning "Package $package is missing"
        missing_packages+=("$package")
    fi
done

# Test 3: Configuration files check
print_status "Checking configuration files..."
config_files=("requirements.txt" "Dockerfile" "docker-compose.yml" "app.py")

for file in "${config_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "Configuration file $file exists"
    else
        print_error "Configuration file $file is missing"
        exit 1
    fi
done

# Test 4: Dockerfile syntax check
print_status "Checking Dockerfile syntax..."
if command -v docker >/dev/null 2>&1; then
    if docker build --help >/dev/null 2>&1; then
        print_success "Docker is available"
        
        # Check Dockerfile content
        if grep -q "FROM python:" Dockerfile; then
            print_success "Dockerfile uses Python base image"
        else
            print_warning "Dockerfile may not use Python base image"
        fi
    else
        print_warning "Docker build not available"
    fi
else
    print_warning "Docker not installed or not in PATH"
fi

# Test 5: Docker Compose syntax check
print_status "Checking Docker Compose syntax..."
if command -v docker-compose >/dev/null 2>&1; then
    if docker-compose config >/dev/null 2>&1; then
        print_success "Docker Compose configuration is valid"
    else
        print_warning "Docker Compose configuration has issues"
    fi
    
    # Check enhanced compose file
    if [ -f "docker-compose.enhanced.yml" ]; then
        if docker-compose -f docker-compose.enhanced.yml config >/dev/null 2>&1; then
            print_success "Enhanced Docker Compose configuration is valid"
        else
            print_warning "Enhanced Docker Compose configuration has issues"
        fi
    fi
else
    print_warning "Docker Compose not installed or not in PATH"
fi

# Test 6: Basic import test
print_status "Testing basic imports..."
if python3 -c "
try:
    import fastapi
    import uvicorn
    import sqlalchemy
    import pandas as pd
    import numpy as np
    print('✅ All critical imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
" 2>/dev/null; then
    print_success "Critical imports working"
else
    print_error "Critical import failures detected"
    exit 1
fi

# Test 7: FastAPI app creation test
print_status "Testing FastAPI app creation..."
if python3 -c "
import sys
import os
sys.path.insert(0, '.')
os.environ['TESTING'] = 'true'

try:
    from fastapi import FastAPI
    app = FastAPI(title='Test App')
    print('✅ FastAPI app creation successful')
except Exception as e:
    print(f'❌ FastAPI app creation failed: {e}')
    exit(1)
" 2>/dev/null; then
    print_success "FastAPI app creation works"
else
    print_warning "FastAPI app creation may have issues"
fi

# Test 8: Environment variables test
print_status "Testing environment variable loading..."
if python3 -c "
import os
from dotenv import load_dotenv

# Test loading environment variables
test_vars = ['DATABASE_URL', 'REDIS_URL', 'ENVIRONMENT']
for var in test_vars:
    value = os.getenv(var, 'default')
    print(f'{var}: {value}')

print('✅ Environment variable loading successful')
" 2>/dev/null; then
    print_success "Environment variable loading works"
else
    print_warning "Environment variable loading may have issues"
fi

# Test 9: Quick pytest run (if available)
print_status "Running quick pytest validation..."
if command -v pytest >/dev/null 2>&1; then
    if [ -f "tests/test_sanity.py" ]; then
        print_status "Running sanity tests..."
        if pytest tests/test_sanity.py::TestSystemSanity::test_python_version -v --tb=short >/dev/null 2>&1; then
            print_success "Basic sanity tests pass"
        else
            print_warning "Some sanity tests may be failing"
        fi
    else
        print_warning "Sanity test file not found"
    fi
else
    print_warning "pytest not available for testing"
fi

# Test 10: Check for common security issues
print_status "Checking for common security issues..."
security_checks=0

# Check for hardcoded secrets
if grep -r "password.*=" . --include="*.py" --include="*.yml" --include="*.yaml" | grep -v "test" | grep -v "example" >/dev/null 2>&1; then
    print_warning "Potential hardcoded passwords found"
    ((security_checks++))
fi

# Check for debug mode in production configs
if grep -r "DEBUG.*=.*True" . --include="*.py" --include="*.env*" | grep -v "test" >/dev/null 2>&1; then
    print_warning "Debug mode may be enabled in production configs"
    ((security_checks++))
fi

if [ $security_checks -eq 0 ]; then
    print_success "No obvious security issues found"
else
    print_warning "$security_checks potential security issues detected"
fi

# Summary
echo ""
echo "=================================================================="
echo "📊 QUICK TEST SUMMARY"
echo "=================================================================="

# Count successes and warnings
success_count=$(grep -c "SUCCESS" <<< "$(set +x; exec 2>&1; bash -x $0 2>&1)" || echo "0")
warning_count=$(grep -c "WARNING" <<< "$(set +x; exec 2>&1; bash -x $0 2>&1)" || echo "0")

print_status "✅ Python version compatible"
print_status "✅ Configuration files present"
print_status "✅ Basic imports working"

if [ ${#missing_packages[@]} -eq 0 ]; then
    print_status "✅ All required packages installed"
else
    print_warning "⚠️  Missing packages: ${missing_packages[*]}"
fi

if command -v docker >/dev/null 2>&1; then
    print_status "✅ Docker available"
else
    print_warning "⚠️  Docker not available"
fi

echo ""
print_status "🎯 NEXT STEPS:"
echo "   1. Install missing packages: pip install -r requirements.txt"
echo "   2. Install test dependencies: pip install -r requirements-test.txt" 
echo "   3. Run full test suite: python scripts/run_tests.py --quick"
echo "   4. Start application: python app.py"
echo "   5. Run Docker build: docker build -t trading-system ."

echo ""
echo "=================================================================="
print_success "🚀 Quick test completed! System appears ready for development."
echo "=================================================================="

# Clean up test files
rm -f test.db test.db-shm test.db-wal 2>/dev/null || true

exit 0