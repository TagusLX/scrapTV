#!/usr/bin/env python3
"""
Test real scraping functionality for Idealista price extraction
"""

import requests
import re
from bs4 import BeautifulSoup

def test_zone_price_extraction(url):
    """Test extraction of 'Preço médio nesta zona' from a specific URL"""
    
    print(f"🔍 Testing price extraction from: {url}")
    print("=" * 80)
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text()
            
            print(f"📄 Page length: {len(page_text)} characters")
            
            # Look for "Preço médio nesta zona" in the text
            zone_text_found = False
            if 'preço médio nesta zona' in page_text.lower():
                zone_text_found = True
                print("✅ Found 'Preço médio nesta zona' text on page")
                
                # Find the context around this text
                import re
                context_match = re.search(r'.{0,100}preço médio nesta zona.{0,100}', page_text, re.IGNORECASE)
                if context_match:
                    print(f"📝 Context: {context_match.group()}")
            else:
                print("❌ 'Preço médio nesta zona' text not found on page")
            
            # Test our extraction patterns
            zone_patterns = [
                r'preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                r'Preço médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                r'médio nesta zona[:\s]*(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                # Additional patterns
                r'preço médio[^€]*?(\d+(?:[.,]\d+)?)\s*€\s*/?m²?',
                r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?[^€]*?médio'
            ]
            
            print("\n🎯 Testing extraction patterns:")
            for i, pattern in enumerate(zone_patterns, 1):
                zone_match = re.search(pattern, page_text, re.IGNORECASE)
                if zone_match:
                    price_str = zone_match.group(1).replace(',', '.')
                    try:
                        zone_price = float(price_str)
                        print(f"✅ Pattern {i}: Found price {zone_price:.2f} €/m² using pattern: {pattern[:50]}...")
                    except:
                        print(f"❌ Pattern {i}: Invalid price format: {price_str}")
                else:
                    print(f"❌ Pattern {i}: No match")
            
            # Search for any €/m² mentions
            print(f"\n🔍 Searching for all '€/m²' mentions:")
            euro_per_sqm_matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*€\s*/?m²?', page_text, re.IGNORECASE)
            if euro_per_sqm_matches:
                print(f"Found {len(euro_per_sqm_matches)} €/m² prices on page:")
                for price_str in euro_per_sqm_matches[:10]:  # Show first 10
                    clean_price = price_str.replace(',', '.')
                    try:
                        price = float(clean_price)
                        print(f"  - {price:.2f} €/m²")
                    except:
                        print(f"  - {price_str} (invalid format)")
            else:
                print("❌ No €/m² prices found on page")
                
            # Look for specific HTML elements that might contain the zone price
            print(f"\n🏷️ Looking for HTML elements with zone price info:")
            
            # Search in specific sections
            info_sections = soup.find_all(['div', 'section', 'span'], class_=re.compile(r'info|stats|summary|zone|area'))
            print(f"Found {len(info_sections)} potential info sections")
            
            for i, section in enumerate(info_sections[:5]):  # Check first 5
                section_text = section.get_text()
                if 'médio' in section_text.lower() and '€' in section_text:
                    print(f"  Section {i+1}: {section_text[:100]}...")
            
        else:
            print(f"❌ Failed to fetch page: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error during scraping test: {e}")
    
    print("=" * 80)

def main():
    # Test the specific URL mentioned by the user
    test_url = "https://www.idealista.pt/arrendar-casas/aveiro/eixo-e-eirol/com-apartamentos,arrendamento-longa-duracao/"
    test_zone_price_extraction(test_url)
    
    # Test a few more URLs for comparison
    additional_urls = [
        "https://www.idealista.pt/comprar-casas/aveiro/eixo-e-eirol/com-apartamentos/",
        "https://www.idealista.pt/comprar-casas/tavira/conceicao-e-cabanas-de-tavira/com-apartamentos/"
    ]
    
    for url in additional_urls:
        print("\n")
        test_zone_price_extraction(url)

if __name__ == "__main__":
    main()