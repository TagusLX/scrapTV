from scrapfly import ScrapflyClient, ScrapeConfig
from bs4 import BeautifulSoup
import json
import re

locations = [
    {"name": "Portugal", "code": "portugal", "report_name": "Portugal"},
    {"name": "Continental", "code": "portugal-continental", "report_name": "Continental"},
    {"name": "Região Autónoma da Madeira", "code": "madeira-ilha", "report_name": "Madeira (Ilha)"},
    {"name": "Região Autónoma dos Açores", "code": "acores", "report_name": "Açores"},
    {"name": "Aveiro", "code": "aveiro", "report_name": "Aveiro"},
    {"name": "Beja", "code": "beja", "report_name": "Beja"},
    {"name": "Braga", "code": "braga", "report_name": "Braga"},
    {"name": "Bragança", "code": "braganca", "report_name": "Bragança"},
    {"name": "Castelo Branco", "code": "castelo-branco", "report_name": "Castelo Branco"},
    {"name": "Coimbra", "code": "coimbra", "report_name": "Coimbra"},
    {"name": "Évora", "code": "evora", "report_name": "Évora"},
    {"name": "Faro", "code": "faro", "report_name": "Faro"},
    {"name": "Guarda", "code": "guarda", "report_name": "Guarda"},
    {"name": "Leiria", "code": "leiria", "report_name": "Leiria"},
    {"name": "Lisboa", "code": "lisboa", "report_name": "Lisboa"},
    {"name": "Portalegre", "code": "portalegre", "report_name": "Portalegre"},
    {"name": "Porto", "code": "porto", "report_name": "Porto"},
    {"name": "Santarém", "code": "santarem", "report_name": "Santarém"},
    {"name": "Setúbal", "code": "setubal", "report_name": "Setúbal"},
    {"name": "Viana do Castelo", "code": "viana-do-castelo", "report_name": "Viana do Castelo"},
    {"name": "Vila Real", "code": "vila-real", "report_name": "Vila Real"},
    {"name": "Viseu", "code": "viseu", "report_name": "Viseu"},
    {"name": "Ilha da Madeira", "code": "madeira-ilha", "report_name": "Madeira (Ilha)"},
    {"name": "Ilha de Porto Santo", "code": "porto-santo-ilha", "report_name": "Porto Santo (Ilha)"},
    {"name": "Ilha de Santa Maria", "code": "santa-maria-ilha", "report_name": "Santa Maria (Ilha)"},
    {"name": "Ilha de São Miguel", "code": "sao-miguel-ilha", "report_name": "São Miguel (ilha)"},
    {"name": "Ilha Terceira", "code": "terceira-ilha", "report_name": "Terceira (Ilha)"},
    {"name": "Ilha Graciosa", "code": "graciosa-ilha", "report_name": "Graciosa (Ilha)"},
    {"name": "Ilha de São Jorge", "code": "sao-jorge-ilha", "report_name": "São Jorge (Ilha)"},
    {"name": "Ilha do Pico", "code": "pico-ilha", "report_name": "Pico (Ilha)"},
    {"name": "Ilha do Faial", "code": "faial-ilha", "report_name": "Faial (Ilha)"},
    {"name": "Ilha das Flores", "code": "flores-ilha", "report_name": "Flores (Ilha)"},
    {"name": "Ilha do Corvo", "code": "corvo-ilha", "report_name": "Corvo (Ilha)"},
]

def get_price(soup):
    price_span = soup.find('div', class_='stats-text-container')
    if price_span:
        price_text = price_span.find('strong').text.strip().replace('.', '').replace(',', '.')
        try:
            return int(float(price_text))
        except ValueError:
            return 0
    return 0

def scrape_prices_with_scrapfly():
    scrapfly = ScrapflyClient(key="scp-test-4e3c6fb3875f4c9ea9c4ea6bbbc8b40d")
    market_prices = {location['name']: {"name": location['name'], "code": location['code'], "average": 0, "average_rent": 0} for location in locations}

    # Scrape sale prices
    sale_url = "https://www.idealista.pt/media/relatorios-preco-habitacao/venda/report/"
    sale_response = scrapfly.scrape(ScrapeConfig(url=sale_url, asp=True))
    sale_soup = BeautifulSoup(sale_response.content, 'html.parser')

    sale_table = sale_soup.find('table')
    for row in sale_table.find_all('tr')[1:]:
        cols = row.find_all('td')
        location_name = cols[0].text.strip()
        price_text = cols[1].text.strip().replace('€/m2', '').replace('.', '').replace(',', '.').strip()

        for location in locations:
            if location['report_name'] == location_name:
                market_prices[location['name']]['average'] = int(float(price_text))

    # Scrape rent prices
    rent_url = "https://www.idealista.pt/media/relatorios-preco-habitacao/arrendamento/report/"
    rent_response = scrapfly.scrape(ScrapeConfig(url=rent_url, asp=True))
    rent_soup = BeautifulSoup(rent_response.content, 'html.parser')

    rent_table = rent_soup.find('table')
    for row in rent_table.find_all('tr')[1:]:
        cols = row.find_all('td')
        location_name = cols[0].text.strip()
        price_text = cols[1].text.strip().replace('€/m2', '').replace('.', '').replace(',', '.').strip()

        for location in locations:
            if location['report_name'] == location_name:
                market_prices[location['name']]['average_rent'] = int(float(price_text))

    # Hardcode missing values
    market_prices['Continental']['average'] = 2951
    market_prices['Continental']['average_rent'] = 16
    market_prices['Região Autónoma dos Açores']['average'] = 2162
    market_prices['Região Autónoma dos Açores']['average_rent'] = 11

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
    market_prices = scrape_prices_with_scrapfly()
    generate_php_file(market_prices)
    print("market-prices.php generated successfully.")
