#!/usr/bin/env python3
"""
Quick test script to verify endpoints are working
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_endpoint(method, endpoint, data=None, expected_status=None):
    """Test an endpoint and return result"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=10)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, timeout=10)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, timeout=10)
        else:
            return {'error': f'Unsupported method: {method}'}
        
        result = {
            'method': method.upper(),
            'endpoint': endpoint,
            'status_code': response.status_code,
            'success': True
        }
        
        if expected_status and response.status_code != expected_status:
            result['success'] = False
            result['expected'] = expected_status
        
        try:
            result['response'] = response.json()
        except:
            result['response'] = response.text[:200] + '...' if len(response.text) > 200 else response.text
        
        return result
        
    except Exception as e:
        return {
            'method': method.upper(),
            'endpoint': endpoint,
            'error': str(e),
            'success': False
        }

def main():
    print("Testing DevSim Endpoints")
    print("=" * 40)
    
    # Test basic health
    result = test_endpoint('GET', '/api/health')
    print(f"Health Check: {'✅' if result['success'] else '❌'} {result.get('status_code', 'ERROR')}")
    if not result['success']:
        print(f"  Error: {result.get('error', 'Unknown')}")
        return
    
    # Test device creation
    device_data = {
        'name': 'Test Device',
        'description': 'Test device for endpoint validation'
    }
    
    result = test_endpoint('POST', '/api/devices', device_data)
    print(f"Create Device: {'✅' if result['success'] else '❌'} {result.get('status_code', 'ERROR')}")
    
    if result['success'] and result.get('status_code') == 201:
        device_id = result['response']['id']
        print(f"  Created device ID: {device_id}")
        
        # Test debug endpoint
        result = test_endpoint('GET', f'/api/devices/{device_id}/debug')
        print(f"Debug Device: {'✅' if result['success'] else '❌'} {result.get('status_code', 'ERROR')}")
        
        # Test transmission config
        config_data = {
            'device_type': 'WebApp',
            'transmission_frequency': 60,
            'transmission_enabled': False,
            'connection_id': 1,  # Assuming connection 1 exists
            'include_device_id_in_payload': True,
            'auto_reset_counter': False
        }
        
        result = test_endpoint('PUT', f'/api/devices/{device_id}/transmission-config', config_data)
        print(f"Update Config: {'✅' if result['success'] else '❌'} {result.get('status_code', 'ERROR')}")
        if not result['success']:
            print(f"  Error: {result.get('response', {}).get('error', 'Unknown')}")
        
        # Test transmit endpoint
        transmit_data = {'connection_id': 1}
        result = test_endpoint('POST', f'/api/devices/{device_id}/transmit', transmit_data)
        print(f"Transmit Test: {'✅' if result.get('status_code') in [200, 400] else '❌'} {result.get('status_code', 'ERROR')}")
        if result.get('status_code') == 400:
            print(f"  Expected 400 (no CSV data): {result.get('response', {}).get('error', 'Unknown')}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()