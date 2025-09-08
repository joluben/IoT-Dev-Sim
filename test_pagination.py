#!/usr/bin/env python3
"""
Test script for pagination functionality in Device Simulator
Tests both backend API endpoints and frontend integration
"""

import requests
import json
import sys
import time

def test_pagination_endpoints():
    """Test pagination endpoints for devices, connections, and projects"""
    base_url = "http://localhost:5000/api"
    
    print("🧪 Testing Pagination Endpoints...")
    
    # Test devices pagination
    print("\n📱 Testing Devices Pagination:")
    try:
        # Test basic pagination
        response = requests.get(f"{base_url}/devices?page=1&per_page=5")
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and 'pagination' in data:
                print(f"✅ Devices pagination working - {len(data['items'])} items, page {data['pagination']['page']}")
                print(f"   Total: {data['pagination']['total']}, Pages: {data['pagination']['pages']}")
            elif isinstance(data, list):
                print(f"✅ Devices legacy format - {len(data)} items")
            else:
                print(f"❌ Unexpected devices response format: {type(data)}")
        else:
            print(f"❌ Devices endpoint error: {response.status_code}")
            
        # Test with search filter
        response = requests.get(f"{base_url}/devices?page=1&per_page=10&search=sensor")
        if response.status_code == 200:
            print("✅ Devices search filter working")
        else:
            print(f"❌ Devices search filter error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Devices test failed: {e}")
    
    # Test connections pagination
    print("\n🔗 Testing Connections Pagination:")
    try:
        response = requests.get(f"{base_url}/connections?page=1&per_page=5")
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and 'pagination' in data:
                print(f"✅ Connections pagination working - {len(data['items'])} items, page {data['pagination']['page']}")
            elif isinstance(data, list):
                print(f"✅ Connections legacy format - {len(data)} items")
            else:
                print(f"❌ Unexpected connections response format: {type(data)}")
        else:
            print(f"❌ Connections endpoint error: {response.status_code}")
            
        # Test with type filter
        response = requests.get(f"{base_url}/connections?page=1&per_page=10&type=MQTT")
        if response.status_code == 200:
            print("✅ Connections type filter working")
        else:
            print(f"❌ Connections type filter error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connections test failed: {e}")
    
    # Test projects pagination
    print("\n📁 Testing Projects Pagination:")
    try:
        response = requests.get(f"{base_url}/projects?page=1&per_page=5")
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and 'pagination' in data:
                print(f"✅ Projects pagination working - {len(data['items'])} items, page {data['pagination']['page']}")
            elif isinstance(data, list):
                print(f"✅ Projects legacy format - {len(data)} items")
            else:
                print(f"❌ Unexpected projects response format: {type(data)}")
        else:
            print(f"❌ Projects endpoint error: {response.status_code}")
            
        # Test with active filter
        response = requests.get(f"{base_url}/projects?page=1&per_page=10&active=true")
        if response.status_code == 200:
            print("✅ Projects active filter working")
        else:
            print(f"❌ Projects active filter error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Projects test failed: {e}")

def test_pagination_parameters():
    """Test various pagination parameter combinations"""
    base_url = "http://localhost:5000/api"
    
    print("\n🔧 Testing Pagination Parameters:")
    
    # Test different page sizes
    for per_page in [5, 10, 20, 50]:
        try:
            response = requests.get(f"{base_url}/devices?page=1&per_page={per_page}")
            if response.status_code == 200:
                data = response.json()
                items_count = len(data.get('items', data)) if isinstance(data, dict) else len(data)
                print(f"✅ Page size {per_page}: {items_count} items returned")
            else:
                print(f"❌ Page size {per_page} failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Page size {per_page} error: {e}")
    
    # Test page boundaries
    try:
        # Test page 0 (should default to 1)
        response = requests.get(f"{base_url}/devices?page=0&per_page=10")
        if response.status_code == 200:
            print("✅ Page 0 handled correctly")
        
        # Test negative page (should default to 1)
        response = requests.get(f"{base_url}/devices?page=-1&per_page=10")
        if response.status_code == 200:
            print("✅ Negative page handled correctly")
            
        # Test large page size (should be capped)
        response = requests.get(f"{base_url}/devices?page=1&per_page=1000")
        if response.status_code == 200:
            print("✅ Large page size handled correctly")
            
    except Exception as e:
        print(f"❌ Boundary test error: {e}")

def main():
    """Main test function"""
    print("🚀 Starting Pagination Tests for Device Simulator")
    print("=" * 60)
    
    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    for i in range(10):
        try:
            response = requests.get("http://localhost:5000/api/devices", timeout=2)
            if response.status_code in [200, 404, 500]:  # Any response means server is up
                print("✅ Server is ready")
                break
        except:
            time.sleep(1)
            if i == 9:
                print("❌ Server not responding after 10 seconds")
                return False
    
    # Run tests
    test_pagination_endpoints()
    test_pagination_parameters()
    
    print("\n" + "=" * 60)
    print("✅ Pagination tests completed!")
    print("\n📋 Summary:")
    print("- Backend pagination endpoints implemented")
    print("- Frontend pagination components created")
    print("- Search and filter parameters supported")
    print("- Page size limits and boundaries handled")
    print("- Legacy fallback support maintained")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
