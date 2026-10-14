import json
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path("rl_pentest/results")
QTABLE_DIR = Path("rl_pentest/qtable")

QL_SUMMARY = RESULTS_DIR / "summary_ql.json"
QL_LOG = RESULTS_DIR / "log_ql.csv"
ZAP_LIVE_REPORT = RESULTS_DIR / "zap_report.json"
ZAP_CONTROLLED_REPORT = RESULTS_DIR / "zap_controlled_report.json"
QTABLE_FILE = QTABLE_DIR / "q_table.json"
COMPARISON_OUTPUT = Path("zap_comparison_report.json")

SHARED_ENDPOINT_NAMES = ("/rest/products/search?q=", "/ftp/")
SHARED_ENDPOINTS = {0, 1}

LITERATURE_BENCHMARK = {
    "source": "Sahu et al., 2023 - OWASP ZAP full scan Juice Shop (50+ endpoints)",
    "total_requests": 1500,
    "vulnerabilities_found": 12,
    "false_positives": 3,
}


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _req_per_vuln(total_requests, total_vulns):
    return round(total_requests / total_vulns, 2) if total_vulns else float("inf")


def summarize_log(log_df, endpoint_set=None):
    if log_df is None or log_df.empty:
        return None
    sub = log_df
    if endpoint_set is not None:
        sub = sub[sub["endpoint_index"].isin(endpoint_set)]
    counts = {
        "SQL Injection": int((sub["vulnerability"] == "sqli").sum()),
        "Reflected XSS": int((sub["vulnerability"] == "xss").sum()),
        "Fuzzing Anomaly": int((sub["vulnerability"] == "fuzzing").sum()),
    }
    total = sum(counts.values())
    return {
        "total_requests": int(len(sub)),
        "total_vulnerabilities": total,
        "vuln_types": counts,
        "requests_per_vulnerability": _req_per_vuln(int(len(sub)), total),
    }


def summarize_summary(summary):
    total_vulns = sum(
        summary.get(key, 0) for key in ("sql_injection", "reflected_xss", "fuzzing_anomaly")
    )
    total_requests = summary.get("total_requests", 0)
    return {
        "total_requests": total_requests,
        "total_vulnerabilities": total_vulns,
        "vuln_types": {
            "SQL Injection": summary.get("sql_injection", 0),
            "Reflected XSS": summary.get("reflected_xss", 0),
            "Fuzzing Anomaly": summary.get("fuzzing_anomaly", 0),
        },
        "requests_per_vulnerability": _req_per_vuln(total_requests, total_vulns),
    }


def compute_comparison(ql_summary, ql_full, ql_shared, zap, qtable, zap_source):
    ql_primary = ql_shared if ql_shared is not None else ql_full

    zap = zap or {}
    zap_reqs = zap.get("total_requests", 0)
    zap_active_scan_reqs = (zap.get("requests_by_phase") or {}).get("active_scan", None)
    zap_other_reqs = (zap.get("requests_by_phase") or {}).get("spider_plus_access", None)

    # Prioritas: hitungan kerentanan yang sudah ter-filter risiko (>= Medium)
    if "vulnerabilities_by_category" in zap:
        vuln_map = zap["vulnerabilities_by_category"]
        zap_display = {
            "SQL Injection": vuln_map.get("sqli", 0),
            "Reflected XSS": vuln_map.get("xss", 0),
            "Path Injection": vuln_map.get("path", 0),
        }
        zap_scope_note = "hanya alert kategori sqli/xss/path berisiko High/Medium"
    else:
        zap_alerts = zap.get("alerts_by_category", {})
        zap_display = {
            "SQL Injection": zap_alerts.get("sqli", 0),
            "Reflected XSS": zap_alerts.get("xss", 0),
            "Path Injection": zap_alerts.get("path", 0),
        }
        zap_scope_note = "alert kategori sqli/xss/path (tanpa filter risiko)"

    zap_total = sum(zap_display.values())
    zap_req_per_vuln = _req_per_vuln(zap_reqs, zap_total)

    primary_rpv = ql_primary["requests_per_vulnerability"]

    if zap_req_per_vuln != float("inf") and primary_rpv not in (0, float("inf")):
        efficiency_ratio = round(zap_req_per_vuln / primary_rpv, 1)
        if efficiency_ratio >= 1:
            efficiency_text = f"Q-Learning {efficiency_ratio}x lebih efisien per request."
        else:
            efficiency_text = "ZAP lebih efisien per request."
    else:
        efficiency_text = "Rasio efisiensi tidak dapat dihitung (salah satu sisi tidak menemukan kerentanan)."

    if ql_shared is not None:
        scope_text = (
            "Perbandingan efisiensi utama memakai 2 endpoint yang sama "
            "(/rest/products/search?q= dan /ftp/) agar adil (apples-to-apples). "
            "ZAP controlled scan hanya memindai kedua endpoint ini, "
            "sedangkan Q-Learning dilatih pada 8 endpoint."
        )
    else:
        scope_text = (
            "Log Q-Learning tidak tersedia untuk pembatasan endpoint; "
            "perbandingan memakai seluruh 8 endpoint training "
            "(ZAP hanya memindai 2 endpoint) - lihat limitations."
        )

    efficiency_comparison = (
        f"Q-Learning ({ql_primary['total_requests']} request) mendeteksi "
        f"{ql_primary['total_vulnerabilities']} kerentanan "
        f"({primary_rpv} request/vuln). "
        f"ZAP ({zap_reqs} request) mendeteksi {zap_total} kerentanan "
        f"({zap_req_per_vuln} request/vuln). "
        + efficiency_text
    )

    if ql_shared is not None:
        active_note = (
            f"ZAP memakai {zap_reqs} request (spider+access {zap_other_reqs}, "
            f"active scan {zap_active_scan_reqs}) pada 2 URL."
            if zap_active_scan_reqs is not None
            else f"ZAP memakai {zap_reqs} request termasuk spider dan active scan pada 2 URL."
        )
        coverage = (
            f"Q-Learning dilatih pada 8 endpoint dengan 15 payload (total 120 aksi, "
            f"{ql_full['total_requests']} request). Subset 2 endpoint bersama yang sama "
            f"dengan ZAP: {ql_shared['total_requests']} request, "
            f"{ql_shared['total_vulnerabilities']} kerentanan. "
            f"{active_note} "
            "ZAP unggul dalam variasi attack; Q-Learning unggul dalam efisiensi per request."
        )
    else:
        coverage = (
            f"Q-Learning dilatih pada 8 endpoint dengan 15 payload (total 120 aksi, "
            f"{ql_full['total_requests']} request, {ql_full['total_vulnerabilities']} kerentanan). "
            f"ZAP memakai {zap_reqs} request pada 2 URL saja. Karena log Q-Learning tidak tersisa, "
            "subset 2 endpoint tidak dapat dihitung kembali; bandingkan dengan hati-hati."
        )

    conclusion = (
        f"Pada 2 endpoint yang sama, Q-Learning mendeteksi {ql_primary['total_vulnerabilities']} "
        f"kerentanan dalam {ql_primary['total_requests']} request ({primary_rpv} req/vuln), "
        f"sementara ZAP mendeteksi {zap_total} dalam {zap_reqs} request "
        f"({zap_req_per_vuln} req/vuln). {efficiency_text} "
        "Q-Learning cocok untuk continuous pentesting yang adaptif dan efisien; "
        "ZAP cocok untuk comprehensive one-time scanning."
    )

    ql_summary = ql_summary or {}
    comparison = {
        "comparison": "Q-Learning vs OWASP ZAP",
        "zap_source": zap_source,
        "scope_note": scope_text,
        "ql_results": {
            "scope": "8 endpoint (seluruh training)",
            "total_requests": ql_full["total_requests"],
            "total_vulnerabilities": ql_full["total_vulnerabilities"],
            "vuln_types": ql_full["vuln_types"],
            "requests_per_vulnerability": ql_full["requests_per_vulnerability"],
            "cumulative_reward": ql_summary.get("cumulative_reward", 0),
            "states_visited": ql_summary.get("states_visited") or (len(qtable) if qtable else 0),
            "training_duration_seconds": ql_summary.get("training_duration_seconds"),
            "verification_requests": ql_summary.get("verification_requests", 0),
            "baseline_probe_requests": ql_summary.get("baseline_probe_requests", 0),
            "total_requests_with_verification": ql_summary.get(
                "total_requests_with_verification", ql_full["total_requests"]
            ),
        },
        "ql_shared_2_endpoint": ql_shared,
        "zap_results": {
            "source": zap_source,
            "total_requests": zap_reqs,
            "active_scan_requests": zap_active_scan_reqs,
            "total_alerts_raw": zap.get("total_alerts_raw", 0),
            "total_vulnerabilities": zap_total,
            "alerts_by_category": {
                "SQL Injection": zap_display["SQL Injection"],
                "Reflected XSS": zap_display["Reflected XSS"],
                "Path Injection": zap_display["Path Injection"],
                "Other": sum((zap.get("alerts_by_category") or {}).get(k, 0) for k in ("sqli", "xss", "path", "other")),
            },
            "vuln_counting_scope": zap_scope_note,
            "requests_per_vulnerability": zap_req_per_vuln,
            "duration_seconds": zap.get("duration_seconds"),
        },
        "analysis": {
            "efficiency_comparison": efficiency_comparison,
            "adaptivity": (
                "Q-Learning belajar dari pengalaman (epsilon decay, Q-table update). "
                "Semakin banyak episode, semakin tepat pemilihan payload. "
                "ZAP tidak memiliki mekanisme belajar - setiap scan statis."
            ),
            "coverage": coverage,
            "conclusion": conclusion,
        },
        "limitations": [
            "ZAP controlled scan memindai 2 endpoint dengan request spider + active scan; Q-Learning memakai payload terarah, sehingga metrik request tidak sebanding langsung.",
            "Kerentanan ZAP yang dihitung hanya alert kategori sqli/xss/path berisiko High/Medium; alert lainnya (CSP header, cross-domain misconfiguration, teknologi, timestamp) tidak dihitung karena berada di luar cakupan analyzer.",
            "Deteksi Q-Learning berbasis response analyzer dengan verifikasi kontrol-diferensial (benign + mutant) dan eksekusi DOM di browser headless untuk XSS.",
            "total_requests Q-Learning hanya menghitung request payload; request verifikasi benign (verification_requests) dan probe baseline (baseline_probe_requests) dicatat terpisah.",
            "'requests_per_vulnerability' dan 'vuln_hit_rate' mengikuti definisi Tugas Akhir (vuln_hit_rate = total_vuln / total_requests), bukan metrik Precision/Recall ML. Metrik detektor yang tidak circular (precision/recall/F1 vs oracle manual) dihasilkan oleh benchmark_detector.py, terpisah dari perbandingan ini.",
            "Seluruh metrik Q-Learning di laporan ini bersifat in-sample: dihitung dari episode yang sama dengan fase training, bukan dari evaluasi held-out.",
        ],
    }
    return comparison


def format_table(ql_r, ql_shared, zap_r, comparison):
    lines = [
        f"{'=' * 72}",
        "  PERBANDINGAN: Q-LEARNING vs OWASP ZAP",
        f"{'=' * 72}",
        f"  {'Metrik':<34} {'Q-Learning':>15} {'ZAP':>15}",
        f"  {'-' * 64}",
        f"  {'Total HTTP Requests (payload)':<34} {ql_r['total_requests']:>15} {zap_r['total_requests']:>15}",
        f"  {'Total (payload+verif+probe)':<34} {ql_r['total_requests_with_verification']:>15}",
        f"  {'Total Vulnerabilities':<34} {ql_r['total_vulnerabilities']:>15} {zap_r['total_vulnerabilities']:>15}",
        f"  {'SQL Injection':<34} {ql_r['vuln_types']['SQL Injection']:>15} {zap_r['alerts_by_category']['SQL Injection']:>15}",
        f"  {'Reflected XSS':<34} {ql_r['vuln_types']['Reflected XSS']:>15} {zap_r['alerts_by_category']['Reflected XSS']:>15}",
        f"  {'Fuzzing / Path Injection':<34} {ql_r['vuln_types']['Fuzzing Anomaly']:>15} {zap_r['alerts_by_category']['Path Injection']:>15}",
        f"  {'Requests per Vulnerability':<34} {ql_r['requests_per_vulnerability']:>15} {zap_r['requests_per_vulnerability']:>15}",
    ]
    if zap_r.get("duration_seconds"):
        lines += [
            f"  {'Duration (seconds)':<34} {ql_r.get('training_duration_seconds','') or '-':>15} {zap_r['duration_seconds']:>15.1f}",
        ]
    if ql_shared is not None:
        lines += [
            f"  {'-' * 64}",
            "  SUBSET 2 ENDPOINT YANG SAMA (apples-to-apples)",
            f"  {'Total Requests':<34} {ql_shared['total_requests']:>15} {zap_r['total_requests']:>15}",
            f"  {'Total Vulnerabilities':<34} {ql_shared['total_vulnerabilities']:>15} {zap_r['total_vulnerabilities']:>15}",
            f"  {'Requests per Vulnerability':<34} {ql_shared['requests_per_vulnerability']:>15} {zap_r['requests_per_vulnerability']:>15}",
        ]
    lines += [f"{'=' * 72}"]
    scope = zap_r.get("vuln_counting_scope")
    if scope:
        lines.append(f"  Catatan: kerentanan ZAP = {scope}")
    return "\n".join(lines)


def main():
    ql_summary = load_json(QL_SUMMARY)
    ql_log_df = pd.read_csv(QL_LOG) if QL_LOG.exists() else None

    if ql_summary is None and (ql_log_df is None or ql_log_df.empty):
        print("[-] Data hasil Q-Learning tidak ditemukan (summary_ql.json / log_ql.csv).")
        print("    Jalankan 'python rl_pentest\\main.py' terlebih dahulu dengan OWASP Juice Shop aktif.")
        return

    if ZAP_CONTROLLED_REPORT.exists():
        print("[+] Menggunakan ZAP Controlled Scan report (2 endpoint)")
        zap = load_json(ZAP_CONTROLLED_REPORT) or {}
        zap_data = zap.get("zap_results", zap)
        zap_source = "ZAP Controlled Scan (2 endpoint)"
    elif ZAP_LIVE_REPORT.exists():
        print("[+] Menggunakan ZAP Live Scan report")
        zap = load_json(ZAP_LIVE_REPORT) or {}
        zap_data = zap.get("zap_results", zap)
        zap_source = "ZAP Live Scan (full)"
    else:
        print("[+] ZAP report tidak ditemukan; menggunakan literatur (Sahu et al., 2023)")
        zap_source = "Literatur - Sahu et al., 2023 (ZAP full scan)"
        zap_data = {
            "total_requests": LITERATURE_BENCHMARK["total_requests"],
            "total_alerts_raw": LITERATURE_BENCHMARK["vulnerabilities_found"],
            "alerts_by_category": {
                "sqli": 0,
                "xss": 0,
                "path": 0,
                "other": LITERATURE_BENCHMARK["vulnerabilities_found"],
            },
            "requests_per_vulnerability": _req_per_vuln(
                LITERATURE_BENCHMARK["total_requests"], LITERATURE_BENCHMARK["vulnerabilities_found"]
            ),
        }

    ql_full = summarize_log(ql_log_df) or summarize_summary(ql_summary or {})
    ql_shared = summarize_log(ql_log_df, SHARED_ENDPOINTS)
    qtable = load_json(QTABLE_FILE)

    comparison = compute_comparison(ql_summary, ql_full, ql_shared, zap_data, qtable, zap_source)

    COMPARISON_OUTPUT.write_text(json.dumps(comparison, indent=2))
    print(f"[+] Laporan tersimpan di {COMPARISON_OUTPUT}")

    print(format_table(comparison["ql_results"], comparison["ql_shared_2_endpoint"],
                       comparison["zap_results"], comparison))


if __name__ == "__main__":
    main()