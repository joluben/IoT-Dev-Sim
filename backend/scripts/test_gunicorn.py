#!/usr/bin/env python3
"""
DevSim Gunicorn Configuration Test
=================================

This script tests the Gunicorn configuration and validates that the
production setup is working correctly.
"""

import os
import sys
import time
import requests
import subprocess
import threading
from pathlib import Path


class GunicornTester:
    """Test Gunicorn configuration and deployment"""
    
    def __init__(self):
        self.process = None
        self.base_url = "http://localhost:5000"
        self.startup_timeout = 30
        
    def start_gunicorn(self):
        """Start Gunicorn in test mode"""
        print("🚀 Starting Gunicorn for testing...")
        
        # Set test environment
        env = os.environ.copy()
        env.update({
            'FLASK_ENV': 'production',
            'FLASK_DEBUG': 'false',
            'SECRET_KEY': 'test-secret-key-for-gunicorn-testing',
            'ENCRYPTION_KEY': 'test-encryption-key-for-gunicorn-testing',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-for-gunicorn-testing',
            'ALLOW_SENSITIVE_CONNECTIONS': 'false'
        })
        
        # Start Gunicorn with test configuration
        cmd = [
            'gunicorn',
            '--config', 'gunicorn_config.py',
            '--bind', '0.0.0.0:5000',
            '--workers', '2',  # Reduced for testing
            '--timeout', '30',
            '--log-level', 'info',
            'run:app'
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=os.getcwd()
            )
            
            print(f"✅ Gunicorn started with PID: {self.process.pid}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start Gunicorn: {e}")
            return False
    
    def wait_for_startup(self):
        """Wait for Gunicorn to start and be ready"""
        print("⏳ Waiting for Gunicorn to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < self.startup_timeout:
            try:
                response = requests.get(f"{self.base_url}/api/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Gunicorn is ready and responding")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
        
        print("❌ Timeout waiting for Gunicorn to start")
        return False
    
    def test_health_endpoints(self):
        """Test all health check endpoints"""
        print("🔍 Testing health check endpoints...")
        
        endpoints = [
            ("/api/health", "Basic health check"),
            ("/api/health/detailed", "Detailed health check"),
            ("/api/health/system", "System health check"),
            ("/api/health/readiness", "Readiness probe"),
            ("/api/health/liveness", "Liveness probe"),
            ("/api/health/security", "Security health check")
        ]
        
        results = []
        
        for endpoint, description in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, timeout=10)
                
                success = response.status_code in [200, 503]  # 503 is acceptable for some health checks
                status = "✅ PASS" if success else "❌ FAIL"
                
                results.append({
                    'endpoint': endpoint,
                    'description': description,
                    'status_code': response.status_code,
                    'success': success,
                    'response_time': response.elapsed.total_seconds()
                })
                
                print(f"  {status} {endpoint} - {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
                
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'description': description,
                    'success': False,
                    'error': str(e)
                })
                print(f"  ❌ FAIL {endpoint} - {e}")
        
        return results
    
    def test_api_endpoints(self):
        """Test basic API endpoints"""
        print("🔍 Testing API endpoints...")
        
        endpoints = [
            ("/api/devices", "Devices API"),
            ("/api/projects", "Projects API"),
            ("/api/connections", "Connections API")
        ]
        
        results = []
        
        for endpoint, description in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, timeout=10)
                
                # Accept 200 (success) or 401 (auth required) as valid responses
                success = response.status_code in [200, 401]
                status = "✅ PASS" if success else "❌ FAIL"
                
                results.append({
                    'endpoint': endpoint,
                    'description': description,
                    'status_code': response.status_code,
                    'success': success,
                    'response_time': response.elapsed.total_seconds()
                })
                
                print(f"  {status} {endpoint} - {response.status_code} ({response.elapsed.total_seconds():.3f}s)")
                
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'description': description,
                    'success': False,
                    'error': str(e)
                })
                print(f"  ❌ FAIL {endpoint} - {e}")
        
        return results
    
    def test_performance(self):
        """Test basic performance metrics"""
        print("🔍 Testing performance...")
        
        # Test multiple concurrent requests
        import concurrent.futures
        
        def make_request():
            try:
                response = requests.get(f"{self.base_url}/api/health", timeout=10)
                return response.elapsed.total_seconds()
            except:
                return None
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            response_times = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Filter out failed requests
        valid_times = [t for t in response_times if t is not None]
        
        if valid_times:
            avg_time = sum(valid_times) / len(valid_times)
            max_time = max(valid_times)
            min_time = min(valid_times)
            
            print(f"  📊 Concurrent requests: {len(valid_times)}/10 successful")
            print(f"  📊 Average response time: {avg_time:.3f}s")
            print(f"  📊 Min response time: {min_time:.3f}s")
            print(f"  📊 Max response time: {max_time:.3f}s")
            
            # Performance thresholds
            performance_ok = avg_time < 1.0 and max_time < 2.0
            status = "✅ PASS" if performance_ok else "⚠️  SLOW"
            print(f"  {status} Performance test")
            
            return {
                'success': performance_ok,
                'avg_time': avg_time,
                'max_time': max_time,
                'min_time': min_time,
                'successful_requests': len(valid_times)
            }
        else:
            print("  ❌ FAIL All concurrent requests failed")
            return {'success': False, 'error': 'All requests failed'}
    
    def stop_gunicorn(self):
        """Stop Gunicorn process"""
        if self.process:
            print("🛑 Stopping Gunicorn...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                print("✅ Gunicorn stopped gracefully")
            except subprocess.TimeoutExpired:
                print("⚠️  Forcing Gunicorn termination...")
                self.process.kill()
                self.process.wait()
    
    def run_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("DevSim Gunicorn Configuration Test")
        print("=" * 60)
        
        # Check prerequisites
        if not os.path.exists('gunicorn_config.py'):
            print("❌ gunicorn_config.py not found")
            return False
        
        if not os.path.exists('run.py'):
            print("❌ run.py not found")
            return False
        
        try:
            # Start Gunicorn
            if not self.start_gunicorn():
                return False
            
            # Wait for startup
            if not self.wait_for_startup():
                return False
            
            print("\n" + "=" * 60)
            
            # Run tests
            health_results = self.test_health_endpoints()
            print()
            api_results = self.test_api_endpoints()
            print()
            performance_results = self.test_performance()
            
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            
            # Calculate success rates
            health_success = sum(1 for r in health_results if r.get('success', False))
            api_success = sum(1 for r in api_results if r.get('success', False))
            performance_success = performance_results.get('success', False)
            
            print(f"Health endpoints: {health_success}/{len(health_results)} passed")
            print(f"API endpoints: {api_success}/{len(api_results)} passed")
            print(f"Performance test: {'PASS' if performance_success else 'FAIL'}")
            
            # Overall result
            overall_success = (
                health_success == len(health_results) and
                api_success == len(api_results) and
                performance_success
            )
            
            if overall_success:
                print("\n✅ ALL TESTS PASSED - Gunicorn configuration is working correctly!")
            else:
                print("\n❌ SOME TESTS FAILED - Please check the configuration")
            
            return overall_success
            
        finally:
            self.stop_gunicorn()


def main():
    """Main entry point"""
    tester = GunicornTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()