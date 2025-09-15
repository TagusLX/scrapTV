import json

def add_fields_to_structure(data):
    for distrito_name, distrito_data in data['php_array'].items():
        add_new_fields(distrito_data)
        for concelho_name, concelho_data in distrito_data['freguesias'].items():
            add_new_fields(concelho_data)
            for freguesia_name, freguesia_data in concelho_data['freguesias'].items():
                add_new_fields(freguesia_data)
    return data

def add_new_fields(location_data):
    location_data['url'] = ""
    location_data['last_update'] = ""
    location_data['average_t0_sale'] = 0
    location_data['average_t1_sale'] = 0
    location_data['average_t2_sale'] = 0
    location_data['average_t3_sale'] = 0
    location_data['average_t4_sale'] = 0
    location_data['average_t5_sale'] = 0
    location_data['average_t0_rent'] = 0
    location_data['average_t1_rent'] = 0
    location_data['average_t2_rent'] = 0
    location_data['average_t3_rent'] = 0
    location_data['average_t4_rent'] = 0
    location_data['average_t5_rent'] = 0
    location_data['average_new_houses_sale'] = 0
    location_data['average_good_condition_houses_sale'] = 0
    location_data['average_to_renovate_houses_sale'] = 0
    location_data['average_new_apartments_sale'] = 0
    location_data['average_good_condition_apartments_sale'] = 0
    location_data['average_to_renovate_apartments_sale'] = 0
    location_data['average_buildable_land_sale'] = 0
    location_data['average_agricultural_land_sale'] = 0

if __name__ == "__main__":
    with open('wp-idealista-scraper/includes/data/portugal_administrative_structure.json', 'r') as f:
        structure = json.load(f)

    new_structure = add_fields_to_structure(structure)

    with open('wp-idealista-scraper/includes/data/portugal_administrative_structure.json', 'w') as f:
        json.dump(new_structure, f, indent=4, ensure_ascii=False)

    print("Fields added to structure successfully.")
