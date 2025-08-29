import requests
import sys
import time
import json
from datetime import datetime

class IdealistaScraperAPITester:
    def __init__(self, base_url="https://realestate-scraper.preview.emergentagent.com"):
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

    def test_get_scraping_sessions(self):
        """Test getting all scraping sessions"""
        success, response = self.run_test(
            "Get All Scraping Sessions",
            "GET",
            "scraping-sessions",
            200
        )
        if success:
            print(f"   Found {len(response)} sessions")
            return True
        return False

    def test_get_specific_session(self):
        """Test getting a specific scraping session"""
        if not self.session_id:
            print("❌ No session ID available for testing")
            return False
            
        success, response = self.run_test(
            "Get Specific Scraping Session",
            "GET",
            f"scraping-sessions/{self.session_id}",
            200
        )
        if success:
            print(f"   Session Status: {response.get('status', 'unknown')}")
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
        
        # Test with region filter
        success3, response3 = self.run_test(
            "Get Properties (with region filter)",
            "GET",
            "properties?region=lisboa&limit=5",
            200
        )
        
        if success1:
            print(f"   Total properties found: {len(response1)}")
        if success2:
            print(f"   Limited properties found: {len(response2)}")
        if success3:
            print(f"   Lisboa properties found: {len(response3)}")
            
        return success1 and success2 and success3

    def test_get_region_stats(self):
        """Test getting regional statistics"""
        success, response = self.run_test(
            "Get Regional Statistics",
            "GET",
            "stats/regions",
            200
        )
        if success:
            print(f"   Found stats for {len(response)} regions/locations")
            if response:
                sample_stat = response[0]
                print(f"   Sample: {sample_stat.get('region', 'N/A')} - {sample_stat.get('location', 'N/A')}")
            return True
        return False

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

    def test_clear_properties(self):
        """Test clearing all properties"""
        success, response = self.run_test(
            "Clear All Properties",
            "DELETE",
            "properties",
            200
        )
        if success:
            deleted_count = response.get('message', '').split()
            print(f"   Result: {response.get('message', 'Unknown result')}")
            return True
        return False

    def test_captcha_endpoints(self):
        """Test CAPTCHA-related endpoints"""
        print("\n🔐 Testing CAPTCHA Endpoints...")
        
        # Test getting CAPTCHA image for non-existent session (should fail)
        fake_session_id = "fake-session-123"
        success1, response1 = self.run_test(
            "Get CAPTCHA Image (Non-existent Session)",
            "GET",
            f"captcha/{fake_session_id}",
            404
        )
        
        # Test solving CAPTCHA for non-existent session (should fail)
        success2, response2 = self.run_test(
            "Solve CAPTCHA (Non-existent Session)",
            "POST",
            f"captcha/{fake_session_id}/solve",
            404,
            data={"solution": "test123"}
        )
        
        # If we have a real session, test with it
        if self.session_id:
            # Test getting CAPTCHA image for real session (might not have CAPTCHA)
            success3, response3 = self.run_test(
                "Get CAPTCHA Image (Real Session)",
                "GET",
                f"captcha/{self.session_id}",
                404,  # Expected 404 if no CAPTCHA image exists
                timeout=10
            )
            
            # Test solving CAPTCHA for session not waiting for CAPTCHA
            success4, response4 = self.run_test(
                "Solve CAPTCHA (Session Not Waiting)",
                "POST",
                f"captcha/{self.session_id}/solve",
                400,  # Expected 400 if session is not waiting for CAPTCHA
                data={"solution": "test123"}
            )
            
            return success1 and success2 and success3 and success4
        
        return success1 and success2

    def test_session_status_monitoring(self):
        """Test session status monitoring for CAPTCHA detection"""
        if not self.session_id:
            print("❌ No session ID available for status monitoring")
            return False
            
        print(f"\n👁️ Monitoring session {self.session_id} for status changes...")
        
        # Check session status multiple times
        for i in range(3):
            success, response = self.run_test(
                f"Session Status Check #{i+1}",
                "GET",
                f"scraping-sessions/{self.session_id}",
                200
            )
            
            if success:
                status = response.get('status', 'unknown')
                print(f"   Current Status: {status}")
                
                # Check for CAPTCHA-related fields
                if 'captcha_image_path' in response:
                    print(f"   CAPTCHA Image Path: {response['captcha_image_path']}")
                if 'current_url' in response:
                    print(f"   Current URL: {response['current_url']}")
                    
                # If waiting for CAPTCHA, try to get the image
                if status == 'waiting_captcha':
                    print("   🔐 Session is waiting for CAPTCHA!")
                    captcha_success, captcha_response = self.run_test(
                        "Get CAPTCHA Image (Waiting Session)",
                        "GET",
                        f"captcha/{self.session_id}",
                        200
                    )
                    if captcha_success:
                        print("   ✅ CAPTCHA image retrieved successfully")
                    break
                    
            time.sleep(2)  # Wait 2 seconds between checks
            
        return True

    def wait_for_session_completion(self, max_wait_time=60):
        """Wait for scraping session to complete or timeout"""
        if not self.session_id:
            return False
            
        print(f"\n⏳ Waiting for session {self.session_id} to complete (max {max_wait_time}s)...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                url = f"{self.api_url}/scraping-sessions/{self.session_id}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    session_data = response.json()
                    status = session_data.get('status', 'unknown')
                    print(f"   Status: {status}")
                    
                    if status in ['completed', 'failed']:
                        if status == 'completed':
                            print(f"✅ Session completed with {session_data.get('total_properties', 0)} properties")
                            return True
                        else:
                            print(f"❌ Session failed: {session_data.get('error_message', 'Unknown error')}")
                            return False
                            
                time.sleep(5)  # Wait 5 seconds before checking again
            except Exception as e:
                print(f"   Error checking session: {e}")
                time.sleep(5)
        
        print(f"⏰ Session did not complete within {max_wait_time} seconds")
        return False

def main():
    print("🚀 Starting Idealista Scraper API Tests with CAPTCHA Support")
    print("=" * 60)
    
    tester = IdealistaScraperAPITester()
    
    # Test basic endpoints first
    print("\n📋 Testing Basic API Endpoints...")
    tester.test_get_scraping_sessions()
    tester.test_get_properties()
    tester.test_get_region_stats()
    tester.test_export_php()
    
    # Test CAPTCHA endpoints
    print("\n🔐 Testing CAPTCHA Endpoints...")
    tester.test_captcha_endpoints()
    
    # Test scraping functionality
    print("\n🕷️ Testing Scraping Functionality...")
    if tester.test_start_scraping():
        # Wait a bit for the session to start
        time.sleep(3)
        tester.test_get_specific_session()
        
        # Monitor session for CAPTCHA detection
        tester.test_session_status_monitoring()
        
        # Wait for session to complete (with shorter timeout for testing)
        tester.wait_for_session_completion(max_wait_time=30)
        
        # Test data retrieval after scraping
        print("\n📊 Testing Data After Scraping...")
        tester.test_get_properties()
        tester.test_get_region_stats()
        tester.test_export_php()
    
    # Test data management
    print("\n🗑️ Testing Data Management...")
    tester.test_clear_properties()
    
    # Final results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())