import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "rl_pentest")

from config import ENDPOINTS  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "rl_pentest" / "results"
QTABLE_DIR = ROOT / "rl_pentest" / "qtable"
PAYLOADS_FILE = ROOT / "rl_pentest" / "data" / "payloads.json"
OUTPUT_DIR = ROOT / "lampiran"
OUTPUT_FILE = OUTPUT_DIR / "lampiran_tugas_akhir.xlsx"

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def action_names() -> list[str]:
    payloads = json.loads(PAYLOADS_FILE.read_text(encoding="utf-8"))
    names = []
    for ep_idx in range(len(ENDPOINTS)):
        for p in payloads:
            names.append(f"{p['name']}@ep{ep_idx}")
    return names


def style_sheet(ws, widths: dict, freeze: str = "A2"):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = freeze


def write_df(ws, df: pd.DataFrame):
    ws.append(list(df.columns))
    for _, row in df.iterrows():
        ws.append([None if pd.isna(v) else v for v in row.tolist()])


def sheet_training(wb):
    df = pd.read_csv(RESULTS_DIR / "log.csv", encoding="utf-8")
    ws = wb.active
    ws.title = "Data Training RL"
    write_df(ws, df)
    style_sheet(ws, {"A": 22, "B": 12, "C": 30, "D": 50, "E": 12,
                     "F": 12, "G": 12, "H": 12, "I": 14, "J": 14, "K": 14,
                     "L": 10, "M": 12, "N": 12, "O": 12, "P": 10, "Q": 10,
                     "R": 12, "S": 40, "T": 40})


def sheet_qtable(wb):
    q = json.loads((QTABLE_DIR / "q_table.json").read_text(encoding="utf-8"))
    names = action_names()
    rows = []
    for state, values in q.items():
        row = {"state": state}
        for i, name in enumerate(names):
            row[name] = values[i] if i < len(values) else ""
        rows.append(row)
    df = pd.DataFrame(rows)
    ws = wb.create_sheet("Q-Table Hasil Learning")
    write_df(ws, df)
    style_sheet(ws, {"A": 32} | {get_column_letter(c): 12 for c in range(2, len(names) + 2)})


def sheet_zap(wb):
    rep = json.loads((RESULTS_DIR / "zap_controlled_report.json").read_text(encoding="utf-8"))
    rows = []
    for cat, alerts in rep.get("alerts_categorized", {}).items():
        for a in alerts:
            rows.append({
                "Kategori": cat,
                "Nama Alert": a.get("name"),
                "Risk": a.get("risk"),
                "URL": a.get("url"),
                "Param": a.get("param"),
                "Evidence": a.get("evidence"),
                "Attack": a.get("attack"),
            })
    df = pd.DataFrame(rows)
    ws = wb.create_sheet("Hasil Scan ZAP")
    write_df(ws, df)
    style_sheet(ws, {"A": 10, "B": 40, "C": 14, "D": 60, "E": 12, "F": 50, "G": 30})

    zap = rep.get("zap_results", {})
    ws2 = wb.create_sheet("Ringkasan Scan ZAP")
    meta = rep.get("metadata", {})
    data = {
        "Tool": meta.get("tool", ""),
        "Target": meta.get("target", ""),
        "Endpoint": "; ".join(meta.get("endpoints_scanned", [])),
        "Timestamp": meta.get("timestamp", ""),
        "Total Requests": zap.get("total_requests", 0),
        "Total Alerts (raw)": zap.get("total_alerts_raw", 0),
        "Total Vulnerabilities": zap.get("total_vulnerabilities", 0),
        "SQL Injection": zap.get("alerts_by_category", {}).get("sqli", 0),
        "Reflected XSS": zap.get("alerts_by_category", {}).get("xss", 0),
        "Path Injection": zap.get("alerts_by_category", {}).get("path", 0),
        "Other": zap.get("alerts_by_category", {}).get("other", 0),
        "Requests per Vulnerability": zap.get("requests_per_vulnerability", 0),
    }
    write_df(ws2, pd.DataFrame({"Metrik": list(data.keys()), "Nilai": list(data.values())}))
    style_sheet(ws2, {"A": 35, "B": 80})


def sheet_comparison(wb):
    rep = json.loads((ROOT / "zap_comparison_report.json").read_text(encoding="utf-8"))
    ws = wb.create_sheet("Perbandingan QL vs ZAP")

    ql = rep["ql_results"]
    zap = rep["zap_results"]
    rows = [
        ("Sumber ZAP", rep.get("zap_source", "")),
        ("Target Endpoint", rep.get("target_endpoints", "")),
        ("Total Requests - Q-Learning", ql["total_requests"]),
        ("Total Requests - ZAP", zap["total_requests"]),
        ("Total Vulnerabilities - Q-Learning", ql["total_vulnerabilities"]),
        ("Total Vulnerabilities - ZAP", zap["total_vulnerabilities"]),
        ("SQL Injection - Q-Learning", ql["vuln_types"]["SQL Injection"]),
        ("SQL Injection - ZAP", zap["alerts_by_category"]["SQL Injection"]),
        ("Reflected XSS - Q-Learning", ql["vuln_types"]["Reflected XSS"]),
        ("Reflected XSS - ZAP", zap["alerts_by_category"]["Reflected XSS"]),
        ("Path / Fuzzing - Q-Learning", ql["vuln_types"]["Path / Fuzzing"]),
        ("Path Injection - ZAP", zap["alerts_by_category"]["Path Injection"]),
        ("Requests per Vulnerability - Q-Learning", ql["requests_per_vulnerability"]),
        ("Requests per Vulnerability - ZAP", zap["requests_per_vulnerability"]),
        ("Cumulative Reward - Q-Learning", ql["cumulative_reward"]),
        ("States Visited - Q-Learning", ql["states_visited"]),
    ]
    write_df(ws, pd.DataFrame({"Metrik": [r[0] for r in rows], "Nilai": [r[1] for r in rows]}))
    style_sheet(ws, {"A": 45, "B": 30})

    ws2 = wb.create_sheet("Analisis Perbandingan")
    anal = rep["analysis"]
    rows2 = [
        ("Efisiensi", anal["efficiency_comparison"]),
        ("Adaptivitas", anal["adaptivity"]),
        ("Cakupan", anal["coverage"]),
        ("Kesimpulan", anal["conclusion"]),
    ]
    write_df(ws2, pd.DataFrame({"Aspek": [r[0] for r in rows2], "Penjelasan": [r[1] for r in rows2]}))
    for row in ws2.iter_rows(min_row=2, max_row=ws2.max_row, max_col=2):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    ws2.column_dimensions["B"].width = 100
    ws2.column_dimensions["A"].width = 15
    style_sheet(ws2, {"A": 15, "B": 100})


def sheet_summary(wb):
    rep = json.loads((RESULTS_DIR / "summary.json").read_text(encoding="utf-8"))
    rows = list(rep.items())
    ws = wb.create_sheet("Ringkasan Training")
    write_df(ws, pd.DataFrame({"Metrik": [r[0] for r in rows], "Nilai": [r[1] for r in rows]}))
    style_sheet(ws, {"A": 35, "B": 80})


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    sheet_training(wb)
    sheet_qtable(wb)
    sheet_zap(wb)
    sheet_comparison(wb)
    sheet_summary(wb)
    wb.save(OUTPUT_FILE)
    print(f"[+] Lampiran tersimpan: {OUTPUT_FILE}")
    for s in wb.sheetnames:
        print(f"    - Sheet: {s}")


if __name__ == "__main__":
    main()
