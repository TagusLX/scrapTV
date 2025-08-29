#!/usr/bin/env python3
"""
API Test for Idealista Scraper Backend
Tests the backend API endpoints locally
"""

import requests
import sys
import time
import json
from datetime import datetime

class LocalAPITester:
    def __init__(self):
        # Use local backend URL
        self.base_url = "http://localhost:8001"
        self.api_url = f"{self.base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_basic_endpoints(self):
        """Test basic API endpoints"""
        print("\n📋 Testing Basic API Endpoints...")
        
        # Test getting properties
        success1, response1 = self.run_test(
            "Get Properties",
            "GET",
            "properties",
            200
        )
        
        # Test getting stats
        success2, response2 = self.run_test(
            "Get Regional Statistics",
            "GET",
            "stats/regions",
            200
        )
        
        # Test getting scraping sessions
        success3, response3 = self.run_test(
            "Get Scraping Sessions",
            "GET",
            "scraping-sessions",
            200
        )
        
        if success1:
            print(f"   Properties found: {len(response1)}")
        if success2:
            print(f"   Stats found: {len(response2)}")
        if success3:
            print(f"   Sessions found: {len(response3)}")
            
        return success1 and success2 and success3

    def test_administrative_endpoints(self):
        """Test administrative structure endpoints"""
        print("\n🏛️ Testing Administrative Structure Endpoints...")
        
        # Test getting all districts
        success1, response1 = self.run_test(
            "Get All Districts",
            "GET",
            "administrative/districts",
            200
        )
        
        if success1 and response1:
            print(f"   Found {len(response1)} districts")
            
            # Test with faro district
            success2, response2 = self.run_test(
                "Get Concelhos for Faro",
                "GET",
                "administrative/districts/faro/concelhos",
                200
            )
            
            if success2 and response2:
                print(f"   Found {len(response2)} concelhos in Faro")
                
                # Check if tavira is in the list
                if "tavira" in [c.lower() for c in response2]:
                    print(f"   ✅ Found Tavira in Faro concelhos")
                    
                    # Test getting freguesias for tavira
                    success3, response3 = self.run_test(
                        "Get Freguesias for Faro/Tavira",
                        "GET",
                        "administrative/districts/faro/concelhos/tavira/freguesias",
                        200
                    )
                    
                    if success3 and response3:
                        print(f"   Found {len(response3)} freguesias in Faro/Tavira")
                        
                        # Check for target freguesia
                        target_names = [
                            "conceicao e cabanas de tavira",
                            "conceicao-e-cabanas-de-tavira",
                            "conceição e cabanas de tavira"
                        ]
                        
                        found_target = False
                        for target in target_names:
                            if target in [f.lower() for f in response3]:
                                print(f"   ✅ Found target freguesia: {target}")
                                found_target = True
                                break
                        
                        if not found_target:
                            print(f"   ⚠️ Target freguesia not found, available freguesias:")
                            for f in response3[:5]:  # Show first 5
                                print(f"      - {f}")
                        
                        return success1 and success2 and success3
                        
        return success1

    def test_filtering_endpoints(self):
        """Test filtering endpoints"""
        print("\n🔍 Testing Filtering Endpoints...")
        
        # Test properties filter
        success1, response1 = self.run_test(
            "Filter Properties (no filters)",
            "GET",
            "properties/filter",
            200
        )
        
        # Test with distrito filter
        success2, response2 = self.run_test(
            "Filter Properties (distrito=faro)",
            "GET",
            "properties/filter?distrito=faro",
            200
        )
        
        # Test stats filter
        success3, response3 = self.run_test(
            "Filter Stats (distrito=faro)",
            "GET",
            "stats/filter?distrito=faro",
            200
        )
        
        if success1:
            print(f"   Total properties (no filter): {len(response1)}")
        if success2:
            print(f"   Faro properties: {len(response2)}")
        if success3:
            print(f"   Faro stats: {len(response3)}")
            
        return success1 and success2 and success3

    def test_php_export(self):
        """Test PHP export functionality"""
        print("\n📤 Testing PHP Export...")
        
        success, response = self.run_test(
            "Export PHP Data",
            "GET",
            "export/php",
            200
        )
        
        if success and 'php_array' in response:
            php_data = response['php_array']
            print(f"   PHP array contains {len(php_data)} regions")
            
            # Check hierarchical structure
            if php_data:
                sample_region = list(php_data.keys())[0]
                print(f"   Sample region: {sample_region}")
                
                region_data = php_data[sample_region]
                if 'freguesias' in region_data:
                    print(f"   Region has {len(region_data['freguesias'])} concelhos")
                    
        return success

def main():
    """Main test function"""
    print("🚀 Idealista Scraper Local API Tests")
    print("Testing backend API endpoints locally")
    print("=" * 60)
    
    tester = LocalAPITester()
    
    # Test basic endpoints
    basic_passed = tester.test_basic_endpoints()
    
    # Test administrative endpoints
    admin_passed = tester.test_administrative_endpoints()
    
    # Test filtering endpoints
    filter_passed = tester.test_filtering_endpoints()
    
    # Test PHP export
    php_passed = tester.test_php_export()
    
    # Final results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    print(f"\n🎯 COMPONENT TEST RESULTS:")
    print(f"   Basic Endpoints: {'✅ PASSED' if basic_passed else '❌ FAILED'}")
    print(f"   Administrative Endpoints: {'✅ PASSED' if admin_passed else '❌ FAILED'}")
    print(f"   Filtering Endpoints: {'✅ PASSED' if filter_passed else '❌ FAILED'}")
    print(f"   PHP Export: {'✅ PASSED' if php_passed else '❌ FAILED'}")
    
    if tester.tests_passed == tester.tests_run:
        print("\n🎉 All API tests passed!")
        return 0
    else:
        print("\n❌ Some API tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())