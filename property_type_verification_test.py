#!/usr/bin/env python3
"""
Property Type Categorization & Rural Plot Verification Test

This test specifically verifies the improved property type categorization 
and rural plot scraping functionality as requested in the review.
"""

import requests
import json
from collections import defaultdict

class PropertyTypeVerificationTester:
    def __init__(self, base_url="https://property-radar-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        
    def get_properties(self):
        """Get all properties from the API"""
        response = requests.get(f"{self.api_url}/properties")
        if response.status_code == 200:
            return response.json()
        return []
    
    def get_detailed_stats(self, **filters):
        """Get detailed statistics with optional filters"""
        params = "&".join([f"{k}={v}" for k, v in filters.items() if v])
        url = f"{self.api_url}/stats/detailed"
        if params:
            url += f"?{params}"
        
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return []
    
    def test_property_type_categorization(self):
        """Test 1: Verify property types are correctly categorized"""
        print("🏠 Test 1: Property Type Categorization")
        print("=" * 50)
        
        properties = self.get_properties()
        print(f"Total properties found: {len(properties)}")
        
        if not properties:
            print("❌ No properties found to test")
            return False
        
        # Check property types
        property_types = set()
        administrative_unit_count = 0
        
        for prop in properties:
            prop_type = prop.get('property_type', 'unknown')
            property_types.add(prop_type)
            
            if prop_type == 'administrative_unit':
                administrative_unit_count += 1
        
        print(f"Property types found: {sorted(property_types)}")
        
        # Verify expected property types exist
        expected_types = {'apartment', 'house', 'urban_plot', 'rural_plot'}
        found_expected_types = property_types.intersection(expected_types)
        
        success = True
        
        if found_expected_types:
            print(f"✅ Found expected property types: {sorted(found_expected_types)}")
        else:
            print(f"❌ No expected property types found")
            success = False
        
        # Verify no administrative_unit entries
        if administrative_unit_count == 0:
            print(f"✅ No 'administrative_unit' entries found (as expected)")
        else:
            print(f"❌ Found {administrative_unit_count} 'administrative_unit' entries (should be 0)")
            success = False
        
        return success
    
    def test_property_type_multipliers(self):
        """Test 2: Verify property type pricing multipliers"""
        print("\n💰 Test 2: Property Type Pricing Multipliers")
        print("=" * 50)
        
        properties = self.get_properties()
        
        if not properties:
            print("❌ No properties found to test")
            return False
        
        # Group properties by type and calculate average prices
        type_prices = defaultdict(list)
        
        for prop in properties:
            prop_type = prop.get('property_type', 'unknown')
            price_per_sqm = prop.get('price_per_sqm')
            operation_type = prop.get('operation_type')
            
            if price_per_sqm and price_per_sqm > 0 and operation_type == 'sale':
                type_prices[prop_type].append(price_per_sqm)
        
        # Calculate averages
        type_averages = {}
        for prop_type, prices in type_prices.items():
            if prices:
                type_averages[prop_type] = sum(prices) / len(prices)
        
        print("Property type average prices (sales only):")
        for prop_type, avg_price in type_averages.items():
            print(f"  {prop_type}: {avg_price:.2f} €/m²")
        
        success = True
        
        # Verify relative pricing (multipliers)
        if 'house' in type_averages:
            house_price = type_averages['house']
            
            # Test apartment multiplier (~1.1x)
            if 'apartment' in type_averages:
                apartment_ratio = type_averages['apartment'] / house_price
                print(f"\nApartment vs House ratio: {apartment_ratio:.2f}x (expected ~1.1x)")
                if 1.05 <= apartment_ratio <= 1.15:
                    print("✅ Apartment pricing multiplier correct")
                else:
                    print("⚠️ Apartment pricing multiplier outside expected range")
            
            # Test urban plot multiplier (~0.4x)
            if 'urban_plot' in type_averages:
                urban_plot_ratio = type_averages['urban_plot'] / house_price
                print(f"Urban plot vs House ratio: {urban_plot_ratio:.2f}x (expected ~0.4x)")
                if 0.35 <= urban_plot_ratio <= 0.45:
                    print("✅ Urban plot pricing multiplier correct")
                else:
                    print("⚠️ Urban plot pricing multiplier outside expected range")
            
            # Test rural plot multiplier (~0.15x)
            if 'rural_plot' in type_averages:
                rural_plot_ratio = type_averages['rural_plot'] / house_price
                print(f"Rural plot vs House ratio: {rural_plot_ratio:.2f}x (expected ~0.15x)")
                if 0.10 <= rural_plot_ratio <= 0.20:
                    print("✅ Rural plot pricing multiplier correct")
                else:
                    print("⚠️ Rural plot pricing multiplier outside expected range")
        else:
            print("❌ No house properties found for comparison")
            success = False
        
        return success
    
    def test_rural_plot_urls(self):
        """Test 3: Verify rural plot URLs are only for sales"""
        print("\n🔗 Test 3: Rural Plot URL Generation")
        print("=" * 50)
        
        properties = self.get_properties()
        
        if not properties:
            print("❌ No properties found to test")
            return False
        
        rural_plots_found = 0
        rural_plots_in_sales = 0
        rural_plots_in_rentals = 0
        url_errors = []
        
        for prop in properties:
            if prop.get('property_type') == 'rural_plot':
                rural_plots_found += 1
                operation_type = prop.get('operation_type', 'unknown')
                url = prop.get('url', '')
                
                if operation_type == 'sale':
                    rural_plots_in_sales += 1
                    # Verify URL pattern
                    if '/comprar-terrenos/' in url and '/com-terreno-nao-urbanizavel/' in url:
                        print(f"✅ Rural plot sale URL correct: {url}")
                    else:
                        print(f"❌ Rural plot sale URL incorrect: {url}")
                        url_errors.append(url)
                elif operation_type == 'rent':
                    rural_plots_in_rentals += 1
                    print(f"❌ Found rural plot in rentals (should not exist): {url}")
        
        print(f"\nRural plots summary:")
        print(f"  Total: {rural_plots_found}")
        print(f"  Sales: {rural_plots_in_sales}")
        print(f"  Rentals: {rural_plots_in_rentals}")
        
        success = True
        
        if rural_plots_in_rentals == 0:
            print("✅ No rural plots found in rentals (as expected)")
        else:
            print(f"❌ Found {rural_plots_in_rentals} rural plots in rentals (should be 0)")
            success = False
        
        if not url_errors:
            print("✅ All rural plot URLs are correctly formatted")
        else:
            print(f"❌ Found {len(url_errors)} incorrectly formatted URLs")
            success = False
        
        return success
    
    def test_detailed_statistics_filtering(self):
        """Test 4: Verify detailed statistics filtering with new property types"""
        print("\n📊 Test 4: Detailed Statistics Filtering")
        print("=" * 50)
        
        success = True
        
        # Test urban_plot filter
        urban_plot_stats = self.get_detailed_stats(property_type='urban_plot')
        print(f"Urban plot detailed stats: {len(urban_plot_stats)} regions")
        
        if urban_plot_stats:
            for stat in urban_plot_stats:
                for detailed_stat in stat['detailed_stats']:
                    if detailed_stat['property_type'] != 'urban_plot':
                        print(f"❌ Found non-urban_plot in filter: {detailed_stat['property_type']}")
                        success = False
                        break
                else:
                    continue
                break
            else:
                print("✅ All detailed stats are for urban_plot properties")
        
        # Test rural_plot filter
        rural_plot_stats = self.get_detailed_stats(property_type='rural_plot')
        print(f"Rural plot detailed stats: {len(rural_plot_stats)} regions")
        
        if rural_plot_stats:
            for stat in rural_plot_stats:
                for detailed_stat in stat['detailed_stats']:
                    if detailed_stat['property_type'] != 'rural_plot':
                        print(f"❌ Found non-rural_plot in filter: {detailed_stat['property_type']}")
                        success = False
                        break
                    # Verify rural plots are only in sales
                    if detailed_stat['operation_type'] != 'sale':
                        print(f"❌ Found rural plot in non-sale operation: {detailed_stat['operation_type']}")
                        success = False
                        break
                else:
                    continue
                break
            else:
                print("✅ All detailed stats are for rural_plot properties (sales only)")
        
        return success
    
    def test_database_entries_correctness(self):
        """Test 5: Verify database entries have correct property_type values"""
        print("\n🗄️ Test 5: Database Entries Correctness")
        print("=" * 50)
        
        # Get detailed stats to verify proper categorization
        detailed_stats = self.get_detailed_stats()
        
        if not detailed_stats:
            print("❌ No detailed stats found")
            return False
        
        all_property_types = set()
        for stat in detailed_stats:
            for detailed_stat in stat['detailed_stats']:
                all_property_types.add(detailed_stat['property_type'])
        
        print(f"Property types in detailed stats: {sorted(all_property_types)}")
        
        success = True
        
        # Check that we don't have administrative_unit in detailed stats
        if 'administrative_unit' not in all_property_types:
            print("✅ No 'administrative_unit' in detailed stats (as expected)")
        else:
            print("❌ Found 'administrative_unit' in detailed stats (should not exist)")
            success = False
        
        # Check for expected property types
        expected_in_stats = {'apartment', 'house', 'urban_plot', 'rural_plot'}
        found_in_stats = all_property_types.intersection(expected_in_stats)
        
        if found_in_stats:
            print(f"✅ Found expected property types in detailed stats: {sorted(found_in_stats)}")
        else:
            print("❌ No expected property types found in detailed stats")
            success = False
        
        return success
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("🚀 Property Type Categorization & Rural Plot Verification")
        print("=" * 70)
        
        results = []
        
        # Run all tests
        results.append(("Property Type Categorization", self.test_property_type_categorization()))
        results.append(("Property Type Multipliers", self.test_property_type_multipliers()))
        results.append(("Rural Plot URLs", self.test_rural_plot_urls()))
        results.append(("Detailed Statistics Filtering", self.test_detailed_statistics_filtering()))
        results.append(("Database Entries Correctness", self.test_database_entries_correctness()))
        
        # Summary
        print("\n" + "=" * 70)
        print("📋 TEST RESULTS SUMMARY")
        print("=" * 70)
        
        passed_tests = 0
        total_tests = len(results)
        
        for test_name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name}: {status}")
            if passed:
                passed_tests += 1
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All property type categorization and rural plot tests PASSED!")
            return True
        else:
            print("❌ Some tests failed. Review the implementation.")
            return False

def main():
    tester = PropertyTypeVerificationTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())