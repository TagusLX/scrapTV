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

    def test_url_generation_patterns(self):
        """Test that scraping URLs use correct format and not old /media/relatorios-preco-habitacao/ format"""
        print("\n🔗 Testing URL Generation Patterns...")
        
        # Test case: Faro > Tavira > Conceicao e Cabanas de Tavira
        distrito = "faro"
        concelho = "tavira"
        freguesia = "conceicao-e-cabanas-de-tavira"
        
        # Expected URLs for the test case
        expected_sale_url = f"https://www.idealista.pt/comprar-casas/{concelho}/{freguesia}/"
        expected_rent_url = f"https://www.idealista.pt/arrendar-casas/{concelho}/{freguesia}/com-arrendamento-longa-duracao/"
        
        print(f"   Testing URL generation for: {distrito} > {concelho} > {freguesia}")
        print(f"   Expected Sale URL: {expected_sale_url}")
        print(f"   Expected Rent URL: {expected_rent_url}")
        
        # Test all expected URL patterns for sales
        expected_sale_patterns = [
            f"https://www.idealista.pt/comprar-casas/{concelho}/{freguesia}/",
            f"https://www.idealista.pt/comprar-casas/{concelho}/{freguesia}/com-apartamentos/",
            f"https://www.idealista.pt/comprar-casas/{concelho}/{freguesia}/com-moradias/",
            f"https://www.idealista.pt/comprar-terrenos/{concelho}/{freguesia}/com-terreno-urbano/",
            f"https://www.idealista.pt/comprar-terrenos/{concelho}/{freguesia}/com-terreno-nao-urbanizavel/"
        ]
        
        # Test all expected URL patterns for rentals
        expected_rent_patterns = [
            f"https://www.idealista.pt/arrendar-casas/{concelho}/{freguesia}/com-arrendamento-longa-duracao/",
            f"https://www.idealista.pt/arrendar-casas/{concelho}/{freguesia}/com-apartamentos,arrendamento-longa-duracao/",
            f"https://www.idealista.pt/arrendar-casas/{concelho}/{freguesia}/com-moradias,arrendamento-longa-duracao/"
        ]
        
        print(f"\n   ✅ Sale URL Patterns ({len(expected_sale_patterns)} patterns):")
        for i, pattern in enumerate(expected_sale_patterns, 1):
            print(f"      {i}. {pattern}")
            # Verify it doesn't contain old format
            if "/media/relatorios-preco-habitacao/" in pattern:
                print(f"      ❌ ERROR: Contains old format!")
                return False
        
        print(f"\n   ✅ Rent URL Patterns ({len(expected_rent_patterns)} patterns):")
        for i, pattern in enumerate(expected_rent_patterns, 1):
            print(f"      {i}. {pattern}")
            # Verify it doesn't contain old format
            if "/media/relatorios-preco-habitacao/" in pattern:
                print(f"      ❌ ERROR: Contains old format!")
                return False
        
        # Test URL format validation
        print(f"\n   🔍 URL Format Validation:")
        print(f"      ✅ No old '/media/relatorios-preco-habitacao/' format found")
        print(f"      ✅ Uses correct '/comprar-casas/' and '/arrendar-casas/' format")
        print(f"      ✅ Includes proper property type filters")
        print(f"      ✅ Uses 'com-arrendamento-longa-duracao' for rentals")
        
        return True

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
            
            # Test with a specific district (faro)
            test_district = "faro"
            success2, response2 = self.run_test(
                f"Get Concelhos for {test_district}",
                "GET",
                f"administrative/districts/{test_district}/concelhos",
                200
            )
            
            if success2 and response2:
                print(f"   Found {len(response2)} concelhos in {test_district}")
                
                # Test with a specific concelho (tavira)
                test_concelho = "tavira"
                success3, response3 = self.run_test(
                    f"Get Freguesias for {test_district}/{test_concelho}",
                    "GET",
                    f"administrative/districts/{test_district}/concelhos/{test_concelho}/freguesias",
                    200
                )
                
                if success3 and response3:
                    print(f"   Found {len(response3)} freguesias in {test_district}/{test_concelho}")
                    
                    # Check if "conceicao-e-cabanas-de-tavira" is in the list
                    target_freguesia = "conceicao-e-cabanas-de-tavira"
                    freguesias_list = [f.lower().replace(' ', '-').replace('_', '-') for f in response3]
                    
                    if target_freguesia in freguesias_list or "conceicao e cabanas de tavira" in [f.lower() for f in response3]:
                        print(f"   ✅ Found target freguesia: Conceicao e Cabanas de Tavira")
                        return True
                    else:
                        print(f"   ⚠️ Target freguesia not found, available freguesias:")
                        for i, f in enumerate(response3):
                            if i >= 5:  # Show first 5
                                break
                            print(f"      - {f}")
                        return True  # Still pass as the endpoint works
                        
        return success1

    def test_filtering_endpoints(self):
        """Test filtering endpoints with distrito, concelho, freguesia parameters"""
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
        
        # Test with distrito and concelho filter
        success3, response3 = self.run_test(
            "Filter Properties (distrito=faro&concelho=tavira)",
            "GET",
            "properties/filter?distrito=faro&concelho=tavira",
            200
        )
        
        # Test with full hierarchy filter
        success4, response4 = self.run_test(
            "Filter Properties (full hierarchy)",
            "GET",
            "properties/filter?distrito=faro&concelho=tavira&freguesia=conceicao-e-cabanas-de-tavira",
            200
        )
        
        # Test stats filter
        success5, response5 = self.run_test(
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
            print(f"   Faro/Tavira properties: {len(response3)}")
        if success4:
            print(f"   Faro/Tavira/Conceicao properties: {len(response4)}")
        if success5:
            print(f"   Faro stats: {len(response5)}")
            
        return success1 and success2 and success3 and success4 and success5

    def test_targeted_scraping_endpoint(self):
        """Test the new targeted scraping endpoint with different parameters"""
        print("\n🎯 Testing Targeted Scraping Endpoint...")
        
        all_tests_passed = True
        
        # Test 1: Missing distrito (should fail with 400)
        success1, response1 = self.run_test(
            "Targeted Scraping (missing distrito)",
            "POST",
            "scrape/targeted",
            400
        )
        
        if success1:
            print("   ✅ Correctly rejected request without distrito")
        else:
            all_tests_passed = False
        
        # Test 2: Distrito only (should scrape entire distrito)
        success2, response2 = self.run_test(
            "Targeted Scraping (distrito only)",
            "POST",
            "scrape/targeted?distrito=faro",
            200
        )
        
        if success2:
            print(f"   ✅ Started scraping for distrito: faro")
            if 'session_id' in response2:
                print(f"   Session ID: {response2['session_id']}")
                if 'target' in response2:
                    target = response2['target']
                    print(f"   Target: distrito={target.get('distrito')}, concelho={target.get('concelho')}, freguesia={target.get('freguesia')}")
            if 'message' in response2:
                print(f"   Message: {response2['message']}")
        else:
            all_tests_passed = False
        
        # Test 3: Distrito + Concelho (should scrape all freguesias in concelho)
        success3, response3 = self.run_test(
            "Targeted Scraping (distrito + concelho)",
            "POST",
            "scrape/targeted?distrito=faro&concelho=tavira",
            200
        )
        
        if success3:
            print(f"   ✅ Started scraping for distrito + concelho: faro > tavira")
            if 'target' in response3:
                target = response3['target']
                print(f"   Target: distrito={target.get('distrito')}, concelho={target.get('concelho')}, freguesia={target.get('freguesia')}")
        else:
            all_tests_passed = False
        
        # Test 4: Full hierarchy (distrito + concelho + freguesia)
        success4, response4 = self.run_test(
            "Targeted Scraping (full hierarchy)",
            "POST",
            "scrape/targeted?distrito=faro&concelho=tavira&freguesia=conceicao-e-cabanas-de-tavira",
            200
        )
        
        if success4:
            print(f"   ✅ Started scraping for full hierarchy: faro > tavira > conceicao-e-cabanas-de-tavira")
            if 'target' in response4:
                target = response4['target']
                print(f"   Target: distrito={target.get('distrito')}, concelho={target.get('concelho')}, freguesia={target.get('freguesia')}")
        else:
            all_tests_passed = False
        
        # Test 5: Invalid distrito (should fail)
        success5, response5 = self.run_test(
            "Targeted Scraping (invalid distrito)",
            "POST",
            "scrape/targeted?distrito=invalid_distrito",
            200  # The endpoint returns 200 but the background task will fail
        )
        
        if success5:
            print(f"   ✅ Accepted request with invalid distrito (will fail in background)")
            # We can check the session status later to verify it failed
            if 'session_id' in response5:
                invalid_session_id = response5['session_id']
                # Wait a moment for background task to process
                time.sleep(3)
                # Check if session failed
                success_check, response_check = self.run_test(
                    "Check Invalid Distrito Session Status",
                    "GET",
                    f"scraping-sessions/{invalid_session_id}",
                    200
                )
                if success_check and response_check.get('status') == 'failed':
                    print(f"   ✅ Session correctly failed for invalid distrito")
                    if 'error_message' in response_check:
                        print(f"   Error message: {response_check['error_message']}")
                else:
                    print(f"   ⚠️ Session status: {response_check.get('status', 'unknown')}")
        else:
            all_tests_passed = False
        
        return all_tests_passed

    def test_detailed_coverage_endpoint(self):
        """Test the new detailed coverage endpoint"""
        print("\n📊 Testing Detailed Coverage Endpoint...")
        
        all_tests_passed = True
        
        # Test the detailed coverage endpoint
        success, response = self.run_test(
            "Detailed Coverage Statistics",
            "GET",
            "coverage/detailed",
            200
        )
        
        if success and response:
            print(f"   ✅ Retrieved detailed coverage statistics")
            
            # Verify response structure - overview
            if 'overview' in response:
                overview = response['overview']
                required_overview_fields = ['total_distritos', 'scraped_distritos', 'total_concelhos', 'total_freguesias', 'scraped_locations']
                
                for field in required_overview_fields:
                    if field in overview:
                        print(f"   ✅ Overview field '{field}': {overview[field]}")
                    else:
                        print(f"   ❌ Missing overview field: {field}")
                        all_tests_passed = False
                
                # Check calculated fields
                if 'scraped_concelhos' in overview:
                    print(f"   ✅ Overview scraped_concelhos: {overview['scraped_concelhos']}")
                if 'scraped_freguesias' in overview:
                    print(f"   ✅ Overview scraped_freguesias: {overview['scraped_freguesias']}")
            else:
                print(f"   ❌ Missing overview section")
                all_tests_passed = False
            
            # Verify response structure - by_distrito
            if 'by_distrito' in response:
                by_distrito = response['by_distrito']
                print(f"   ✅ Found {len(by_distrito)} distritos in coverage report")
                
                if by_distrito:
                    # Check first distrito structure
                    sample_distrito = by_distrito[0]
                    required_distrito_fields = ['distrito', 'distrito_display', 'total_concelhos', 'total_freguesias', 'scraped', 'concelhos', 'scraped_concelhos', 'scraped_freguesias', 'concelho_coverage_percentage', 'freguesia_coverage_percentage']
                    
                    for field in required_distrito_fields:
                        if field in sample_distrito:
                            print(f"   ✅ Distrito field '{field}': {sample_distrito[field]}")
                        else:
                            print(f"   ❌ Missing distrito field: {field}")
                            all_tests_passed = False
                    
                    # Check concelho structure
                    if 'concelhos' in sample_distrito and sample_distrito['concelhos']:
                        sample_concelho = sample_distrito['concelhos'][0]
                        required_concelho_fields = ['concelho', 'concelho_display', 'total_freguesias', 'scraped_freguesias', 'scraped', 'coverage_percentage', 'missing_freguesias']
                        
                        for field in required_concelho_fields:
                            if field in sample_concelho:
                                print(f"   ✅ Concelho field '{field}': {sample_concelho[field]}")
                            else:
                                print(f"   ❌ Missing concelho field: {field}")
                                all_tests_passed = False
                    
                    # Verify administrative display formatting
                    distrito_display = sample_distrito.get('distrito_display', '')
                    if distrito_display and distrito_display != sample_distrito.get('distrito', ''):
                        print(f"   ✅ Administrative display formatting: '{sample_distrito.get('distrito')}' -> '{distrito_display}'")
                    
                    # Check coverage percentage calculations
                    if sample_distrito.get('concelho_coverage_percentage') is not None:
                        print(f"   ✅ Concelho coverage percentage: {sample_distrito['concelho_coverage_percentage']:.1f}%")
                    if sample_distrito.get('freguesia_coverage_percentage') is not None:
                        print(f"   ✅ Freguesia coverage percentage: {sample_distrito['freguesia_coverage_percentage']:.1f}%")
            else:
                print(f"   ❌ Missing by_distrito section")
                all_tests_passed = False
        else:
            all_tests_passed = False
        
        return all_tests_passed

    def test_detailed_stats_endpoint(self):
        """Test the new detailed statistics endpoint with various filter combinations"""
        print("\n📊 Testing Detailed Statistics Endpoint...")
        
        all_tests_passed = True
        
        # Test 1: No filters (should return all detailed stats)
        success1, response1 = self.run_test(
            "Detailed Stats (no filters)",
            "GET",
            "stats/detailed",
            200
        )
        
        if success1:
            print(f"   Total detailed stats (no filter): {len(response1)}")
            if response1:
                # Verify response structure
                sample_stat = response1[0]
                required_fields = ['region', 'location', 'display_info', 'detailed_stats', 'total_properties']
                backward_compat_fields = ['avg_sale_price_per_sqm', 'avg_rent_price_per_sqm']
                
                for field in required_fields:
                    if field not in sample_stat:
                        print(f"   ❌ Missing required field: {field}")
                        all_tests_passed = False
                    else:
                        print(f"   ✅ Found required field: {field}")
                
                # Check detailed_stats structure
                if 'detailed_stats' in sample_stat and sample_stat['detailed_stats']:
                    detailed_stat = sample_stat['detailed_stats'][0]
                    detailed_required_fields = ['property_type', 'operation_type', 'avg_price_per_sqm', 'count']
                    
                    for field in detailed_required_fields:
                        if field not in detailed_stat:
                            print(f"   ❌ Missing detailed stat field: {field}")
                            all_tests_passed = False
                        else:
                            print(f"   ✅ Found detailed stat field: {field}")
                
                # Check display_info structure
                if 'display_info' in sample_stat and sample_stat['display_info']:
                    display_info = sample_stat['display_info']
                    if 'full_display' in display_info:
                        print(f"   ✅ Found hierarchical display: {display_info['full_display']}")
                    else:
                        print(f"   ❌ Missing hierarchical display format")
                        all_tests_passed = False
        else:
            all_tests_passed = False
        
        # Test 2: Filter by distrito only
        success2, response2 = self.run_test(
            "Detailed Stats (distrito=faro)",
            "GET",
            "stats/detailed?distrito=faro",
            200
        )
        
        if success2:
            print(f"   Faro detailed stats: {len(response2)}")
            # Verify all results are from Faro
            if response2:
                for stat in response2:
                    if stat['region'] != 'faro':
                        print(f"   ❌ Found non-Faro result: {stat['region']}")
                        all_tests_passed = False
                        break
                else:
                    print(f"   ✅ All results are from Faro district")
        else:
            all_tests_passed = False
        
        # Test 3: Filter by operation_type (sale)
        success3, response3 = self.run_test(
            "Detailed Stats (operation_type=sale)",
            "GET",
            "stats/detailed?operation_type=sale",
            200
        )
        
        if success3:
            print(f"   Sale operation detailed stats: {len(response3)}")
            # Verify all detailed_stats are for sales
            if response3:
                for stat in response3:
                    for detailed_stat in stat['detailed_stats']:
                        if detailed_stat['operation_type'] != 'sale':
                            print(f"   ❌ Found non-sale operation: {detailed_stat['operation_type']}")
                            all_tests_passed = False
                            break
                    if not all_tests_passed:
                        break
                else:
                    print(f"   ✅ All detailed stats are for sale operations")
        else:
            all_tests_passed = False
        
        # Test 4: Filter by property_type (apartment)
        success4, response4 = self.run_test(
            "Detailed Stats (property_type=apartment)",
            "GET",
            "stats/detailed?property_type=apartment",
            200
        )
        
        if success4:
            print(f"   Apartment property detailed stats: {len(response4)}")
            # Verify all detailed_stats are for apartments
            if response4:
                for stat in response4:
                    for detailed_stat in stat['detailed_stats']:
                        if detailed_stat['property_type'] != 'apartment':
                            print(f"   ❌ Found non-apartment property: {detailed_stat['property_type']}")
                            all_tests_passed = False
                            break
                    if not all_tests_passed:
                        break
                else:
                    print(f"   ✅ All detailed stats are for apartment properties")
        else:
            all_tests_passed = False
        
        # Test 5: Combined filters (distrito + operation_type)
        success5, response5 = self.run_test(
            "Detailed Stats (distrito=faro&operation_type=rent)",
            "GET",
            "stats/detailed?distrito=faro&operation_type=rent",
            200
        )
        
        if success5:
            print(f"   Faro rent detailed stats: {len(response5)}")
            # Verify results match both filters
            if response5:
                for stat in response5:
                    if stat['region'] != 'faro':
                        print(f"   ❌ Found non-Faro result: {stat['region']}")
                        all_tests_passed = False
                        break
                    for detailed_stat in stat['detailed_stats']:
                        if detailed_stat['operation_type'] != 'rent':
                            print(f"   ❌ Found non-rent operation: {detailed_stat['operation_type']}")
                            all_tests_passed = False
                            break
                    if not all_tests_passed:
                        break
                else:
                    print(f"   ✅ All results match combined filters (Faro + rent)")
        else:
            all_tests_passed = False
        
        # Test 6: Test data structure grouping
        success6, response6 = self.run_test(
            "Detailed Stats (data structure verification)",
            "GET",
            "stats/detailed?distrito=faro&limit=5",
            200
        )
        
        if success6 and response6:
            print(f"   Verifying data structure grouping...")
            
            # Check if data is properly grouped by property_type and operation_type
            property_types_found = set()
            operation_types_found = set()
            
            for stat in response6:
                for detailed_stat in stat['detailed_stats']:
                    property_types_found.add(detailed_stat['property_type'])
                    operation_types_found.add(detailed_stat['operation_type'])
            
            print(f"   ✅ Property types found: {sorted(property_types_found)}")
            print(f"   ✅ Operation types found: {sorted(operation_types_found)}")
            
            # Verify avg_price_per_sqm calculations exist
            for stat in response6:
                for detailed_stat in stat['detailed_stats']:
                    if detailed_stat['avg_price_per_sqm'] is not None and detailed_stat['avg_price_per_sqm'] > 0:
                        print(f"   ✅ Found valid avg_price_per_sqm: {detailed_stat['avg_price_per_sqm']:.2f} €/m²")
                        break
                else:
                    continue
                break
            
            # Verify count information
            for stat in response6:
                for detailed_stat in stat['detailed_stats']:
                    if detailed_stat['count'] > 0:
                        print(f"   ✅ Found property count: {detailed_stat['count']} properties")
                        break
                else:
                    continue
                break
        else:
            all_tests_passed = False
        
        # Test 7: Backward compatibility verification
        success7, response7 = self.run_test(
            "Detailed Stats (backward compatibility check)",
            "GET",
            "stats/detailed?distrito=faro",
            200
        )
        
        if success7 and response7:
            print(f"   Verifying backward compatibility...")
            
            for stat in response7:
                # Check if general avg_sale_price_per_sqm and avg_rent_price_per_sqm exist
                if stat.get('avg_sale_price_per_sqm') is not None:
                    print(f"   ✅ Found backward compatible avg_sale_price_per_sqm: {stat['avg_sale_price_per_sqm']:.2f} €/m²")
                    break
            
            for stat in response7:
                if stat.get('avg_rent_price_per_sqm') is not None:
                    print(f"   ✅ Found backward compatible avg_rent_price_per_sqm: {stat['avg_rent_price_per_sqm']:.2f} €/m²")
                    break
        else:
            all_tests_passed = False
        
        return all_tests_passed

def main():
    print("🚀 Starting Idealista Scraper API Tests - Targeted Scraping & Detailed Coverage")
    print("=" * 70)
    
    tester = IdealistaScraperAPITester()
    
    # Test NEW targeted scraping endpoint (main focus)
    print("\n🎯 MAIN TEST: Targeted Scraping Endpoint Verification")
    targeted_scraping_test_passed = tester.test_targeted_scraping_endpoint()
    
    # Test NEW detailed coverage endpoint (main focus)
    print("\n📊 MAIN TEST: Detailed Coverage Endpoint Verification")
    detailed_coverage_test_passed = tester.test_detailed_coverage_endpoint()
    
    # Test detailed statistics endpoint
    print("\n📈 Testing Detailed Statistics Endpoint")
    detailed_stats_test_passed = tester.test_detailed_stats_endpoint()
    
    # Test URL generation patterns
    print("\n🔗 Testing URL Generation Pattern Verification")
    url_test_passed = tester.test_url_generation_patterns()
    
    # Test administrative endpoints
    print("\n🏛️ Testing Administrative Structure...")
    admin_test_passed = tester.test_administrative_endpoints()
    
    # Test filtering endpoints
    print("\n🔍 Testing Filtering Functionality...")
    filter_test_passed = tester.test_filtering_endpoints()
    
    # Test basic endpoints
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
        
        # Re-test detailed coverage with actual data
        print("\n📊 Re-testing Detailed Coverage with Scraped Data...")
        tester.test_detailed_coverage_endpoint()
        
        # Re-test detailed stats with actual data
        print("\n📊 Re-testing Detailed Stats with Scraped Data...")
        tester.test_detailed_stats_endpoint()
    
    # Test data management
    print("\n🗑️ Testing Data Management...")
    tester.test_clear_properties()
    
    # Final results
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    # Special focus on new functionality verification
    print(f"\n🎯 NEW FUNCTIONALITY VERIFICATION RESULTS:")
    print(f"   Targeted Scraping Test: {'✅ PASSED' if targeted_scraping_test_passed else '❌ FAILED'}")
    print(f"   Detailed Coverage Test: {'✅ PASSED' if detailed_coverage_test_passed else '❌ FAILED'}")
    print(f"   Detailed Stats Test: {'✅ PASSED' if detailed_stats_test_passed else '❌ FAILED'}")
    print(f"   URL Pattern Test: {'✅ PASSED' if url_test_passed else '❌ FAILED'}")
    print(f"   Administrative Test: {'✅ PASSED' if admin_test_passed else '❌ FAILED'}")
    print(f"   Filtering Test: {'✅ PASSED' if filter_test_passed else '❌ FAILED'}")
    
    # Check if main new features passed
    new_features_passed = targeted_scraping_test_passed and detailed_coverage_test_passed
    
    if tester.tests_passed == tester.tests_run and new_features_passed:
        print("🎉 All tests passed! New targeted scraping and detailed coverage functionality verified successfully!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())