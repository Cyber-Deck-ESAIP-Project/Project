import sys
import json
from datetime import datetime

from fetcher import fetch_latest
from parser import filter_cves
from storage import save, load
from alert import send_alert

CONFIG_FILE = "config.json"


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def update():
    print("[*] Fetching CVEs...")

    config = load_config()
    keywords = config.get("keywords", [])

    data = fetch_latest()
    print(f"[DEBUG] Raw fetched: {len(data)}")

    filtered = filter_cves(data, keywords)
    print(f"[DEBUG] Filtered: {len(filtered)}")

    # fallback if nothing matched
    if not filtered:
        print("[!] No matches, saving fallback data")
        filtered = [
            {
                "id": f"RAW-{i}",
                "summary": str(cve)[:200],
                "cvss": "N/A"
            }
            for i, cve in enumerate(data[:10])
        ]

    new_items = save(filtered)

    print(f"[+] Stored {len(filtered)} CVEs")

    if new_items:
        print(f"\n🚨 NEW THREATS DETECTED: {len(new_items)}")

        for cve in new_items:
            print("-------------------------")
            print(f"ID: {cve.get('id')}")
            print(f"Summary: {cve.get('summary')[:120]}")

            # ✅ TELEGRAM ALERT
            msg = f"🚨 {cve.get('id')}\n{cve.get('summary')[:150]}"
            print(msg)
            send_alert(msg)
    else:
        print("\n[+] No new threats")


def show():
    data = load()

    if not data.get("results"):
        print("[!] No CVEs stored")
        return

    print(f"[+] Last updated: {data.get('timestamp')}")

    for cve in data["results"]:
        print("\n-------------------------")
        print(f"ID: {cve.get('id')}")
        print(f"CVSS: {cve.get('cvss')}")
        print(f"Summary: {cve.get('summary')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py [update|show]")
        exit()

    if sys.argv[1] == "update":
        update()
    elif sys.argv[1] == "show":
        show()
