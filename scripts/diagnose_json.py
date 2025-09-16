import json
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DATA_FILE = ROOT_DIR / 'wp-idealista-scraper' / 'includes' / 'data' / 'portugal_administrative_structure.json'

def diagnose_json():
    """Loads the market data structure and reports any JSON decoding errors."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            districts = data.get('php_array', {})
            print(f"Successfully loaded JSON data. Number of districts: {len(districts)}")
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print(f"Error is at line {e.lineno}, column {e.colno}")

        # Try to read the problematic line
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if 0 < e.lineno <= len(lines):
                    print("Problematic line:")
                    print(f">>> {lines[e.lineno - 1].strip()}")

                    # Print context
                    print("Context (5 lines before and after):")
                    start = max(0, e.lineno - 6)
                    end = min(len(lines), e.lineno + 5)
                    for i in range(start, end):
                        print(f"{i+1:5d}: {lines[i].strip()}")
        except Exception as read_e:
            print(f"Could not read the file to show context: {read_e}")

    except FileNotFoundError:
        print(f"File not found: {DATA_FILE}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    diagnose_json()
