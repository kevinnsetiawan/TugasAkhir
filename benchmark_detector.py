"""Benchmark mandiri kualitas detektor (bukan circular).

Masalah yang diselesaikan skrip ini
-----------------------------------
`ResponseAnalyzer._detect_vulnerability` dipakai untuk dua hal sekaligus:
memberi reward ke agent (reward_system.py) DAN menghitung "kerentanan yang
ditemukan" pada metrics.py. Angka akurasi yang dihitung dari log training
selalu circular, karena tidak ada oracle yang benar-benar independen.

Skrip ini memutus lingkaran tersebut: agent RL tidak dipakai sama sekali di
sini. `ResponseAnalyzer` dijalankan langsung ke SELURUH ruang aksi
(8 endpoint x 15 payload = 120 request), lalu hasilnya dibandingkan dengan
label ground truth yang dibuat manual (lihat ground_truth.py). Angka
precision/recall/F1 di sini adalah angka kualitas detektor yang sesungguhnya,
bukan echo dari reward.

Verifikasi yang dipakai sama dengan yang dipakai saat training, agar benchmark
menilai sistem yang benar-benar berjalan:
  - sqli/fuzzing : kontrol-diferensial (benign + mutant ternetralkan)
  - xss          : eksekusi DOM di headless Chromium (bukan refleksi HTTP)

Pemakaian:
    python benchmark_detector.py
    python benchmark_detector.py --no-browser
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "rl_pentest"))

import cyber_output as cyber
from analyzer.browser_verifier import BrowserVerifier
from analyzer.response_analyzer import ResponseAnalyzer
from config import BASE_URL, ENDPOINTS, PAYLOADS_FILE, REQUEST_TIMEOUT, XSS_PAGES
from engine.http_client import HTTPClient
from engine.payload_generator import PayloadGenerator
from ground_truth import expected_label, ground_truth_summary
from training_loop import probe_endpoint_baselines, verify_vulnerability, verify_xss_in_browser

VULN_CLASSES = ("sqli", "xss", "fuzzing")


def evaluate_action(client, analyzer, payload_generator, browser_verifier, action_index):
    """Kirim satu aksi, terverifikasi, dan kembalikan (predicted, verified).

    Percabangan ini HARUS meniru `run_episode` (training_loop.py) persis, kalau
    tidak benchmark tidak lagi menilai sistem yang benar-benar berjalan.

    Perbedaan penting yang mudah terlewat: untuk XSS, `run_episode` MELOMPATI
    deteksi berbasis HTTP dan langsung ke browser. Alasannya /rest/track-order
    membalas JSON, bukan HTML, sehingga `served_as_html` bernilai False dan
    `analyze()` selalu mengembalikan "none" - padahal vektornya benar-benar
    dieksekusi di halaman /#/track-result. Benchmark yang keluar terlalu awal
    di sini akan melaporkan recall XSS = 0 secara palsu.
    """
    payload_entry, endpoint_index = payload_generator.get_payload_and_endpoint(action_index)
    payload_text = payload_entry["payload"]
    payload_category = payload_entry.get("category", "")
    surface = client.surface_of(endpoint_index)
    xss_page = (XSS_PAGES or {}).get(endpoint_index)

    try:
        response = client.send_payload(payload_text, endpoint_index=endpoint_index)
    except RuntimeError:
        return "none", False

    analysis = analyzer.analyze(
        response, payload_text, endpoint_index=endpoint_index, surface=surface
    )

    # Jalur XSS: sama seperti run_episode, ketentuannya berdasarkan kategori
    # payload dan keberadaan halaman SPA, BUKAN berdasarkan prediksi HTTP.
    if payload_category == "xss" and xss_page:
        executed = verify_xss_in_browser(browser_verifier, xss_page, payload_text)
        return ("xss" if executed else "none"), executed

    predicted = analysis.get("vulnerability", "none")
    if predicted == "none":
        return "none", False

    verified, _ = verify_vulnerability(
        client, analyzer, payload_text, endpoint_index, predicted
    )
    return (predicted if verified else "none"), verified


def confusion_counts(rows):
    tp = fp = fn = tn = unknown = 0
    for row in rows:
        truth, predicted = row["truth"], row["predicted"]
        if truth == "unknown":
            unknown += 1
            continue
        if truth != "none" and predicted == truth:
            tp += 1
        elif truth != "none" and predicted != truth:
            fn += 1
        elif truth == "none" and predicted != "none":
            fp += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "unlabelled": unknown}


def safe_div(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def prf(tp, fp, fn):
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    if precision and recall and (precision + recall):
        f1 = round(2 * precision * recall / (precision + recall), 4)
    else:
        f1 = 0.0 if (tp + fp + fn) else None
    return precision, recall, f1


def run_benchmark(include_browser=True):
    n_endpoints = len(ENDPOINTS)
    payload_generator = PayloadGenerator(PAYLOADS_FILE, n_endpoints=n_endpoints)
    client = HTTPClient(BASE_URL, endpoints=ENDPOINTS, timeout=REQUEST_TIMEOUT)
    analyzer = ResponseAnalyzer()
    browser_verifier = BrowserVerifier(BASE_URL) if include_browser else None
    n_actions = payload_generator.get_action_count()

    cyber.init()
    print("\n" + cyber.banner("Q-Learning").replace(
        "Reinforcement Learning Autonomous Web Pentest :: Q-Learning",
        "Detector Benchmark (no RL agent)"))
    cyber.info(f"TARGET       : {BASE_URL}")
    cyber.info(f"ACTION SPACE : {n_actions} ({n_endpoints} endpoint x {n_payloads(n_actions, n_endpoints)} payload)")
    cyber.info("AGENT        : TIDAK dipakai (tanpa RL, tanpa reward) - inilah yang membuat benchmark tidak circular")
    cyber.info(f"ORACLE       : ground_truth.py (label manual)")
    cyber.info("VERIFICATION : kontrol-diferensial + eksekusi DOM headless chromium")
    cyber.thinline()
    cyber.boot("probing endpoint baselines ...")
    probe_endpoint_baselines(client, analyzer)
    cyber.boot(f"evaluating all {n_actions} actions ...\n")

    rows = []
    started = time.monotonic()
    for action_index in range(n_actions):
        predicted, verified = evaluate_action(
            client, analyzer, payload_generator, browser_verifier, action_index
        )
        entry, endpoint_index = payload_generator.get_payload_and_endpoint(action_index)
        row = {
            "action_index": action_index,
            "action_name": f"{entry['name']}@ep{endpoint_index}",
            "endpoint_index": endpoint_index,
            "truth": expected_label(action_index, payload_generator.n_payloads),
            "predicted": predicted,
            "verified": verified,
        }
        rows.append(row)
        if row["truth"] != "unknown" and predicted != "none":
            marker = "OK " if predicted == row["truth"] else "FP "
            cyber.log(
                f"{marker} {row['action_name']:<24} truth={row['truth']:<8} pred={predicted}",
                "+" if marker == "OK " else "!",
                cyber.GREEN if marker == "OK " else cyber.RED,
            )
        if (action_index + 1) % 30 == 0:
            elapsed = time.monotonic() - started
            cyber.log(
                "evaluated %d/%d %s %.1fs"
                % (action_index + 1, n_actions, cyber.progress_bar(action_index + 1, n_actions), elapsed),
                "=", cyber.CYAN,
            )

    counts = confusion_counts(rows)
    precision, recall, f1 = prf(counts["tp"], counts["fp"], counts["fn"])
    duration = round(time.monotonic() - started, 2)

    report = {
        "note": (
            "Benchmark detektor TANPA agent RL. ResponseAnalyzer dibandingkan "
            "dengan oracle ground truth manual (ground_truth.py), sehingga tidak "
            "mengulang log training."
        ),
        "caveat": (
            "PERINGATAN INTERPRETASI: nilai perfect di sini DIJANGAN disajikan "
            "sebagai bukti detektor sempurna atau generalisasi. Konfirmasi manual "
            "memakai mekanisme yang sama dengan sistem (kontrol-diferensial + "
            "eksekusi DOM), sehingga kesepakatan oracle-detektor tidak "
            "independen penuh. Yang sah diklaim: nol false positive pada aksi "
            "berlabel negatif, konsistensi terhadap ground truth terkurasi, dan "
            "bahwa quality gate benar-benar menyaring kandidat. Skor 1.0 berarti "
            "detektor tidak salah pada ground truth ini - bukan berarti ia "
            "berpikir pada environment lain. Lihat docstring ground_truth.py."
        ),
        "target": BASE_URL,
        "n_actions": n_actions,
        "browser_verifier_used": bool(include_browser and browser_verifier
                                       and getattr(browser_verifier, "available", False)),
        "duration_seconds": duration,
        "ground_truth": ground_truth_summary(n_endpoints, payload_generator.n_payloads),
        "confusion_matrix": counts,
        "micro": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "specificity": safe_div(counts["tn"], counts["tn"] + counts["fp"]),
        },
        "per_class": {},
        "rows": rows,
    }
    for vuln_class in VULN_CLASSES:
        class_rows = [r for r in rows if r["truth"] == vuln_class]
        ctp = sum(1 for r in class_rows if r["predicted"] == vuln_class)
        cfp = sum(1 for r in rows if r["predicted"] == vuln_class and r["truth"] != vuln_class)
        cfn = len(class_rows) - ctp
        cprecision, crecall, cf1 = prf(ctp, cfp, cfn)
        report["per_class"][vuln_class] = {
            "support": len(class_rows),
            "tp": ctp, "fp": cfp, "fn": cfn,
            "precision": cprecision,
            "recall": crecall,
            "f1": cf1,
        }

    if browser_verifier:
        browser_verifier.close()
    return report


def n_payloads(n_actions, n_endpoints):
    return n_actions // n_endpoints if n_endpoints else 0


def print_report(report):
    counts = report["confusion_matrix"]
    micro = report["micro"]
    truth = report["ground_truth"]
    lines = [cyber.rule(), "  " + cyber.paint("=== CONFUSION MATRIX (detector vs ground truth manual) ===",
                                              cyber.BOLD, cyber.CYAN), cyber.thinline()]
    lines.append("  %s %s" % (cyber.paint("true positive  (TP)", cyber.BOLD, cyber.GREEN), counts["tp"]))
    lines.append("  %s %s" % (cyber.paint("false positive (FP)", cyber.BOLD, cyber.RED), counts["fp"]))
    lines.append("  %s %s" % (cyber.paint("false negative (FN)", cyber.BOLD, cyber.YELLOW), counts["fn"]))
    lines.append("  %s %s" % (cyber.paint("true negative  (TN)", cyber.BOLD, cyber.GREEN), counts["tn"]))
    if counts["unlabelled"]:
        lines.append("  %s %s" % (cyber.paint("unlabelled (unknown)", cyber.DIM, cyber.BLUE), counts["unlabelled"]))
    lines.append(cyber.thinline())
    lines.append("  %s %s" % (cyber.paint("precision".ljust(24), cyber.WHITE),
                              cyber.paint(str(micro["precision"]), cyber.GREEN)))
    lines.append("  %s %s" % (cyber.paint("recall".ljust(24), cyber.WHITE),
                              cyber.paint(str(micro["recall"]), cyber.GREEN)))
    lines.append("  %s %s" % (cyber.paint("f1".ljust(24), cyber.WHITE),
                              cyber.paint(str(micro["f1"]), cyber.GREEN)))
    lines.append("  %s %s" % (cyber.paint("specificity".ljust(24), cyber.WHITE),
                              cyber.paint(str(micro["specificity"]), cyber.GREEN)))
    lines.append(cyber.thinline())
    lines.append("  " + cyber.paint("per-class:", cyber.BOLD, cyber.CYAN))
    for vuln_class, stats in report["per_class"].items():
        lines.append("    %-10s support=%-3d P=%-7s R=%-7s F1=%-7s" % (
            vuln_class, stats["support"], stats["precision"], stats["recall"], stats["f1"]))
    lines.append(cyber.thinline())
    lines.append("  %s %s" % (cyber.paint("actions labelled".ljust(24), cyber.WHITE), truth["labelled_actions"]))
    lines.append("  %s %s" % (cyber.paint("confirmed positives".ljust(24), cyber.WHITE), truth["positives"]))
    lines.append(cyber.thinline())
    lines.append("  " + cyber.paint("PERINGATAN: skor perfect 1.0 TIDAK berarti detektor sempurna.", cyber.BOLD, cyber.YELLOW))
    lines.append("  " + cyber.paint("Konfirmasi manual memakai mekanisme yang sama dengan sistem,", cyber.DIM, cyber.YELLOW))
    lines.append("  " + cyber.paint("jadi ini mengukur konsistensi + nol false positive,", cyber.DIM, cyber.YELLOW))
    lines.append("  " + cyber.paint("BUKAN generalisasi. Sertakan catatan ini di tesis.", cyber.DIM, cyber.YELLOW))
    lines.append(cyber.rule())
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Benchmark detektor tanpa agent RL")
    parser.add_argument("--out", default=str(
        Path(__file__).resolve().parent / "rl_pentest" / "results" / "detector_benchmark.json"))
    parser.add_argument("--no-browser", action="store_true", help="lewati verifikasi DOM (XSS jadi prediksi HTTP saja)")
    args = parser.parse_args()

    report = run_benchmark(include_browser=not args.no_browser)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report)
    cyber.ok(f"benchmark report saved -> {out_path}")
    print()


if __name__ == "__main__":
    main()
