"""Mock authorized institutional-record adapter (AICTE records). Replace ONLY with an authorized integration."""
import json, os

PATH = os.path.join(os.path.dirname(__file__), "..", "data", "institution_records.json")


def get_record(institution_id, path=None):
    try:
        with open(path or PATH) as f:
            return json.load(f).get(institution_id)
    except FileNotFoundError:
        return None
