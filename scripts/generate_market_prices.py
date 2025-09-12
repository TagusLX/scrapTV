import json

data = {
    "Portugal (the whole country)": {"sale": 2951, "rent": 16.8},
    "Continental (the mainland)": {"sale": 2951, "rent": 16.8},
    "Região Autónoma da Madeira (autonomous region)": {"sale": 3536, "rent": 15.0},
    "Região Autónoma dos Açores (autonomous region)": {"sale": 2162, "rent": 11.9},
    "Aveiro (district)": {"sale": 1925, "rent": 10.0},
    "Beja (district)": {"sale": 1324, "rent": 9.6},
    "Braga (district)": {"sale": 1820, "rent": 9.9},
    "Bragança (district)": {"sale": 893, "rent": 6.5},
    "Castelo Branco (district)": {"sale": 973, "rent": 6.5},
    "Coimbra (district)": {"sale": 1525, "rent": 11.6},
    "Évora (district)": {"sale": 1511, "rent": 11.2},
    "Faro (district)": {"sale": 3792, "rent": 16.1},
    "Guarda (district)": {"sale": 785, "rent": 6.5},
    "Leiria (district)": {"sale": 1833, "rent": 10.2},
    "Lisboa (district)": {"sale": 4502, "rent": 20.5},
    "Portalegre (district)": {"sale": 869, "rent": 7.2},
    "Porto (district)": {"sale": 2952, "rent": 15.9},
    "Santarém (district)": {"sale": 1400, "rent": 8.9},
    "Setúbal (district)": {"sale": 3037, "rent": 13.9},
    "Viana do Castelo (district)": {"sale": 1593, "rent": 9.5},
    "Vila Real (district)": {"sale": 1059, "rent": 8.6},
    "Viseu (district)": {"sale": 1172, "rent": 7.9},
    "Ilha da Madeira (island)": {"sale": 3536, "rent": 15.0},
    "Ilha de Porto Santo (island)": {"sale": 2904, "rent": 10.60},
    "Ilha de Santa Maria (island)": {"sale": 1452, "rent": 10.71},
    "Ilha de São Miguel (island)": {"sale": 2162, "rent": 11.9},
    "Ilha Terceira (island)": {"sale": 1526, "rent": 10.71},
    "Ilha Graciosa (island)": {"sale": 796, "rent": 10.71},
    "Ilha de São Jorge (island)": {"sale": 1463, "rent": 10.71},
    "Ilha do Pico (island)": {"sale": 1480, "rent": 10.71},
    "Ilha do Faial (island)": {"sale": 1921, "rent": 10.71},
    "Ilha das Flores (island)": {"sale": 1488, "rent": 10.71},
    "Ilha do Corvo (island)": {"sale": 0, "rent": 0},
}

locations = [
    {"name": "Portugal", "code": "portugal"},
    {"name": "Continental", "code": "portugal-continental"},
    {"name": "Região Autónoma da Madeira", "code": "madeira-ilha"},
    {"name": "Região Autónoma dos Açores", "code": "acores"},
    {"name": "Aveiro", "code": "aveiro-distrito"},
    {"name": "Beja", "code": "beja-distrito"},
    {"name": "Braga", "code": "braga-distrito"},
    {"name": "Bragança", "code": "braganca-distrito"},
    {"name": "Castelo Branco", "code": "castelo-branco-distrito"},
    {"name": "Coimbra", "code": "coimbra-distrito"},
    {"name": "Évora", "code": "evora-distrito"},
    {"name": "Faro", "code": "faro-distrito"},
    {"name": "Guarda", "code": "guarda-distrito"},
    {"name": "Leiria", "code": "leiria-distrito"},
    {"name": "Lisboa", "code": "lisboa-distrito"},
    {"name": "Portalegre", "code": "portalegre-distrito"},
    {"name": "Porto", "code": "porto-distrito"},
    {"name": "Santarém", "code": "santarem-distrito"},
    {"name": "Setúbal", "code": "setubal-distrito"},
    {"name": "Viana do Castelo", "code": "viana-do-castelo-distrito"},
    {"name": "Vila Real", "code": "vila-real-distrito"},
    {"name": "Viseu", "code": "viseu-distrito"},
    {"name": "Ilha da Madeira", "code": "madeira-ilha"},
    {"name": "Ilha de Porto Santo", "code": "porto-santo-ilha"},
    {"name": "Ilha de Santa Maria", "code": "santa-maria-ilha-dos-acores"},
    {"name": "Ilha de São Miguel", "code": "sao-miguel-ilha-dos-acores"},
    {"name": "Ilha Terceira", "code": "terceira-ilha-dos-acores"},
    {"name": "Ilha Graciosa", "code": "graciosa-ilha-dos-acores"},
    {"name": "Ilha de São Jorge", "code": "sao-jorge-ilha-dos-acores"},
    {"name": "Ilha do Pico", "code": "pico-ilha-dos-acores"},
    {"name": "Ilha do Faial", "code": "faial-ilha-dos-acores"},
    {"name": "Ilha das Flores", "code": "flores-ilha-dos-acores"},
    {"name": "Ilha do Corvo", "code": "corvo-ilha-dos-acores"},
]


def get_prices_from_data():
    market_prices = {}
    for location in locations:
        name_map = {
            "Portugal": "Portugal (the whole country)",
            "Continental": "Continental (the mainland)",
            "Região Autónoma da Madeira": "Região Autónoma da Madeira (autonomous region)",
            "Região Autónoma dos Açores": "Região Autónoma dos Açores (autonomous region)",
            "Aveiro": "Aveiro (district)",
            "Beja": "Beja (district)",
            "Braga": "Braga (district)",
            "Bragança": "Bragança (district)",
            "Castelo Branco": "Castelo Branco (district)",
            "Coimbra": "Coimbra (district)",
            "Évora": "Évora (district)",
            "Faro": "Faro (district)",
            "Guarda": "Guarda (district)",
            "Leiria": "Leiria (district)",
            "Lisboa": "Lisboa (district)",
            "Portalegre": "Portalegre (district)",
            "Porto": "Porto (district)",
            "Santarém": "Santarém (district)",
            "Setúbal": "Setúbal (district)",
            "Viana do Castelo": "Viana do Castelo (district)",
            "Vila Real": "Vila Real (district)",
            "Viseu": "Viseu (district)",
            "Ilha da Madeira": "Ilha da Madeira (island)",
            "Ilha de Porto Santo": "Ilha de Porto Santo (island)",
            "Ilha de Santa Maria": "Ilha de Santa Maria (island)",
            "Ilha de São Miguel": "Ilha de São Miguel (island)",
            "Ilha Terceira": "Ilha Terceira (island)",
            "Ilha Graciosa": "Ilha Graciosa (island)",
            "Ilha de São Jorge": "Ilha de São Jorge (island)",
            "Ilha do Pico": "Ilha do Pico (island)",
            "Ilha do Faial": "Ilha do Faial (island)",
            "Ilha das Flores": "Ilha das Flores (island)",
            "Ilha do Corvo": "Ilha do Corvo (island)",
        }

        full_name = name_map.get(location['name'], location['name'])

        price_data = data.get(full_name, {"sale": 0, "rent": 0})

        market_prices[location['name']] = {
            "name": location['name'],
            "code": location['code'],
            "average": int(price_data['sale']),
            "average_rent": int(price_data['rent']),
        }
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
    market_prices = get_prices_from_data()
    generate_php_file(market_prices)
    print("market-prices.php generated successfully.")
