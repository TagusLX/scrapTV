import requests
import sys
import time
import json
from datetime import datetime

class IdealistaScraperAPITester:
    def __init__(self, base_url="https://property-radar-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
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
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
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

    def test_administrative_endpoints(self):
        """Test administrative hierarchy endpoints"""
        print("\n🏛️ Testing Administrative Endpoints...")
        
        # Test getting all districts
        success1, districts_response = self.run_test(
            "Get All Districts",
            "GET",
            "administrative/districts",
            200
        )
        
        if not success1:
            return False
            
        districts = districts_response.get('districts', [])
        print(f"   Found {len(districts)} districts")
        
        if not districts:
            print("   ❌ No districts found")
            return False
            
        # Test with first district
        test_district = districts[0]['id']
        print(f"   Testing with district: {test_district}")
        
        # Test getting concelhos for a district
        success2, concelhos_response = self.run_test(
            f"Get Concelhos for {test_district}",
            "GET",
            f"administrative/districts/{test_district}/concelhos",
            200
        )
        
        if not success2:
            return False
            
        concelhos = concelhos_response.get('concelhos', [])
        print(f"   Found {len(concelhos)} concelhos in {test_district}")
        
        if not concelhos:
            print(f"   ❌ No concelhos found for {test_district}")
            return False
            
        # Test with first concelho
        test_concelho = concelhos[0]['id']
        print(f"   Testing with concelho: {test_concelho}")
        
        # Test getting freguesias for a distrito/concelho
        success3, freguesias_response = self.run_test(
            f"Get Freguesias for {test_district}/{test_concelho}",
            "GET",
            f"administrative/districts/{test_district}/concelhos/{test_concelho}/freguesias",
            200
        )
        
        if not success3:
            return False
            
        freguesias = freguesias_response.get('freguesias', [])
        print(f"   Found {len(freguesias)} freguesias in {test_district}/{test_concelho}")
        
        # Test hierarchical naming format
        if freguesias:
            sample_freguesia = freguesias[0]
            print(f"   Sample hierarchical format: {test_district} > {test_concelho} > {sample_freguesia['name']}")
            
            # Verify display formatting
            if 'name_display' in sample_freguesia:
                print(f"   Display name: {sample_freguesia['name_display']}")
        
        # Test invalid district (should return 404)
        success4, error_response = self.run_test(
            "Get Concelhos for Invalid District",
            "GET",
            "administrative/districts/invalid-district/concelhos",
            404
        )
        
        # Test invalid concelho (should return 404)
        success5, error_response = self.run_test(
            f"Get Freguesias for Invalid Concelho",
            "GET",
            f"administrative/districts/{test_district}/concelhos/invalid-concelho/freguesias",
            404
        )
        
        return success1 and success2 and success3 and success4 and success5

    def test_filtering_endpoints(self):
        """Test filtering endpoints for properties and statistics"""
        print("\n🔍 Testing Filtering Endpoints...")
        
        # First, get some districts to test with
        success_districts, districts_response = self.run_test(
            "Get Districts for Filtering Tests",
            "GET",
            "administrative/districts",
            200
        )
        
        if not success_districts:
            print("   ❌ Cannot get districts for filtering tests")
            return False
            
        districts = districts_response.get('districts', [])
        if not districts:
            print("   ❌ No districts available for filtering tests")
            return False
            
        test_district = districts[0]['id']
        print(f"   Using district for filtering tests: {test_district}")
        
        # Test properties filtering - no filters
        success1, response1 = self.run_test(
            "Filter Properties (no filters)",
            "GET",
            "properties/filter",
            200
        )
        
        # Test properties filtering - by distrito
        success2, response2 = self.run_test(
            "Filter Properties (by distrito)",
            "GET",
            f"properties/filter?distrito={test_district}",
            200
        )
        
        # Test properties filtering - by distrito and operation type
        success3, response3 = self.run_test(
            "Filter Properties (by distrito and operation)",
            "GET",
            f"properties/filter?distrito={test_district}&operation_type=sale",
            200
        )
        
        # Test properties filtering - with limit
        success4, response4 = self.run_test(
            "Filter Properties (with limit)",
            "GET",
            f"properties/filter?distrito={test_district}&limit=5",
            200
        )
        
        if success1:
            print(f"   Properties (no filter): {len(response1)}")
        if success2:
            print(f"   Properties (distrito filter): {len(response2)}")
            # Check if display_info is present
            if response2 and len(response2) > 0 and 'display_info' in response2[0]:
                display_info = response2[0]['display_info']
                if 'full_display' in display_info:
                    print(f"   Sample hierarchical display: {display_info['full_display']}")
        if success3:
            print(f"   Properties (distrito + operation): {len(response3)}")
        if success4:
            print(f"   Properties (with limit): {len(response4)}")
        
        # Test statistics filtering - no filters
        success5, stats1 = self.run_test(
            "Filter Statistics (no filters)",
            "GET",
            "stats/filter",
            200
        )
        
        # Test statistics filtering - by distrito
        success6, stats2 = self.run_test(
            "Filter Statistics (by distrito)",
            "GET",
            f"stats/filter?distrito={test_district}",
            200
        )
        
        if success5:
            print(f"   Statistics (no filter): {len(stats1)}")
        if success6:
            print(f"   Statistics (distrito filter): {len(stats2)}")
            # Check hierarchical naming in stats
            if stats2 and len(stats2) > 0 and 'display_info' in stats2[0]:
                display_info = stats2[0]['display_info']
                if 'full_display' in display_info:
                    print(f"   Sample stats hierarchical display: {display_info['full_display']}")
        
        # Test with multiple administrative levels (if we have the data)
        # Get concelhos for more detailed filtering
        success_concelhos, concelhos_response = self.run_test(
            f"Get Concelhos for Detailed Filtering",
            "GET",
            f"administrative/districts/{test_district}/concelhos",
            200
        )
        
        if success_concelhos:
            concelhos = concelhos_response.get('concelhos', [])
            if concelhos:
                test_concelho = concelhos[0]['id']
                print(f"   Testing detailed filtering with concelho: {test_concelho}")
                
                # Test filtering by distrito and concelho
                success7, response7 = self.run_test(
                    "Filter Properties (distrito + concelho)",
                    "GET",
                    f"properties/filter?distrito={test_district}&concelho={test_concelho}",
                    200
                )
                
                success8, stats3 = self.run_test(
                    "Filter Statistics (distrito + concelho)",
                    "GET",
                    f"stats/filter?distrito={test_district}&concelho={test_concelho}",
                    200
                )
                
                if success7:
                    print(f"   Properties (distrito + concelho): {len(response7)}")
                if success8:
                    print(f"   Statistics (distrito + concelho): {len(stats3)}")
                
                return (success1 and success2 and success3 and success4 and 
                       success5 and success6 and success7 and success8)
        
        return success1 and success2 and success3 and success4 and success5 and success6

    def test_export_php(self):
        """Test PHP export functionality with hierarchical naming"""
        success, response = self.run_test(
            "Export PHP Data",
            "GET",
            "export/php",
            200
        )
        if success and 'php_array' in response:
            php_data = response['php_array']
            print(f"   PHP array contains {len(php_data)} regions")
            
            # Test hierarchical structure
            if php_data:
                sample_region = list(php_data.keys())[0]
                print(f"   Sample region: {sample_region}")
                
                # Check if the structure has the expected hierarchy
                region_data = php_data[sample_region]
                if 'freguesias' in region_data:
                    print(f"   Region has {len(region_data['freguesias'])} concelhos")
                    if region_data['freguesias']:
                        sample_concelho = list(region_data['freguesias'].keys())[0]
                        concelho_data = region_data['freguesias'][sample_concelho]
                        if 'freguesias' in concelho_data:
                            print(f"   Concelho {sample_concelho} has {len(concelho_data['freguesias'])} freguesias")
                            
                            # Test hierarchical naming format
                            if concelho_data['freguesias']:
                                sample_freguesia = list(concelho_data['freguesias'].keys())[0]
                                print(f"   Sample hierarchical path: {sample_region} > {sample_concelho} > {sample_freguesia}")
                                
            return True
        return False

    def test_start_scraping(self):
        """Test starting a scraping session"""
        success, response = self.run_test(
            "Start Scraping Session",
            "POST",
            "scrape/start",
            200
        )
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            print(f"   Session ID: {self.session_id}")
            return True
        return False

    def test_get_properties(self):
        """Test getting properties with various filters"""
        # Test without filters
        success1, response1 = self.run_test(
            "Get Properties (no filters)",
            "GET",
            "properties",
            200
        )
        
        # Test with limit
        success2, response2 = self.run_test(
            "Get Properties (with limit)",
            "GET",
            "properties?limit=10",
            200
        )
        
        if success1:
            print(f"   Total properties found: {len(response1)}")
        if success2:
            print(f"   Limited properties found: {len(response2)}")
            
        return success1 and success2

def main():
    print("🚀 Starting Portuguese Real Estate Scraper API Tests")
    print("=" * 60)
    
    tester = IdealistaScraperAPITester()
    
    # Test the specific endpoints mentioned in the review request
    print("\n🏛️ Testing Administrative Endpoints...")
    admin_success = tester.test_administrative_endpoints()
    
    print("\n🔍 Testing Filtering Endpoints...")
    filter_success = tester.test_filtering_endpoints()
    
    print("\n📤 Testing PHP Export Endpoint...")
    php_success = tester.test_export_php()
    
    # Test basic functionality
    print("\n📋 Testing Basic Endpoints...")
    props_success = tester.test_get_properties()
    
    # Optional: Test scraping if needed
    print("\n🕷️ Testing Scraping Session (Optional)...")
    scraping_success = tester.test_start_scraping()
    
    # Final results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    # Summary of key tests
    print("\n📋 Key Test Results:")
    print(f"   Administrative Endpoints: {'✅ PASS' if admin_success else '❌ FAIL'}")
    print(f"   Filtering Endpoints: {'✅ PASS' if filter_success else '❌ FAIL'}")
    print(f"   PHP Export Endpoint: {'✅ PASS' if php_success else '❌ FAIL'}")
    print(f"   Basic Properties: {'✅ PASS' if props_success else '❌ FAIL'}")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())