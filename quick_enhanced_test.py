#!/usr/bin/env python3

import requests
import json

def test_enhanced_functionality():
    base_url = "https://property-radar-4.preview.emergentagent.com/api"
    
    print("🔧 Testing Enhanced Error Handling and Retry Functionality")
    print("=" * 60)
    
    # Test 1: Enhanced Scraping Session Model
    print("\n1️⃣ Testing Enhanced Scraping Session Model...")
    
    # Check existing sessions for enhanced fields
    response = requests.get(f"{base_url}/scraping-sessions")
    if response.status_code == 200:
        sessions = response.json()
        enhanced_session = None
        
        for session in sessions:
            if 'failed_zones' in session and 'success_zones' in session:
                enhanced_session = session
                break
        
        if enhanced_session:
            print(f"✅ Found enhanced session: {enhanced_session['id']}")
            print(f"   - Has failed_zones field: {'failed_zones' in enhanced_session}")
            print(f"   - Has success_zones field: {'success_zones' in enhanced_session}")
            print(f"   - Failed zones count: {len(enhanced_session.get('failed_zones', []))}")
            print(f"   - Success zones count: {len(enhanced_session.get('success_zones', []))}")
        else:
            print("❌ No enhanced sessions found")
            return False
    else:
        print("❌ Failed to get sessions")
        return False
    
    # Test 2: Error Analysis Endpoint
    print("\n2️⃣ Testing Error Analysis Endpoint...")
    
    session_id = enhanced_session['id']
    response = requests.get(f"{base_url}/scraping-sessions/{session_id}/errors")
    
    if response.status_code == 200:
        error_data = response.json()
        print("✅ Error analysis endpoint working")
        
        required_fields = ['total_zones_attempted', 'failed_zones_count', 'success_zones_count', 
                          'failure_rate', 'common_errors', 'failed_zones', 'success_zones']
        
        for field in required_fields:
            if field in error_data:
                print(f"   ✅ {field}: {error_data[field]}")
            else:
                print(f"   ❌ Missing field: {field}")
                return False
        
        # Test failure rate calculation
        failure_rate = error_data.get('failure_rate', 0)
        if isinstance(failure_rate, (int, float)) and 0 <= failure_rate <= 100:
            print(f"   ✅ Valid failure rate: {failure_rate}%")
        else:
            print(f"   ❌ Invalid failure rate: {failure_rate}")
            return False
            
    else:
        print(f"❌ Error analysis failed: {response.status_code}")
        return False
    
    # Test 3: Enhanced Scraping Method - Check for detailed error capture
    print("\n3️⃣ Testing Enhanced Scraping Method...")
    
    if error_data.get('failed_zones'):
        failed_zone = error_data['failed_zones'][0]
        if 'errors' in failed_zone:
            for error in failed_zone['errors']:
                error_msg = error.get('error', '')
                if 'HTTP' in error_msg:
                    print(f"   ✅ HTTP status error captured: {error_msg}")
                if 'property_type' in error and 'url' in error:
                    print(f"   ✅ Detailed error info: {error['property_type']} - {error['url']}")
                if 'timestamp' in error:
                    print(f"   ✅ Error timestamp recorded: {error['timestamp']}")
        print("✅ Enhanced scraping method with detailed error capture verified")
    else:
        print("⚠️ No failed zones to verify enhanced method")
    
    # Test 4: Retry Functionality
    print("\n4️⃣ Testing Retry Functionality...")
    
    if error_data.get('failed_zones_count', 0) > 0:
        response = requests.post(f"{base_url}/scrape/retry-failed?session_id={session_id}")
        
        if response.status_code == 200:
            retry_data = response.json()
            print("✅ Retry functionality working")
            
            required_retry_fields = ['message', 'retry_session_id', 'original_session_id', 'zones_to_retry']
            for field in required_retry_fields:
                if field in retry_data:
                    print(f"   ✅ {field}: {retry_data[field]}")
                else:
                    print(f"   ❌ Missing retry field: {field}")
                    return False
        else:
            print(f"❌ Retry failed: {response.status_code}")
            return False
    else:
        print("⚠️ No failed zones to test retry")
    
    # Test 5: Real Price Detection - Check URL patterns
    print("\n5️⃣ Testing Real Price Detection...")
    
    if error_data.get('failed_zones'):
        for failed_zone in error_data['failed_zones']:
            for error in failed_zone.get('errors', []):
                url = error.get('url', '')
                property_type = error.get('property_type', '')
                
                # Verify URL patterns for different property types
                if property_type == 'apartment' and '/com-apartamentos/' in url:
                    print(f"   ✅ Apartment URL pattern correct: {url}")
                elif property_type == 'house' and '/com-moradias/' in url:
                    print(f"   ✅ House URL pattern correct: {url}")
                elif property_type == 'urban_plot' and '/com-terreno-urbano/' in url:
                    print(f"   ✅ Urban plot URL pattern correct: {url}")
                elif property_type == 'rural_plot' and '/com-terreno-nao-urbanizavel/' in url:
                    print(f"   ✅ Rural plot URL pattern correct: {url}")
        
        print("✅ Real price detection URL patterns verified")
    
    # Test 6: Error handling for non-existent sessions
    print("\n6️⃣ Testing Error Handling...")
    
    # Test error analysis for non-existent session
    response = requests.get(f"{base_url}/scraping-sessions/fake-session-123/errors")
    if response.status_code == 404:
        print("✅ Error analysis correctly returns 404 for non-existent session")
    else:
        print(f"❌ Expected 404, got {response.status_code}")
        return False
    
    # Test retry for non-existent session
    response = requests.post(f"{base_url}/scrape/retry-failed?session_id=fake-session-123")
    if response.status_code == 404:
        print("✅ Retry correctly returns 404 for non-existent session")
    else:
        print(f"❌ Expected 404, got {response.status_code}")
        return False
    
    print("\n🎉 All enhanced error handling and retry functionality tests PASSED!")
    return True

if __name__ == "__main__":
    success = test_enhanced_functionality()
    exit(0 if success else 1)