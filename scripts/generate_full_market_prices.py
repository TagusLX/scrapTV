from scrapfly import ScrapflyClient, ScrapeConfig
from bs4 import BeautifulSoup
import json
import re

def get_price(soup):
    price_span = soup.find('div', class_='stats-text-container')
    if price_span:
        price_text = price_span.find('strong').text.strip().replace('.', '').replace(',', '.')
        try:
            return int(float(price_text))
        except ValueError:
            return 0
    return 0

def get_locations_from_structure(structure):
    locations = []
    for distrito_name, distrito_data in structure['php_array'].items():
        locations.append({"name": distrito_name, "code": distrito_data['code'], "type": "distrito"})
        for concelho_name, concelho_data in distrito_data['freguesias'].items():
            locations.append({"name": concelho_name, "code": concelho_data['code'], "type": "concelho"})
            for freguesia_name, freguesia_data in concelho_data['freguesias'].items():
                locations.append({"name": freguesia_name, "code": freguesia_data['code'], "type": "freguesia"})
    return locations


def scrape_prices_with_scrapfly(locations):
    scrapfly = ScrapflyClient(key="scp-test-4e3c6fb3875f4c9ea9c4ea6bbbc8b40d")
    market_prices = {}

    for location in locations:
        # Scrape sale price
        sale_url = f"https://www.idealista.pt/media/relatorios-preco-habitacao/venda/{location['code']}/"
        sale_response = scrapfly.scrape(ScrapeConfig(url=sale_url, asp=True))
        sale_soup = BeautifulSoup(sale_response.content, 'html.parser')
        sale_price = get_price(sale_soup)

        # Scrape rent price
        rent_url = f"https://www.idealista.pt/media/relatorios-preco-habitacao/arrendamento/{location['code']}/"
        rent_response = scrapfly.scrape(ScrapeConfig(url=rent_url, asp=True))
        rent_soup = BeautifulSoup(rent_response.content, 'html.parser')
        rent_price = get_price(rent_soup)

        market_prices[location['name']] = {
            "name": location['name'],
            "code": location['code'],
            "average": sale_price,
            "average_rent": rent_price,
        }
        print(f"Scraped {location['name']}: Sale={sale_price}, Rent={rent_price}")

    return market_prices

def generate_php_file(market_prices):
    with open('wp-idealista-scraper/includes/data/market-prices.php', 'w') as f:
        f.write("<?php\n")
        f.write("$market_prices = [\n")
        for name, data in market_prices.items():
            f.write(f'    "{name}" => [\n')
            f.write(f'        "name" => "{data["name"]}",\n')
            f.write(f'        "code" => "{data["code"]}",\n')
            f.write(f'        "average" => {data["average"]},\n')
            f.write(f'        "average_rent" => {data["average_rent"]},\n')
            f.write("    ],\n")
        f.write("];\n")

if __name__ == "__main__":
    with open('wp-idealista-scraper/includes/data/portugal_administrative_structure.json') as f:
        structure = json.load(f)

    locations = get_locations_from_structure(structure)
    market_prices = scrape_prices_with_scrapfly(locations)
    generate_php_file(market_prices)
    print("market-prices.php generated successfully.")
