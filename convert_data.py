import pandas as pd
import json
import unicodedata
import re

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    value = re.sub(r'[-\s]+', '-', value)
    return value

def create_administrative_structure(df):
    """
    Creates a nested dictionary for the administrative structure of Portugal.
    """
    structure = {}
    for _, row in df.iterrows():
        distrito_name = row['distrito']
        concelho_name = row['concelho']
        freguesia_name = row['freguesia']

        distrito_code = slugify(distrito_name)
        concelho_code = slugify(concelho_name)
        freguesia_code = slugify(freguesia_name)

        # Add distrito if not exists
        if distrito_name not in structure:
            structure[distrito_name] = {
                "name": distrito_name,
                "code": distrito_code,
                "average": 0,
                "average_rent": 0,
                "total_concelhos": 0,
                "freguesias": {}
            }

        # Add concelho if not exists
        if concelho_name not in structure[distrito_name]["freguesias"]:
            structure[distrito_name]["freguesias"][concelho_name] = {
                "name": concelho_name,
                "code": concelho_code,
                "average": 0,
                "average_rent": 0,
                "total_freguesias": 0,
                "freguesias": {}
            }
            structure[distrito_name]["total_concelhos"] += 1

        # Add freguesia
        if freguesia_name not in structure[distrito_name]["freguesias"][concelho_name]["freguesias"]:
            structure[distrito_name]["freguesias"][concelho_name]["freguesias"][freguesia_name] = {
                "name": freguesia_name,
                "code": freguesia_code,
                "full_path": f"{distrito_name} > {concelho_name} > {freguesia_name}",
                "average": 0,
                "average_rent": 0
            }
            structure[distrito_name]["freguesias"][concelho_name]["total_freguesias"] += 1

    return {
        "metadata": {
            "total_distritos": len(structure),
            "total_concelhos": sum(d['total_concelhos'] for d in structure.values()),
            "total_freguesias": sum(c['total_freguesias'] for d in structure.values() for c in d['freguesias'].values()),
            "format": "php_array_administrative_structure"
        },
        "php_array": structure
    }


if __name__ == "__main__":
    # Read the data from the TSV file
    df = pd.read_csv("administrative_data.tsv", sep='\t')

    # Create the nested structure
    portugal_structure = create_administrative_structure(df)

    # Write the structure to a JSON file
    with open("wp-idealista-scraper/portugal_administrative_structure.json", "w", encoding="utf-8") as f:
        json.dump(portugal_structure, f, ensure_ascii=False, indent=4)

    print("Successfully converted administrative data to JSON.")
