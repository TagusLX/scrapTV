import json
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DATA_FILE = ROOT_DIR / 'wp-idealista-scraper' / 'includes' / 'data' / 'portugal_administrative_structure_copy.json'

def load_and_test_data():
    """Loads the market data structure and prints the number of districts."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            districts = data.get('php_array', {})
            print(f"Number of districts loaded: {len(districts)}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading data: {e}")

if __name__ == "__main__":
    load_and_test_data()
