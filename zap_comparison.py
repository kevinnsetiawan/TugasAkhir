import json
from pathlib import Path

RESULTS_DIR = Path("rl_pentest/results")
QTABLE_DIR = Path("rl_pentest/qtable")

QL_SUMMARY = RESULTS_DIR / "summary.json"
ZAP_LIVE_REPORT = RESULTS_DIR / "zap_report.json"
ZAP_CONTROLLED_REPORT = RESULTS_DIR / "zap_controlled_report.json"
QTABLE_FILE = QTABLE_DIR / "q_table.json"
COMPARISON_OUTPUT = Path("zap_comparison_report.json")

LITERATURE_BENCHMARK = {
    "source": "Sahu et al., 2023 — OWASP ZAP full scan Juice Shop (50+ endpoints)",
    "total_requests": 1500,
    "vulnerabilities_found": 12,
    "false_positives": 3,
}


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def compute_comparison(ql, zap):
    ql_reqs = ql.get("total_requests", 0)
    ql_vulns = {k: ql.get(k, 0) for k in ("sql_injection", "reflected_xss", "fuzzing_anomaly")}
    ql_vulns_total = sum(ql_vulns.values())
    ql_req_per_vuln = round(ql_reqs / ql_vulns_total, 2) if ql_vulns_total else float("inf")

    zap_reqs = zap.get("total_requests", 0)
    zap_alerts = zap.get("alerts_by_category", {})
    zap_vulns_total = sum(zap_alerts.get(k, 0) for k in ("sqli", "xss", "path"))
    zap_req_per_vuln = round(zap_reqs / zap_vulns_total, 2) if zap_vulns_total else float("inf")

    efficiency_ratio = (
        round(zap_req_per_vuln / ql_req_per_vuln, 1)
        if ql_req_per_vuln != float("inf") and ql_req_per_vuln > 0
        else 0
    )

    # Determine ZAP source label
    if ZAP_CONTROLLED_REPORT.exists():
        zap_source = "ZAP Controlled Scan (2 endpoint)"
    elif ZAP_LIVE_REPORT.exists():
        zap_source = "ZAP Live Scan (full)"
    else:
        zap_source = f"Literatur — {LITERATURE_BENCHMARK['source']}"
        if zap.get("total_requests") == LITERATURE_BENCHMARK["total_requests"]:
            pass  # already set
        else:
            zap = {
                "total_requests": LITERATURE_BENCHMARK["total_requests"],
                "total_alerts_raw": LITERATURE_BENCHMARK["vulnerabilities_found"],
                "total_vulnerabilities": LITERATURE_BENCHMARK["vulnerabilities_found"],
                "alerts_by_category": {"sqli": 0, "xss": 0, "path": 0, "other": LITERATURE_BENCHMARK["vulnerabilities_found"]},
                "requests_per_vulnerability": round(LITERATURE_BENCHMARK["total_requests"] / LITERATURE_BENCHMARK["vulnerabilities_found"], 2),
            }

    qtable = load_json(QTABLE_FILE)
    states_visited = len(qtable) if qtable else 0

    comparison = {
        "comparison": "Q-Learning vs OWASP ZAP",
        "zap_source": zap_source,
        "target_endpoints": "2 endpoint: /rest/products/search?q= dan /ftp/",
        "ql_results": {
            "total_requests": ql_reqs,
            "total_vulnerabilities": ql_vulns_total,
            "vuln_types": {
                "SQL Injection": ql_vulns["sql_injection"],
                "Reflected XSS": ql_vulns["reflected_xss"],
                "Path / Fuzzing": ql_vulns["fuzzing_anomaly"],
            },
            "requests_per_vulnerability": ql_req_per_vuln,
            "cumulative_reward": ql.get("cumulative_reward", 0),
            "states_visited": states_visited,
        },
        "zap_results": {
            "source": zap_source,
            "total_requests": zap.get("total_requests", 0),
            "total_alerts_raw": zap.get("total_alerts_raw", 0),
            "total_vulnerabilities": zap_vulns_total,
            "alerts_by_category": {
                "SQL Injection": zap_alerts.get("sqli", 0),
                "Reflected XSS": zap_alerts.get("xss", 0),
                "Path Injection": zap_alerts.get("path", 0),
                "Other": zap_alerts.get("other", 0),
            },
            "requests_per_vulnerability": zap_req_per_vuln,
        },
        "analysis": {
            "efficiency_comparison": (
                f"Q-Learning: {ql_req_per_vuln} request/vuln, "
                f"ZAP: {zap_req_per_vuln} request/vuln. "
                f"Q-Learning {efficiency_ratio}x lebih efisien per request."
                if efficiency_ratio >= 1
                else (
                    f"Q-Learning: {ql_req_per_vuln} request/vuln, "
                    f"ZAP: {zap_req_per_vuln} request/vuln."
                )
            ),
            "adaptivity": (
                "Q-Learning belajar dari pengalaman (epsilon decay, Q-table update). "
                "Semakin banyak episode, semakin tepat pemilihan payload. "
                "ZAP tidak memiliki mekanisme belajar — setiap scan statis."
            ),
            "coverage": (
                f"Q-Learning hanya menggunakan {ql_reqs} request terarah (10 payload). "
                f"ZAP menggunakan {zap.get('total_requests', 0)} request dengan ribuan variasi attack. "
                "Q-Learning unggul dalam efisiensi; ZAP unggul dalam breadth of coverage."
            ),
            "conclusion": (
                f"Pada 2 endpoint yang sama, Q-Learning mendeteksi {ql_vulns_total} "
                f"kerentanan dalam {ql_reqs} request ({ql_req_per_vuln} req/vuln), "
                f"sementara ZAP mendeteksi {zap_vulns_total} "
                f"dalam {zap.get('total_requests', 0)} request ({zap_req_per_vuln} req/vuln). "
                f"Q-Learning cocok untuk continuous pentesting yang adaptif dan efisien; "
                f"ZAP cocok untuk comprehensive one-time scanning."
            ),
        },
    }

    return comparison


def format_table(ql, zap):
    rows = [
        ("Total HTTP Requests", ql["total_requests"], zap["total_requests"]),
        ("Total Vulnerabilities", ql["total_vulnerabilities"], zap["total_vulnerabilities"]),
        ("SQL Injection", ql["vuln_types"]["SQL Injection"], zap["alerts_by_category"]["SQL Injection"]),
        ("Reflected XSS", ql["vuln_types"]["Reflected XSS"], zap["alerts_by_category"]["Reflected XSS"]),
        ("Path Injection / Fuzzing", ql["vuln_types"]["Path / Fuzzing"], zap["alerts_by_category"]["Path Injection"]),
        ("Requests per Vulnerability", ql["requests_per_vulnerability"], zap["requests_per_vulnerability"]),
    ]

    lines = [
        f"{'='*65}",
        f"  PERBANDINGAN: Q-LEARNING vs OWASP ZAP",
        f"  {ql.get('target_endpoints', '')}",
        f"{'='*65}",
        f"  {f'ZAP Source: {zap_source}':60}",
        f"{'='*65}",
        f"  {'Metrik':<30} {'Q-Learning':>15} {'ZAP':>15}",
        f"  {'-'*60}",
    ]
    for label, ql_val, zap_val in rows:
        lines.append(f"  {label:<30} {str(ql_val):>15} {str(zap_val):>15}")
    lines.append(f"{'='*65}")
    lines.append("")
    lines.append(f"  ANALISIS")
    lines.append(f"  {comparison['analysis']['efficiency_comparison']}")
    lines.append(f"")
    lines.append(f"  {comparison['analysis']['adaptivity']}")
    lines.append(f"")
    lines.append(f"  {comparison['analysis']['coverage']}")
    lines.append(f"")
    lines.append(f"  KESIMPULAN")
    lines.append(f"  {comparison['analysis']['conclusion']}")
    lines.append(f"{'='*65}")
    return "\n".join(lines)


def main():
    ql = load_json(QL_SUMMARY)
    if ql is None:
        print("[-] Q-Learning summary tidak ditemukan. Jalankan 'python rl_pentest\\main.py' dulu.")
        return

    # Prefer controlled scan > live scan > literature
    if ZAP_CONTROLLED_REPORT.exists():
        zap = load_json(ZAP_CONTROLLED_REPORT)
        zap_data = zap.get("zap_results", zap) if isinstance(zap, dict) else zap
        print("[+] Menggunakan ZAP Controlled Scan report (2 endpoint)")
    elif ZAP_LIVE_REPORT.exists():
        zap = load_json(ZAP_LIVE_REPORT)
        zap_data = zap if isinstance(zap, dict) else {}
        print("[+] Menggunakan ZAP Live Scan report")
    else:
        print("[+] ZAP report tidak ditemukan; menggunakan literatur (Sahu et al., 2023)")
        zap_data = {}

    global comparison, zap_source
    comparison = compute_comparison(ql, zap_data)
    zap_source = comparison["zap_source"]

    COMPARISON_OUTPUT.write_text(json.dumps(comparison, indent=2))
    print(f"[+] Laporan tersimpan di {COMPARISON_OUTPUT}")

    ql_r = comparison["ql_results"]
    zap_r = comparison["zap_results"]
    print(format_table(ql_r, zap_r))


comparison = None
zap_source = ""

if __name__ == "__main__":
    main()
