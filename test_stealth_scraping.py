#!/usr/bin/env python3
"""
Test stealth scraping functionality to verify it bypasses 403 Forbidden errors
"""

import asyncio
import sys
sys.path.append('/app')

from backend.server import StealthScraper
import requests

async def test_stealth_scraper():
    """Test the stealth scraper against Idealista URLs"""
    
    print("🕵️ Testing Stealth Scraper Functionality")
    print("=" * 60)
    
    # Initialize stealth scraper
    scraper = StealthScraper()
    
    # Test URLs that were previously giving 403 errors
    test_urls = [
        "https://www.idealista.pt/arrendar-casas/aveiro/eixo-e-eirol/com-apartamentos,arrendamento-longa-duracao/",
        "https://www.idealista.pt/comprar-casas/aveiro/eixo-e-eirol/com-apartamentos/",
        "https://www.idealista.pt/comprar-casas/tavira/conceicao-e-cabanas-de-tavira/com-apartamentos/"
    ]
    
    results = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n🔍 Test {i}/3: Testing stealth scraping...")
        print(f"URL: {url}")
        
        try:
            # Use stealth scraper
            response = await scraper.stealthy_get(url, timeout=20)
            
            print(f"📡 Response status: {response.status_code}")
            print(f"📄 Content length: {len(response.text)} characters")
            
            if response.status_code == 200:
                print("✅ SUCCESS: Bypassed blocking, received 200 OK")
                
                # Test price extraction
                zone_price, error = scraper.extract_zone_price(response.text, url)
                if zone_price:
                    print(f"💰 PRICE FOUND: {zone_price:.2f} €/m²")
                    results.append({'url': url, 'status': 'SUCCESS', 'price': zone_price})
                else:
                    print(f"⚠️ No price found: {error}")
                    results.append({'url': url, 'status': 'NO_PRICE', 'error': error})
                    
            elif response.status_code == 403:
                print("❌ STILL BLOCKED: 403 Forbidden (need to adjust stealth parameters)")
                results.append({'url': url, 'status': 'BLOCKED', 'error': '403 Forbidden'})
                
            elif response.status_code == 429:
                print("⏳ RATE LIMITED: 429 Too Many Requests")
                results.append({'url': url, 'status': 'RATE_LIMITED', 'error': '429 Rate Limited'})
                
            else:
                print(f"⚠️ UNEXPECTED STATUS: {response.status_code}")
                results.append({'url': url, 'status': f'HTTP_{response.status_code}', 'error': f'HTTP {response.status_code}'})
                
            # Check response headers for debugging
            print("📋 Response headers:")
            interesting_headers = ['content-type', 'server', 'x-rate-limit', 'cf-ray', 'set-cookie']
            for header in interesting_headers:
                if header in response.headers:
                    print(f"   {header}: {response.headers[header]}")
            
        except requests.exceptions.Timeout:
            print("⏰ REQUEST TIMEOUT")
            results.append({'url': url, 'status': 'TIMEOUT', 'error': 'Request timeout'})
            
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 CONNECTION ERROR: {e}")
            results.append({'url': url, 'status': 'CONNECTION_ERROR', 'error': str(e)})
            
        except Exception as e:
            print(f"💥 UNEXPECTED ERROR: {e}")
            results.append({'url': url, 'status': 'ERROR', 'error': str(e)})
        
        # Wait between tests
        if i < len(test_urls):
            print("⏳ Waiting before next test...")
            await asyncio.sleep(10)  # 10 second delay between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 STEALTH SCRAPING TEST RESULTS")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    blocked_count = sum(1 for r in results if r['status'] == 'BLOCKED')
    price_found_count = sum(1 for r in results if r['status'] == 'SUCCESS' and 'price' in r)
    
    print(f"Total tests: {len(results)}")
    print(f"✅ Successful bypasses: {success_count}")
    print(f"❌ Still blocked (403): {blocked_count}")
    print(f"💰 Prices extracted: {price_found_count}")
    
    if success_count > 0:
        print("\n🎉 STEALTH SCRAPER IS WORKING!")
        print("The new stealth approach is successfully bypassing 403 blocks")
    else:
        print("\n⚠️ STEALTH SCRAPER NEEDS ADJUSTMENT")
        print("All requests are still being blocked - need to enhance stealth parameters")
    
    for result in results:
        print(f"\n{result['url'][:50]}...")
        print(f"   Status: {result['status']}")
        if 'price' in result:
            print(f"   Price: {result['price']:.2f} €/m²")
        if 'error' in result:
            print(f"   Error: {result['error']}")

def main():
    """Run the stealth scraper test"""
    asyncio.run(test_stealth_scraper())

if __name__ == "__main__":
    main()