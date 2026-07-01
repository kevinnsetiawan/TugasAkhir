import json
import time
from pathlib import Path

import requests

ZAP_API = "http://localhost:8080"
TARGET = "http://localhost:3000"

CONTROLLED_URLS = [
    "http://localhost:3000/rest/products/search?q=",
    "http://localhost:3000/ftp/",
]

RESULTS_DIR = Path("rl_pentest/results")
OUTPUT = RESULTS_DIR / "zap_controlled_report.json"

QL_VULN_KEYWORDS = {
    "SQL Injection": "sqli",
    "sqlite": "sqli",
    "sql": "sqli",
    "Cross Site Scripting": "xss",
    "XSS": "xss",
    "Path Traversal": "path",
    "Local File Inclusion": "path",
    "LFI": "path",
    "Directory Browsing": "path",
    "Remote File Inclusion": "path",
}


def zap_api(endpoint: str, params: dict = None) -> dict | None:
    try:
        url = f"{ZAP_API}/JSON/{endpoint}"
        resp = requests.get(url, params=params, timeout=60)
        return resp.json()
    except requests.RequestException as e:
        print(f"  [!] ZAP API error: {e}")
        return None


def is_zap_running() -> bool:
    result = zap_api("core/view/version")
    return result is not None


def wait_for_scan(scan_type: str, scan_id: str, poll_interval: float = 2.0):
    if not scan_id:
        return
    while True:
        result = zap_api(f"{scan_type}/view/status", {"scanId": scan_id})
        if result is None:
            break
        status = result.get("status", "0")
        print(f"     Progress: {status}%", end="\r")
        if int(status) >= 100:
            break
        time.sleep(poll_interval)


def classify_zap_alert(alert: dict) -> str:
    name = (alert.get("alert") or "").lower()
    url = (alert.get("url") or "").lower()
    evidence = (alert.get("evidence") or "").lower()
    attack = (alert.get("attack") or "").lower()
    param = (alert.get("param") or "").lower()

    combined = f"{name} {url} {evidence} {attack} {param}"

    if any(kw in name for kw in ["sql"]) or any(
        kw in combined for kw in ["sqli", "sqlite", "db input"]
    ):
        if any(kw in combined for kw in ["time", "blind", "' or", "or 1=1", "union", "select"]):
            return "sqli"
        if "sql injection" in name:
            return "sqli"
    if any(kw in combined for kw in ["xss", "cross site", "<script", "alert(", "onerror"]):
        return "xss"
    if any(kw in combined for kw in ["path traversal", "lfi", "directory", "../", "file include"]):
        return "path"
    return "other"


def main():
    print("=" * 60)
    print("  ZAP Controlled Scan — 2 Endpoint Sama dengan Q-Learning")
    print("=" * 60)

    if not is_zap_running():
        print("\n[-] ZAP daemon tidak terdeteksi di localhost:8080.")
        print("    Jalankan ZAP daemon dulu:")
        print('    "C:\\Program Files\\ZAP\\Zed Attack Proxy\\zap.bat" -daemon -port 8080 -config api.key=')
        return

    print(f"\n[+] ZAP terdeteksi di {ZAP_API}")
    print(f"[+] Target: {TARGET}")
    print(f"[+] Endpoint: {len(CONTROLLED_URLS)} URL\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for url in CONTROLLED_URLS:
        # Step 1: Add URL to ZAP site tree via accessUrl
        print(f"[*] Accessing URL di ZAP site tree: {url}")
        zap_api("core/action/accessUrl", {"url": url})

        # Step 2: Spider (optional but helps ZAP discover more)
        print(f"[*] Spider: {url}")
        spider_result = zap_api("spider/action/scan", {"url": url, "maxChildren": 2})
        if spider_result:
            spider_id = spider_result.get("scan")
            if spider_id:
                wait_for_scan("spider", spider_id)
                print()

        # Step 3: Active scan
        print(f"[*] Active scan: {url}")
        result = zap_api("ascan/action/scan", {"url": url, "recurse": "false"})
        if result is None:
            continue
        scan_id = result.get("scan")
        if scan_id:
            wait_for_scan("ascan", scan_id)
            print()

    print("[*] Mengambil hasil alerts dari ZAP...")
    alerts_result = zap_api("core/view/alerts", {"baseurl": TARGET})
    if alerts_result is None:
        print("[-] Gagal mengambil alerts")
        return

    raw_alerts = alerts_result.get("alerts", [])

    # count total messages via progressive pages (safe limit 100/page)
    total_requests = 0
    page_size = 100
    for start in range(0, 5000, page_size):
        result = zap_api("core/view/messages", {"baseurl": TARGET, "start": start, "count": page_size})
        if result is None:
            break
        msgs = result.get("messages") or []
        count = len(msgs)
        total_requests += count
        if count < page_size:
            break

    categorized = {"sqli": [], "xss": [], "path": [], "other": []}
    for alert in raw_alerts:
        cat = classify_zap_alert(alert)
        categorized[cat].append(alert)

    report = {
        "metadata": {
            "tool": "OWASP ZAP Controlled Scan",
            "target": TARGET,
            "endpoints_scanned": CONTROLLED_URLS,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "zap_results": {
            "total_requests": total_requests,
            "total_alerts_raw": len(raw_alerts),
            "total_vulnerabilities": sum(len(v) for cat, v in categorized.items() if cat != "other"),
            "alerts_by_category": {
                "sqli": len(categorized["sqli"]),
                "xss": len(categorized["xss"]),
                "path": len(categorized["path"]),
                "other": len(categorized["other"]),
            },
            "requests_per_vulnerability": round(
                total_requests / max(sum(len(categorized[k]) for k in ("sqli", "xss", "path")), 1), 2
            ),
            "risk_breakdown": {
                "high": sum(1 for a in raw_alerts if a.get("risk") == "High"),
                "medium": sum(1 for a in raw_alerts if a.get("risk") == "Medium"),
                "low": sum(1 for a in raw_alerts if a.get("risk") == "Low"),
                "informational": sum(1 for a in raw_alerts if a.get("risk") == "Informational"),
            },
        },
        "alerts_categorized": {
            cat: [
                {
                    "name": a.get("alert"),
                    "risk": a.get("risk"),
                    "url": a.get("url"),
                    "param": a.get("param"),
                    "evidence": (a.get("evidence") or "")[:200],
                    "attack": (a.get("attack") or "")[:200],
                }
                for a in alerts
            ]
            for cat, alerts in categorized.items()
        },
    }

    OUTPUT.write_text(json.dumps(report, indent=2))
    print(f"\n[+] Laporan tersimpan di {OUTPUT}")

    r = report["zap_results"]
    print(f"\n{'='*60}")
    print(f"  RINGKASAN ZAP CONTROLLED SCAN")
    print(f"{'='*60}")
    print(f"  Total requests          {r['total_requests']}")
    print(f"  Total alerts (raw)      {r['total_alerts_raw']}")
    print(f"  SQLi alerts             {r['alerts_by_category']['sqli']}")
    print(f"  XSS alerts              {r['alerts_by_category']['xss']}")
    print(f"  Path injection          {r['alerts_by_category']['path']}")
    print(f"  Other alerts            {r['alerts_by_category']['other']}")
    print(f"  Requests per vuln       {r['requests_per_vulnerability']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
