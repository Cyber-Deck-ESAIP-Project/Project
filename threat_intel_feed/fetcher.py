import requests

API_URL = "https://cve.circl.lu/api/last"

def fetch_latest():
    try:
        r = requests.get(API_URL, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[!] Fetch error: {e}")
        return []
