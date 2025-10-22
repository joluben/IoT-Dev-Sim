#!/usr/bin/env python3
"""
DevSim Backend Health Check Script
==================================

This script performs comprehensive health checks for the DevSim backend
in production environments. It checks:
- Application responsiveness
- Database connectivity
- Redis connectivity (if configured)
- System resources
- Critical services

Usage:
    python health_check.py [--verbose] [--timeout=30]
"""

import sys
import time
import json
import argparse
import requests
from urllib.parse import urljoin


class HealthChecker:
    """Comprehensive health checker for DevSim backend"""
    
    def __init__(self, base_url="http://localhost:5000", timeout=30, verbose=False):
        self.base_url = base_url
        self.timeout = timeout
        self.verbose = verbose
        self.checks = []
    
    def log(self, message, level="INFO"):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    def check_basic_health(self):
        """Check basic application health endpoint"""
        try:
            self.log("Checking basic health endpoint...")
            url = urljoin(self.base_url, "/api/health")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                self.checks.append({
                    "name": "basic_health",
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "details": data
                })
                self.log(f"Basic health check passed ({response.elapsed.total_seconds():.3f}s)")
                return True
            else:
                self.checks.append({
                    "name": "basic_health",
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                })
                self.log(f"Basic health check failed: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.checks.append({
                "name": "basic_health",
                "status": "unhealthy",
                "error": str(e)
            })
            self.log(f"Basic health check failed: {e}", "ERROR")
            return False
    
    def check_detailed_health(self):
        """Check detailed health endpoint with database and services"""
        try:
            self.log("Checking detailed health endpoint...")
            url = urljoin(self.base_url, "/api/health/detailed")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check overall status
                overall_healthy = data.get("status") == "healthy"
                
                self.checks.append({
                    "name": "detailed_health",
                    "status": "healthy" if overall_healthy else "unhealthy",
                    "response_time": response.elapsed.total_seconds(),
                    "details": data
                })
                
                if overall_healthy:
                    self.log(f"Detailed health check passed ({response.elapsed.total_seconds():.3f}s)")
                else:
                    self.log(f"Detailed health check failed: {data.get('message', 'Unknown error')}", "ERROR")
                
                return overall_healthy
            else:
                self.checks.append({
                    "name": "detailed_health",
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                })
                self.log(f"Detailed health check failed: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.checks.append({
                "name": "detailed_health",
                "status": "unhealthy",
                "error": str(e)
            })
            self.log(f"Detailed health check failed: {e}", "ERROR")
            return False
    
    def check_api_responsiveness(self):
        """Check API responsiveness with a simple endpoint"""
        try:
            self.log("Checking API responsiveness...")
            url = urljoin(self.base_url, "/api/devices")
            response = requests.get(url, timeout=self.timeout)
            
            # Accept both 200 (with data) and 401 (authentication required)
            if response.status_code in [200, 401]:
                self.checks.append({
                    "name": "api_responsiveness",
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "status_code": response.status_code
                })
                self.log(f"API responsiveness check passed ({response.elapsed.total_seconds():.3f}s)")
                return True
            else:
                self.checks.append({
                    "name": "api_responsiveness",
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                })
                self.log(f"API responsiveness check failed: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.checks.append({
                "name": "api_responsiveness",
                "status": "unhealthy",
                "error": str(e)
            })
            self.log(f"API responsiveness check failed: {e}", "ERROR")
            return False
    
    def check_websocket_endpoint(self):
        """Check if WebSocket endpoint is accessible"""
        try:
            self.log("Checking WebSocket endpoint...")
            # For health check, we just verify the endpoint exists
            # We don't actually establish a WebSocket connection
            url = urljoin(self.base_url, "/ws/transmissions")
            response = requests.get(url, timeout=self.timeout)
            
            # WebSocket endpoints typically return 400 for HTTP requests
            if response.status_code in [400, 426]:  # 426 = Upgrade Required
                self.checks.append({
                    "name": "websocket_endpoint",
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "note": "WebSocket endpoint accessible"
                })
                self.log(f"WebSocket endpoint check passed ({response.elapsed.total_seconds():.3f}s)")
                return True
            else:
                self.checks.append({
                    "name": "websocket_endpoint",
                    "status": "warning",
                    "error": f"Unexpected HTTP {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                })
                self.log(f"WebSocket endpoint check warning: HTTP {response.status_code}", "WARN")
                return True  # Not critical for basic health
                
        except requests.exceptions.RequestException as e:
            self.checks.append({
                "name": "websocket_endpoint",
                "status": "warning",
                "error": str(e)
            })
            self.log(f"WebSocket endpoint check failed: {e}", "WARN")
            return True  # Not critical for basic health
    
    def check_system_health(self):
        """Check system resource health"""
        try:
            self.log("Checking system health...")
            url = urljoin(self.base_url, "/api/health/system")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                system_healthy = data.get("status") in ["healthy", "warning"]
                
                self.checks.append({
                    "name": "system_health",
                    "status": "healthy" if system_healthy else "unhealthy",
                    "response_time": response.elapsed.total_seconds(),
                    "details": data
                })
                
                if system_healthy:
                    self.log(f"System health check passed ({response.elapsed.total_seconds():.3f}s)")
                else:
                    self.log(f"System health check failed: {data.get('status', 'unknown')}", "ERROR")
                
                return system_healthy
            else:
                self.checks.append({
                    "name": "system_health",
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                })
                self.log(f"System health check failed: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.checks.append({
                "name": "system_health",
                "status": "warning",
                "error": str(e)
            })
            self.log(f"System health check failed: {e}", "WARN")
            return True  # Not critical for basic health
    
    def check_readiness(self):
        """Check readiness probe"""
        try:
            self.log("Checking readiness probe...")
            url = urljoin(self.base_url, "/api/health/readiness")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                ready = data.get("ready", False)
                
                self.checks.append({
                    "name": "readiness",
                    "status": "healthy" if ready else "unhealthy",
                    "response_time": response.elapsed.total_seconds(),
                    "details": data
                })
                
                if ready:
                    self.log(f"Readiness check passed ({response.elapsed.total_seconds():.3f}s)")
                else:
                    self.log(f"Readiness check failed: {data.get('checks', {})}", "ERROR")
                
                return ready
            else:
                self.checks.append({
                    "name": "readiness",
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                })
                self.log(f"Readiness check failed: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.checks.append({
                "name": "readiness",
                "status": "unhealthy",
                "error": str(e)
            })
            self.log(f"Readiness check failed: {e}", "ERROR")
            return False
    
    def run_all_checks(self):
        """Run all health checks and return overall status"""
        self.log("Starting comprehensive health checks...")
        
        start_time = time.time()
        
        # Run all checks
        checks_results = [
            self.check_basic_health(),
            self.check_detailed_health(),
            self.check_api_responsiveness(),
            self.check_readiness(),
            self.check_system_health(),
            self.check_websocket_endpoint()
        ]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Determine overall health
        critical_checks = checks_results[:4]  # First 4 are critical (basic, detailed, api, readiness)
        overall_healthy = all(critical_checks)
        
        # Summary
        healthy_count = sum(1 for result in checks_results if result)
        total_count = len(checks_results)
        
        summary = {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "checks_passed": healthy_count,
            "total_checks": total_count,
            "total_time": total_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "checks": self.checks
        }
        
        if self.verbose:
            print("\n" + "="*50)
            print("HEALTH CHECK SUMMARY")
            print("="*50)
            print(f"Overall Status: {summary['overall_status'].upper()}")
            print(f"Checks Passed: {healthy_count}/{total_count}")
            print(f"Total Time: {total_time:.3f}s")
            print(f"Timestamp: {summary['timestamp']}")
            
            if not overall_healthy:
                print("\nFAILED CHECKS:")
                for check in self.checks:
                    if check['status'] == 'unhealthy':
                        print(f"  - {check['name']}: {check.get('error', 'Unknown error')}")
        
        return overall_healthy, summary


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="DevSim Backend Health Check")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--timeout", "-t", type=int, default=30,
                       help="Request timeout in seconds (default: 30)")
    parser.add_argument("--url", "-u", default="http://localhost:5000",
                       help="Backend URL (default: http://localhost:5000)")
    parser.add_argument("--json", "-j", action="store_true",
                       help="Output results in JSON format")
    
    args = parser.parse_args()
    
    # Create health checker
    checker = HealthChecker(
        base_url=args.url,
        timeout=args.timeout,
        verbose=args.verbose and not args.json
    )
    
    # Run health checks
    try:
        healthy, summary = checker.run_all_checks()
        
        if args.json:
            print(json.dumps(summary, indent=2))
        elif not args.verbose:
            # Simple output for non-verbose mode
            status = "HEALTHY" if healthy else "UNHEALTHY"
            print(f"DevSim Backend: {status}")
        
        # Exit with appropriate code
        sys.exit(0 if healthy else 1)
        
    except KeyboardInterrupt:
        print("\nHealth check interrupted")
        sys.exit(2)
    except Exception as e:
        if args.json:
            error_summary = {
                "overall_status": "error",
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            print(json.dumps(error_summary, indent=2))
        else:
            print(f"Health check failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()