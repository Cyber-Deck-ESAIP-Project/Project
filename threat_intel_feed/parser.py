def filter_cves(cves, keywords):
    results = []

    for cve in cves:
        try:
            cve_id = cve.get("cveMetadata", {}).get("cveId", "N/A")

            desc = cve.get("containers", {}).get("cna", {}).get("descriptions", [])
            summary = desc[0].get("value", "") if desc else ""

            if not summary:
                continue

            # keyword filtering
            if keywords:
                if not any(k.lower() in summary.lower() for k in keywords):
                    continue

            results.append({
                "id": cve_id,
                "summary": summary,
                "cvss": "N/A"
            })

        except:
            continue

    return results
