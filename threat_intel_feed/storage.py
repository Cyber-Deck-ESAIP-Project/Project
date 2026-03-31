import json
from datetime import datetime

FILE = "feed.json"

def save(data):
    try:
        old = load()
        old_ids = {c["id"] for c in old.get("results", [])}
    except:
        old_ids = set()

    new_items = [c for c in data if c["id"] not in old_ids]

    with open(FILE, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": data
        }, f, indent=4)

    return new_items


def load():
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return {"results": []}


