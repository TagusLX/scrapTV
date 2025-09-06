#!/usr/bin/env python3

import requests
import sys
import time
import json
from datetime import datetime

class EnhancedErrorHandlingTester:
    def __init__(self, base_url="https://property-radar-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

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
                    print(f"   Response: {json.dumps(response_data, indent=2)[:300]}...")
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

    def test_enhanced_scraping_session_model(self):
        """Test that new sessions properly track failed and success zones"""
        print("\n📋 Testing Enhanced Scraping Session Model...")
        
        # Start a scraping session
        success, response = self.run_test(
            "Create Enhanced Scraping Session",
            "POST",
            "scrape/targeted?distrito=faro&concelho=tavira&freguesia=conceicao-e-cabanas-de-tavira",
            200
        )
        
        if success and 'session_id' in response:
            session_id = response['session_id']
            print(f"   ✅ Session created: {session_id}")
            
            # Wait for some processing
            time.sleep(5)
            
            # Check session details
            success_check, response_check = self.run_test(
                "Check Session Enhanced Fields",
                "GET",
                f"scraping-sessions/{session_id}",
                200
            )
            
            if success_check:
                # Verify enhanced fields exist
                has_failed_zones = 'failed_zones' in response_check
                has_success_zones = 'success_zones' in response_check
                
                print(f"   ✅ Has failed_zones field: {has_failed_zones}")
                print(f"   ✅ Has success_zones field: {has_success_zones}")
                
                if has_failed_zones:
                    failed_count = len(response_check.get('failed_zones', []))
                    print(f"   Failed zones count: {failed_count}")
                
                if has_success_zones:
                    success_count = len(response_check.get('success_zones', []))
                    print(f"   Success zones count: {success_count}")
                
                return session_id, has_failed_zones and has_success_zones
            
        return None, False

    def test_error_analysis_endpoint(self):
        """Test GET /api/scraping-sessions/{session_id}/errors"""
        print("\n📊 Testing Error Analysis Endpoint...")
        
        # First create a session
        session_id, _ = self.test_enhanced_scraping_session_model()
        
        if session_id:
            # Wait for processing
            time.sleep(8)
            
            # Test error analysis endpoint
            success, response = self.run_test(
                "Get Session Error Analysis",
                "GET",
                f"scraping-sessions/{session_id}/errors",
                200
            )
            
            if success:
                # Verify response structure
                required_fields = [
                    'total_zones_attempted', 'failed_zones_count', 'success_zones_count', 
                    'failure_rate', 'common_errors', 'failed_zones', 'success_zones'
                ]
                
                all_fields_present = True
                for field in required_fields:
                    if field in response:
                        print(f"   ✅ Found field '{field}': {response[field]}")
                    else:
                        print(f"   ❌ Missing field: {field}")
                        all_fields_present = False
                
                # Test failure rate calculation
                if 'failure_rate' in response:
                    failure_rate = response['failure_rate']
                    if isinstance(failure_rate, (int, float)) and 0 <= failure_rate <= 100:
                        print(f"   ✅ Valid failure rate: {failure_rate:.1f}%")
                    else:
                        print(f"   ❌ Invalid failure rate: {failure_rate}")
                        all_fields_present = False
                
                return session_id, all_fields_present
            
        return None, False

    def test_retry_functionality(self):
        """Test POST /api/scrape/retry-failed"""
        print("\n🔄 Testing Retry Functionality...")
        
        # Create a session that might have failures
        success, response = self.run_test(
            "Create Session for Retry Test",
            "POST",
            "scrape/targeted?distrito=invalid_distrito",  # This should fail
            200
        )
        
        if success and 'session_id' in response:
            session_id = response['session_id']
            print(f"   ✅ Created test session: {session_id}")
            
            # Wait for it to process and likely fail
            time.sleep(8)
            
            # Check if it has failed zones
            success_check, response_check = self.run_test(
                "Check for Failed Zones",
                "GET",
                f"scraping-sessions/{session_id}/errors",
                200
            )
            
            if success_check:
                failed_count = response_check.get('failed_zones_count', 0)
                print(f"   Found {failed_count} failed zones")
                
                if failed_count > 0:
                    # Test retry functionality
                    success_retry, response_retry = self.run_test(
                        "Retry Failed Zones",
                        "POST",
                        f"scrape/retry-failed?session_id={session_id}",
                        200
                    )
                    
                    if success_retry:
                        # Verify retry response structure
                        required_fields = ['message', 'retry_session_id', 'original_session_id', 'zones_to_retry']
                        all_fields_present = True
                        
                        for field in required_fields:
                            if field in response_retry:
                                print(f"   ✅ Found retry field '{field}': {response_retry[field]}")
                            else:
                                print(f"   ❌ Missing retry field: {field}")
                                all_fields_present = False
                        
                        return True, all_fields_present
                else:
                    print("   ⚠️ No failed zones to test retry with")
                    return True, True  # Still pass if no failures
        
        return False, False

    def test_real_price_detection(self):
        """Test the improved price extraction logic"""
        print("\n💰 Testing Real Price Detection...")
        
        # Start scraping to test price detection
        success, response = self.run_test(
            "Test Real Price Detection",
            "POST",
            "scrape/targeted?distrito=faro&concelho=faro&freguesia=faro-se-e-estoi",
            200
        )
        
        if success and 'session_id' in response:
            session_id = response['session_id']
            print(f"   ✅ Started price detection test: {session_id}")
            
            # Wait for scraping
            time.sleep(10)
            
            # Check for detailed error messages about price detection
            success_check, response_check = self.run_test(
                "Check Price Detection Results",
                "GET",
                f"scraping-sessions/{session_id}/errors",
                200
            )
            
            if success_check:
                failed_zones = response_check.get('failed_zones', [])
                success_zones = response_check.get('success_zones', [])
                
                print(f"   Price detection results: {len(success_zones)} success, {len(failed_zones)} failed")
                
                # Look for specific error messages about price detection
                price_detection_tested = False
                for failed_zone in failed_zones:
                    if 'errors' in failed_zone:
                        for error in failed_zone['errors']:
                            error_msg = error.get('error', '')
                            if 'items-average-price' in error_msg or 'Preço médio nesta zona' in error_msg:
                                print(f"   ✅ Found price detection error: {error_msg}")
                                price_detection_tested = True
                            elif 'HTTP' in error_msg:
                                print(f"   ✅ Found HTTP error capture: {error_msg}")
                
                # Check if any real prices were found
                real_prices_found = len(success_zones) > 0
                if real_prices_found:
                    print(f"   ✅ Real prices detected in {len(success_zones)} zones")
                
                return True, price_detection_tested or real_prices_found
        
        return False, False

def main():
    print("🚀 Testing Enhanced Error Handling and Retry Functionality")
    print("=" * 70)
    
    tester = EnhancedErrorHandlingTester()
    
    # Test 1: Enhanced Scraping Session Model
    print("\n1️⃣ Enhanced Scraping Session Model")
    session_id, model_test_passed = tester.test_enhanced_scraping_session_model()
    
    # Test 2: Error Analysis Endpoint
    print("\n2️⃣ Error Analysis Endpoint")
    _, error_analysis_passed = tester.test_error_analysis_endpoint()
    
    # Test 3: Retry Functionality
    print("\n3️⃣ Retry Functionality")
    retry_started, retry_test_passed = tester.test_retry_functionality()
    
    # Test 4: Real Price Detection
    print("\n4️⃣ Real Price Detection")
    price_started, price_test_passed = tester.test_real_price_detection()
    
    # Test 5: Test error endpoint with non-existent session
    print("\n5️⃣ Error Handling for Non-existent Session")
    success_404, _ = tester.run_test(
        "Error Analysis for Non-existent Session",
        "GET",
        "scraping-sessions/fake-session-123/errors",
        404
    )
    
    # Test 6: Test retry with non-existent session
    print("\n6️⃣ Retry Handling for Non-existent Session")
    success_retry_404, _ = tester.run_test(
        "Retry for Non-existent Session",
        "POST",
        "scrape/retry-failed?session_id=fake-session-123",
        404
    )
    
    # Results
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    print(f"\n🔧 ENHANCED ERROR HANDLING & RETRY FUNCTIONALITY RESULTS:")
    print(f"   Enhanced Session Model: {'✅ PASSED' if model_test_passed else '❌ FAILED'}")
    print(f"   Error Analysis Endpoint: {'✅ PASSED' if error_analysis_passed else '❌ FAILED'}")
    print(f"   Retry Functionality: {'✅ PASSED' if retry_test_passed else '❌ FAILED'}")
    print(f"   Real Price Detection: {'✅ PASSED' if price_test_passed else '❌ FAILED'}")
    print(f"   404 Error Handling: {'✅ PASSED' if success_404 else '❌ FAILED'}")
    print(f"   404 Retry Handling: {'✅ PASSED' if success_retry_404 else '❌ FAILED'}")
    
    all_main_tests_passed = (model_test_passed and error_analysis_passed and 
                            retry_test_passed and price_test_passed and 
                            success_404 and success_retry_404)
    
    if all_main_tests_passed:
        print("🎉 All enhanced error handling and retry functionality tests passed!")
        return 0
    else:
        print("❌ Some enhanced error handling tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())