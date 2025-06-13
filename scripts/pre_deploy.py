#!/usr/bin/env python3
"""
Pre-deployment verification script
Checks system readiness before deployment
"""

import os
import sys
import yaml

import asyncio
import logging
from typing import Dict, List, Any
from pathlib import Path
import redis
import psycopg2
from datetime import datetime
import requests
import ssl

# Setup logging
logger = logging.getLogger(__name__
class PreDeploymentCheck:
    def __init__(self):

        def _load_config(self) -> Dict[str, Any]:
            """Load configuration files"""
            config={
            # Load main config
            with open('config/security.yaml', 'r') as f:

            # Load environment variables
            'DB_HOST': os.getenv('DB_HOST'),
            'DB_PORT': os.getenv('DB_PORT'),
            'DB_NAME': os.getenv('DB_NAME'),
            'REDIS_HOST': os.getenv('REDIS_HOST'),
            'REDIS_PORT': os.getenv('REDIS_PORT'),
            'API_HOST': os.getenv('API_HOST'),
            'API_PORT': os.getenv('API_PORT'

        return config

        async def run_checks(self):
        """Run all pre-deployment checks"""
        logger.info("Starting pre-deployment checks..."
        # Environment checks
        await self._check_environment_variables(
        await self._check_file_permissions(
        # Security checks
        await self._check_ssl_certificates(
        await self._check_firewall_rules(
        # Database checks
        await self._check_database_connection(
        await self._check_database_migrations(
        # Redis checks
        await self._check_redis_connection(
        # API checks
        await self._check_api_endpoints(
        # Cloud checks
        await self._check_cloud_configuration(
        # Print results
        self._print_results(
    return self.checks_passed

    async def _check_environment_variables(self):
    """Check required environment variables"""
    required_vars=[
    'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
    'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD',
    'JWT_SECRET_KEY', 'API_HOST', 'API_PORT'
    missing_vars=[var for var in required_vars if not os.getenv(var}]

    if missing_vars:
        self._add_result('Environment Variables', False, f"Missing variables: {', '.join(missing_vars)}"
        else:
            self._add_result('Environment Variables', True
            async def _check_file_permissions(self):
            """Check file permissions"""
            critical_files=[
            'config/security.yaml',
            '.env',
            'logs/',
            'data/']

            for file_path in critical_files:
                path=Path(file_path
                if not path.exists():
                    self._add_result('File Permissions', False, f"Missing file/directory: {file_path}"
                continue

                if not os.access(path, os.R_OK):
                    self._add_result('File Permissions', False, f"Cannot read: {file_path}"
                    async def _check_ssl_certificates(self):
                    """Check SSL certificates"""
                    cert_path=self.config['security']['network']['ssl']['cert_path']
                    key_path=self.config['security']['network']['ssl']['key_path']

                    try:
                        # Check certificate
                        with open(cert_path, 'r') as f:
                        cert=ssl.PEM_cert_to_DER_cert(f.read(
                        # Check private key
                        with open(key_path, 'r') as f:
                        key=ssl.PEM_privatekey_to_DER_privatekey(f.read(
                        self._add_result('SSL Certificates', True
                        except Exception as e:
                            self._add_result('SSL Certificates', False, str(e
                            async def _check_database_connection(self):
                            """Check database connection"""
                            try:
                                conn=psycopg2.connect(

                                conn.close(
                                self._add_result('Database Connection', True
                                except Exception as e:
                                    self._add_result('Database Connection', False, str(e
                                    async def _check_redis_connection(self):
                                    """Check Redis connection"""
                                    try:
                                        r=redis.Redis(

                                        r.ping(
                                        self._add_result('Redis Connection', True
                                        except Exception as e:
                                            self._add_result('Redis Connection', False, str(e
                                            async def _check_api_endpoints(self):
                                            """Check API endpoints"""
                                            base_url=f"http://{
                                            self.config['env'}['API_HOST']}:{
                                            self.config['env'}['API_PORT']}"

                                            try:
                                                # Check health endpoint
                                                response=requests.get(f"{base_url}/health"
                                                self._add_result('API Health Endpoint', True
                                                else:
                                                    self._add_result('API Health Endpoint', False, f"Status code: {response.status_code}"
                                                    except Exception as e:
                                                        self._add_result('API Endpoints', False, str(e
                                                        async def _check_cloud_configuration(self):
                                                        """Check cloud provider configuration"""
                                                        cloud_provider=os.getenv('CLOUD_PROVIDER'
                                                        required_vars=['AWS_ACCESS_KEY', 'AWS_SECRET_KEY', 'AWS_REGION']
                                                        required_vars=['GOOGLE_APPLICATION_CREDENTIALS']
                                                        else:
                                                            self._add_result('Cloud Configuration', False, "Invalid cloud provider"
                                                        return

                                                        missing_vars=[var for var in required_vars if not os.getenv(var]]

                                                        if missing_vars:
                                                            self._add_result('Cloud Configuration', False, f"Missing variables: {', '.join(missing_vars)}"
                                                            else:
                                                                self._add_result('Cloud Configuration', True
                                                                """Add check result"""
                                                                result={
                                                                'check': check_name,
                                                                'passed': passed,
                                                                'message': message,
                                                                'timestamp': datetime.now().isoformat(

                                                                self.results.append(result
                                                                if not passed:

                                                                    def _print_results(self):
                                                                        """Print check results"""
                                                                        print("\nPre-deployment Check Results:"
                                                                        for result in self.results:
                                                                            status="✅ PASSED" if result['passed'} else "❌ FAILED"
                                                                            print(f"{status} - {result['check'}}"
                                                                            if result['message']:
                                                                                print(f"   Message: {result['message'}}"
                                                                                print("\nOverall Status:", "✅ READY" if self.checks_passed else "❌ NOT READY"
                                                                                async def main(]:
                                                                                checker=PreDeploymentCheck(
                                                                                success=await checker.run_checks(
                                                                                sys.exit(0 if success else 1
                                                                                asyncio.run(main(
