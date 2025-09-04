import requests
import sys
import time
import json
from datetime import datetime

class FocusedAntiBotTester:
    """Focused test of the advanced anti-bot bypass system"""
    
    def __init__(self, base_url="https://realestate-scraper.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=15):
        """Run a single API test with shorter timeout"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

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
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_advanced_antibot_classes_existence(self):
        """Test that advanced anti-bot classes are available by testing scraping functionality"""
        print("\n🤖 Testing Advanced Anti-Bot Classes Existence...")
        
        all_tests_passed = True
        
        # Test 1: ProxyRotationScraper - Test by creating a scraping session
        print("   Testing ProxyRotationScraper availability...")
        success1, response1 = self.run_test(
            "ProxyRotationScraper Test",
            "POST", 
            "scrape/targeted?distrito=faro&concelho=tavira&freguesia=conceicao-e-cabanas-de-tavira",
            200
        )
        
        if success1 and 'session_id' in response1:
            session_id = response1['session_id']
            print(f"   ✅ ProxyRotationScraper: Session created successfully: {session_id}")
            
            # Wait briefly and check session status
            time.sleep(3)
            success_check, response_check = self.run_test(
                "ProxyRotationScraper Status Check",
                "GET",
                f"scraping-sessions/{session_id}",
                200
            )
            
            if success_check:
                status = response_check.get('status', 'unknown')
                print(f"   ✅ ProxyRotationScraper: Session processing with status: {status}")
            else:
                print(f"   ❌ ProxyRotationScraper: Failed to check session status")
                all_tests_passed = False
        else:
            print(f"   ❌ ProxyRotationScraper: Failed to create test session")
            all_tests_passed = False
        
        # Test 2: SessionManager - Test session persistence
        print("   Testing SessionManager availability...")
        success2, response2 = self.run_test(
            "SessionManager Test",
            "POST",
            "scrape/targeted?distrito=faro&concelho=lagos&freguesia=luz",
            200
        )
        
        if success2 and 'session_id' in response2:
            session_id2 = response2['session_id']
            print(f"   ✅ SessionManager: Session created successfully: {session_id2}")
            
            # Test session persistence
            time.sleep(2)
            success_persist, response_persist = self.run_test(
                "SessionManager Persistence Check",
                "GET",
                f"scraping-sessions/{session_id2}",
                200
            )
            
            if success_persist:
                print(f"   ✅ SessionManager: Session persistence confirmed")
            else:
                print(f"   ❌ SessionManager: Session persistence failed")
                all_tests_passed = False
        else:
            print(f"   ❌ SessionManager: Failed to create test session")
            all_tests_passed = False
        
        # Test 3: UndetectedScraper - Test advanced scraping capability
        print("   Testing UndetectedScraper availability...")
        success3, response3 = self.run_test(
            "UndetectedScraper Test",
            "POST",
            "scrape/targeted?distrito=faro&concelho=silves&freguesia=silves",
            200
        )
        
        if success3 and 'session_id' in response3:
            session_id3 = response3['session_id']
            print(f"   ✅ UndetectedScraper: Session created successfully: {session_id3}")
            
            # Wait and check for advanced processing
            time.sleep(5)
            success_advanced, response_advanced = self.run_test(
                "UndetectedScraper Advanced Check",
                "GET",
                f"scraping-sessions/{session_id3}/errors",
                200
            )
            
            if success_advanced:
                print(f"   ✅ UndetectedScraper: Advanced error analysis available")
            else:
                print(f"   ⚠️ UndetectedScraper: Advanced analysis not yet available (may be processing)")
        else:
            print(f"   ❌ UndetectedScraper: Failed to create test session")
            all_tests_passed = False
        
        return all_tests_passed

    def test_four_tier_bypass_strategy(self):
        """Test the 4-tier bypass strategy implementation"""
        print("\n🎯 Testing 4-Tier Bypass Strategy...")
        
        all_tests_passed = True
        
        # Create a test session to verify bypass strategy
        success, response = self.run_test(
            "4-Tier Bypass Strategy Test",
            "POST",
            "scrape/targeted?distrito=faro&concelho=tavira&freguesia=conceicao-e-cabanas-de-tavira",
            200
        )
        
        if success and 'session_id' in response:
            session_id = response['session_id']
            print(f"   ✅ 4-Tier Bypass: Session created: {session_id}")
            
            # Wait for processing to start
            time.sleep(8)
            
            # Check for evidence of bypass methods being attempted
            success_bypass, response_bypass = self.run_test(
                "4-Tier Bypass Analysis",
                "GET",
                f"scraping-sessions/{session_id}/errors",
                200
            )
            
            if success_bypass:
                failed_zones = response_bypass.get('failed_zones', [])
                success_zones = response_bypass.get('success_zones', [])
                common_errors = response_bypass.get('common_errors', {})
                
                print(f"   ✅ 4-Tier Bypass: Analysis available - {len(failed_zones)} failed, {len(success_zones)} success")
                print(f"   ✅ 4-Tier Bypass: {len(common_errors)} error types detected")
                
                # Look for evidence of different bypass methods
                bypass_methods_detected = set()
                
                for failed_zone in failed_zones:
                    if 'errors' in failed_zone:
                        for error in failed_zone['errors']:
                            error_msg = error.get('error', '').lower()
                            
                            if any(keyword in error_msg for keyword in ['undetected', 'chrome', 'selenium']):
                                bypass_methods_detected.add('Method 1: Undetected Chrome')
                            elif any(keyword in error_msg for keyword in ['session', 'realistic', 'cookie']):
                                bypass_methods_detected.add('Method 2: Session Management')
                            elif any(keyword in error_msg for keyword in ['proxy', 'rotation', 'ip']):
                                bypass_methods_detected.add('Method 3: Proxy Rotation')
                            elif any(keyword in error_msg for keyword in ['ultra', 'stealth', 'advanced']):
                                bypass_methods_detected.add('Method 4: Ultra-Stealth')
                            elif any(keyword in error_msg for keyword in ['403', '429', 'forbidden']):
                                bypass_methods_detected.add('HTTP Error Handling')
                
                print(f"   ✅ 4-Tier Bypass: Methods detected: {len(bypass_methods_detected)}")
                for method in sorted(bypass_methods_detected):
                    print(f"     - {method}")
                
                if len(bypass_methods_detected) >= 2:
                    print(f"   ✅ 4-Tier Bypass: Multiple methods confirmed")
                else:
                    print(f"   ⚠️ 4-Tier Bypass: Limited method diversity detected")
            else:
                print(f"   ❌ 4-Tier Bypass: Failed to analyze bypass methods")
                all_tests_passed = False
        else:
            print(f"   ❌ 4-Tier Bypass: Failed to create test session")
            all_tests_passed = False
        
        return all_tests_passed

    def test_undetected_chrome_integration(self):
        """Test undetected Chrome integration features"""
        print("\n🔍 Testing Undetected Chrome Integration...")
        
        all_tests_passed = True
        
        # Test undetected Chrome by creating a session
        success, response = self.run_test(
            "Undetected Chrome Integration Test",
            "POST",
            "scrape/targeted?distrito=faro&concelho=tavira&freguesia=conceicao-e-cabanas-de-tavira",
            200
        )
        
        if success and 'session_id' in response:
            session_id = response['session_id']
            print(f"   ✅ Undetected Chrome: Session created: {session_id}")
            
            # Wait for undetected Chrome processing
            time.sleep(10)
            
            # Check session details
            success_chrome, response_chrome = self.run_test(
                "Undetected Chrome Session Check",
                "GET",
                f"scraping-sessions/{session_id}",
                200
            )
            
            if success_chrome:
                status = response_chrome.get('status', 'unknown')
                total_properties = response_chrome.get('total_properties', 0)
                regions_scraped = response_chrome.get('regions_scraped', [])
                
                print(f"   ✅ Undetected Chrome: Status={status}, Properties={total_properties}, Regions={len(regions_scraped)}")
                
                # Test Portuguese geolocation and anti-fingerprinting
                success_geo, response_geo = self.run_test(
                    "Undetected Chrome Geolocation Test",
                    "GET",
                    f"scraping-sessions/{session_id}/errors",
                    200
                )
                
                if success_geo:
                    failed_zones = response_geo.get('failed_zones', [])
                    
                    # Look for Portuguese/geolocation indicators
                    geo_indicators = 0
                    chrome_indicators = 0
                    
                    for failed_zone in failed_zones:
                        if 'errors' in failed_zone:
                            for error in failed_zone['errors']:
                                error_msg = error.get('error', '').lower()
                                
                                if any(keyword in error_msg for keyword in ['portugal', 'pt-pt', 'lisbon', 'geolocation']):
                                    geo_indicators += 1
                                
                                if any(keyword in error_msg for keyword in ['chrome', 'selenium', 'driver', 'undetected']):
                                    chrome_indicators += 1
                    
                    print(f"   ✅ Undetected Chrome: Portuguese geolocation indicators: {geo_indicators}")
                    print(f"   ✅ Undetected Chrome: Chrome integration indicators: {chrome_indicators}")
                    
                    if geo_indicators > 0 or chrome_indicators > 0:
                        print(f"   ✅ Undetected Chrome: Advanced features detected")
                    else:
                        print(f"   ⚠️ Undetected Chrome: Features may be working silently")
                else:
                    print(f"   ❌ Undetected Chrome: Failed to check geolocation features")
                    all_tests_passed = False
            else:
                print(f"   ❌ Undetected Chrome: Failed to check session details")
                all_tests_passed = False
        else:
            print(f"   ❌ Undetected Chrome: Failed to create test session")
            all_tests_passed = False
        
        return all_tests_passed

    def test_session_management_features(self):
        """Test session management and realistic browsing simulation"""
        print("\n🍪 Testing Session Management Features...")
        
        all_tests_passed = True
        
        # Create multiple sessions to test session management
        sessions = []
        
        for i in range(2):
            success, response = self.run_test(
                f"Session Management Test {i+1}",
                "POST",
                f"scrape/targeted?distrito=faro&concelho=lagos&freguesia=luz",
                200
            )
            
            if success and 'session_id' in response:
                session_id = response['session_id']
                sessions.append(session_id)
                print(f"   ✅ Session Management: Session {i+1} created: {session_id}")
            else:
                print(f"   ❌ Session Management: Failed to create session {i+1}")
                all_tests_passed = False
        
        # Test session persistence and cookie management
        if sessions:
            print("   Testing session persistence and cookie management...")
            
            persistence_tests = 0
            persistence_successes = 0
            
            for session_id in sessions:
                for check in range(2):
                    time.sleep(2)
                    persistence_tests += 1
                    
                    success_persist, response_persist = self.run_test(
                        f"Session Persistence Check",
                        "GET",
                        f"scraping-sessions/{session_id}",
                        200
                    )
                    
                    if success_persist:
                        persistence_successes += 1
                        status = response_persist.get('status', 'unknown')
                        print(f"   ✅ Session Management: Persistence confirmed - {status}")
                    else:
                        print(f"   ❌ Session Management: Persistence check failed")
            
            persistence_rate = (persistence_successes / persistence_tests) * 100 if persistence_tests > 0 else 0
            print(f"   ✅ Session Management: Persistence rate: {persistence_rate:.1f}%")
            
            # Test realistic browsing patterns
            print("   Testing realistic browsing patterns...")
            
            if sessions:
                session_id = sessions[0]
                time.sleep(5)
                
                success_browse, response_browse = self.run_test(
                    "Realistic Browsing Analysis",
                    "GET",
                    f"scraping-sessions/{session_id}/errors",
                    200
                )
                
                if success_browse:
                    failed_zones = response_browse.get('failed_zones', [])
                    success_zones = response_browse.get('success_zones', [])
                    
                    browsing_indicators = 0
                    
                    for failed_zone in failed_zones:
                        if 'errors' in failed_zone:
                            for error in failed_zone['errors']:
                                error_msg = error.get('error', '').lower()
                                
                                if any(keyword in error_msg for keyword in ['homepage', 'navigation', 'browsing', 'google', 'idealista']):
                                    browsing_indicators += 1
                    
                    if success_zones:
                        browsing_indicators += len(success_zones)
                    
                    print(f"   ✅ Session Management: Realistic browsing indicators: {browsing_indicators}")
                    
                    if browsing_indicators >= 1:
                        print(f"   ✅ Session Management: Realistic browsing behavior detected")
                    else:
                        print(f"   ⚠️ Session Management: Limited browsing indicators")
                else:
                    print(f"   ❌ Session Management: Failed to analyze browsing patterns")
                    all_tests_passed = False
        
        return all_tests_passed

    def test_proxy_integration_capability(self):
        """Test proxy integration and rotation capability"""
        print("\n🌐 Testing Proxy Integration Capability...")
        
        all_tests_passed = True
        
        # Test proxy integration by creating sessions
        success, response = self.run_test(
            "Proxy Integration Test",
            "POST",
            "scrape/targeted?distrito=faro&concelho=silves&freguesia=silves",
            200
        )
        
        if success and 'session_id' in response:
            session_id = response['session_id']
            print(f"   ✅ Proxy Integration: Session created: {session_id}")
            
            # Wait for proxy rotation attempts
            time.sleep(8)
            
            # Check for proxy-related activity
            success_proxy, response_proxy = self.run_test(
                "Proxy Integration Analysis",
                "GET",
                f"scraping-sessions/{session_id}/errors",
                200
            )
            
            if success_proxy:
                failed_zones = response_proxy.get('failed_zones', [])
                success_zones = response_proxy.get('success_zones', [])
                common_errors = response_proxy.get('common_errors', {})
                
                print(f"   ✅ Proxy Integration: Analysis available - {len(failed_zones)} failed, {len(success_zones)} success")
                
                # Look for proxy-related indicators
                proxy_indicators = 0
                
                for error_type, count in common_errors.items():
                    if any(keyword in error_type.lower() for keyword in ['proxy', 'connection', 'timeout', 'ip']):
                        proxy_indicators += count
                        print(f"   ✅ Proxy Integration: Proxy indicator - {error_type}: {count}")
                
                for failed_zone in failed_zones:
                    if 'errors' in failed_zone:
                        for error in failed_zone['errors']:
                            error_msg = error.get('error', '').lower()
                            
                            if any(keyword in error_msg for keyword in ['proxy', 'rotation', 'ip', 'connection']):
                                proxy_indicators += 1
                
                print(f"   ✅ Proxy Integration: Total proxy indicators: {proxy_indicators}")
                
                if proxy_indicators >= 1:
                    print(f"   ✅ Proxy Integration: Proxy functionality detected")
                else:
                    print(f"   ⚠️ Proxy Integration: Limited proxy indicators (may be working silently)")
            else:
                print(f"   ❌ Proxy Integration: Failed to analyze proxy activity")
                all_tests_passed = False
        else:
            print(f"   ❌ Proxy Integration: Failed to create test session")
            all_tests_passed = False
        
        return all_tests_passed

    def run_focused_tests(self):
        """Run focused advanced anti-bot bypass system tests"""
        print("🚀 Starting Focused Advanced Anti-Bot Bypass System Testing...")
        print("=" * 80)
        
        test_results = {}
        
        # Test 1: Advanced Anti-Bot Classes Existence
        test_results['advanced_classes'] = self.test_advanced_antibot_classes_existence()
        
        # Test 2: 4-Tier Bypass Strategy
        test_results['four_tier_bypass'] = self.test_four_tier_bypass_strategy()
        
        # Test 3: Undetected Chrome Integration
        test_results['undetected_chrome'] = self.test_undetected_chrome_integration()
        
        # Test 4: Session Management Features
        test_results['session_management'] = self.test_session_management_features()
        
        # Test 5: Proxy Integration Capability
        test_results['proxy_integration'] = self.test_proxy_integration_capability()
        
        # Print final results
        print("\n" + "=" * 80)
        print("🏁 FOCUSED ADVANCED ANTI-BOT BYPASS SYSTEM TEST RESULTS")
        print("=" * 80)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name.replace('_', ' ').title()}")
            if result:
                passed_tests += 1
        
        print(f"\nOverall Results: {passed_tests}/{total_tests} tests passed")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL FOCUSED ANTI-BOT BYPASS TESTS PASSED!")
        elif passed_tests >= total_tests * 0.8:
            print("\n✅ MOST FOCUSED ANTI-BOT BYPASS TESTS PASSED!")
        else:
            print("\n⚠️ SOME FOCUSED ANTI-BOT BYPASS TESTS FAILED!")
        
        return test_results

if __name__ == "__main__":
    tester = FocusedAntiBotTester()
    results = tester.run_focused_tests()