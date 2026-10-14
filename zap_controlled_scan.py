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

# Kerentanan "aktif" yang dihitung setara dengan kategori temuan Q-Learning
# (sqli / xss / fuzzing-path traversal). Alert di luar kategori ini
# (mis. header/CSP, cross-domain misconfiguration, teknologi, timestamp)
# TIDAK dihitung sebagai kerentanan pada perbandingan.
# Hanya alert berisiko High/Medium yang dihitung agar tidak menggelembungkan
# angka ZAP dengan temuan berskala Informational (mis. "Modern Web Application").
RELEVANT_CATEGORIES = {"sqli", "xss", "path"}
RELEVANT_RISKS = {"High", "Medium"}


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


def count_messages(baseurl: str) -> int:
    """Menghitung total pesan HTTP yang direkam ZAP untuk baseurl tertentu."""
    total = 0
    page_size = 100
    for start in range(0, 20000, page_size):
        result = zap_api(
            "core/view/messages",
            {"baseurl": baseurl, "start": start, "count": page_size},
        )
        if result is None:
            break
        msgs = result.get("messages") or []
        total += len(msgs)
        if len(msgs) < page_size:
            break
    return total


def classify_zap_alert(alert: dict) -> str:
    """Klasifikasi alert ZAP berbasis NAMA alert (bukan keyword bebas pada
    evidence/attack) agar hal seperti 'Modern Web Application' tidak terdeteksi
    sebagai XSS."""
    name = (alert.get("alert") or "").lower()
    if not name:
        name = str(alert.get("alertRef") or "").lower()

    # --- SQL Injection ---
    if "sql injection" in name:
        return "sqli"
    if "sql" in name and any(k in name for k in ("error", "query", "blind", "db")):
        return "sqli"
    if name and name.isdigit() and name in {"40018", "40019", "40020", "40021", "90018"}:
        return "sqli"

    # --- Cross-Site Scripting (Reflected / DOM / Persistent) ---
    if "xss" in name or "cross site scripting" in name:
        return "xss"
    if name and name.isdigit() and name in {"40012", "40014", "40016", "40017", "40026", "90027"}:
        return "xss"

    # --- Path Traversal / File Inclusion / Directory Browsing ---
    if any(
        k in name
        for k in (
            "path traversal",
            "directory traversal",
            "local file inclusion",
            "remote file inclusion",
            "directory browsing",
            "file include",
        )
    ):
        return "path"
    if name and name.isdigit() and name in {"40001", "40025", "40028", "90017"}:
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
    print(f"[+] Endpoint: {len(CONTROLLED_URLS)} URL")
    print(f"[+] Aturan penghitungan kerentanan: alert kategori sqli/xss/path berisiko {sorted(RELEVANT_RISKS)}\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    initial_count = count_messages(TARGET)
    print(f"[*] Pesan HTTP awal di session: {initial_count}")

    requests_by_phase = {"spider_plus_access": 0, "active_scan": 0, "total": 0}
    timing_by_url = []
    scan_started = time.time()

    for url in CONTROLLED_URLS:
        entry = {"url": url}

        # --- Step 1: Access URL (masukkan ke site tree ZAP) ---
        zap_api("core/action/accessUrl", {"url": url})

        # --- Step 2: Spider ---
        t0 = time.time()
        spider_result = zap_api("spider/action/scan", {"url": url, "maxChildren": 2})
        if spider_result and spider_result.get("scan"):
            spider_id = spider_result.get("scan")
            wait_for_scan("spider", spider_id)
            print()
        entry["spider_seconds"] = round(time.time() - t0, 2)
        count_after_spider = count_messages(TARGET)
        entry["requests_spider_plus_access"] = max(count_after_spider - initial_count, 0)

        # --- Step 3: Active scan ---
        t0 = time.time()
        result = zap_api("ascan/action/scan", {"url": url, "recurse": "false"})
        scan_id = result.get("scan") if result else None
        if scan_id:
            wait_for_scan("ascan", scan_id)
            print()
        entry["active_scan_seconds"] = round(time.time() - t0, 2) if scan_id else None
        count_after_ascan = count_messages(TARGET)
        entry["requests_active_scan"] = max(count_after_ascan - count_after_spider, 0)

        requests_by_phase["spider_plus_access"] += entry["requests_spider_plus_access"]
        requests_by_phase["active_scan"] += entry["requests_active_scan"]
        timing_by_url.append(entry)
        initial_count = count_after_ascan

    requests_by_phase["total"] = requests_by_phase["spider_plus_access"] + requests_by_phase["active_scan"]

    print("\n[*] Mengambil hasil alerts dari ZAP...")
    alerts_result = zap_api("core/view/alerts", {"baseurl": TARGET})
    if alerts_result is None:
        print("[-] Gagal mengambil alerts")
        return

    raw_alerts = alerts_result.get("alerts", [])

    categorized = {"sqli": [], "xss": [], "path": [], "other": []}
    for alert in raw_alerts:
        cat = classify_zap_alert(alert)
        categorized[cat].append(alert)

    alerts_by_category = {cat: len(alerts) for cat, alerts in categorized.items()}
    # Kerentanan relevan = High/Medium pada kategori sqli/xss/path (setara Q-Learning)
    vulnerabilities_by_category = {
        cat: sum(
            1
            for a in alerts
            if a.get("risk") in RELEVANT_RISKS
        )
        for cat, alerts in categorized.items()
        if cat in RELEVANT_CATEGORIES
    }
    total_vulnerabilities = sum(vulnerabilities_by_category.values())

    elapsed_total = round(time.time() - scan_started, 2)

    report = {
        "metadata": {
            "tool": "OWASP ZAP Controlled Scan",
            "target": TARGET,
            "endpoints_scanned": CONTROLLED_URLS,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "zap_version_requested": (zap_api("core/view/version") or {}).get("version"),
        },
        "zap_results": {
            "total_requests": requests_by_phase["total"],
            "requests_by_phase": requests_by_phase,
            "total_alerts_raw": len(raw_alerts),
            "total_vulnerabilities": total_vulnerabilities,
            "alerts_by_category": alerts_by_category,
            "vulnerabilities_by_category": vulnerabilities_by_category,
            "vulnerability_counting_rule": f"Hanya alert kategori sqli/xss/path berisiko {sorted(RELEVANT_RISKS)}",
            "requests_per_vulnerability": round(
                requests_by_phase["total"] / total_vulnerabilities, 2
            ) if total_vulnerabilities else float("inf"),
            "risk_breakdown": {
                "high": sum(1 for a in raw_alerts if a.get("risk") == "High"),
                "medium": sum(1 for a in raw_alerts if a.get("risk") == "Medium"),
                "low": sum(1 for a in raw_alerts if a.get("risk") == "Low"),
                "informational": sum(1 for a in raw_alerts if a.get("risk") == "Informational"),
            },
            "duration_seconds": elapsed_total,
        },
        "timing_by_url": timing_by_url,
        "alerts_categorized": {
            cat: [
                {
                    "name": a.get("alert"),
                    "alertRef": a.get("alertRef"),
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
    print(f"  Total requests          {r['total_requests']}  (spider+access {requests_by_phase['spider_plus_access']} | ascan {requests_by_phase['active_scan']})")
    print(f"  Total alerts (raw)      {r['total_alerts_raw']}")
    print(f"  SQLi (High/Medium)      {r['vulnerabilities_by_category'].get('sqli', 0)}")
    print(f"  XSS (High/Medium)       {r['vulnerabilities_by_category'].get('xss', 0)}")
    print(f"  Path inj (High/Medium)  {r['vulnerabilities_by_category'].get('path', 0)}")
    print(f"  Other alerts            {r['alerts_by_category'].get('other', 0)}")
    print(f"  Requests per vuln       {r['requests_per_vulnerability']}")
    print(f"  Durasi total            {r['duration_seconds']} detik")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()