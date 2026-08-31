#!/usr/bin/env python
"""Salin aset hasil eksperimen terkini ke folder thesis/ (untuk sinkron Overleaf).

Menyalin dari repo utama (figures/, rl_pentest/results/) ke thesis/figures/
dan thesis/data/. Jalankan dari root repo utama:
    python scripts/export_thesis_assets.py
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THESIS = ROOT / "thesis"

FIGURE_FILES = [
    "figures/cumulative_reward_ql.png",
    "figures/request_count_efficiency_ql.png",
    "figures/q_table_heatmap_ql.png",
    "figures/cumulative_reward_dqn.png",
    "figures/request_count_efficiency_dqn.png",
]

DATA_FILES = [
    "rl_pentest/results/summary_ql.json",
    "rl_pentest/results/summary_dqn.json",
    "zap_comparison_report.json",
]


def main():
    if not THESIS.exists():
        print(f"[-] Folder '{THESIS}' tidak ada. Jalankan dari root repo utama.")
        return

    fig_dir = THESIS / "figures"
    data_dir = THESIS / "data"
    fig_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    copied = []
    for rel in FIGURE_FILES:
        src = ROOT / rel
        if not src.exists():
            print(f"[!] Figure belum ada (jalankan visualize_results.py): {rel}")
            continue
        dest = fig_dir / src.name
        shutil.copy2(src, dest)
        copied.append(dest)

    for rel in DATA_FILES:
        src = ROOT / rel
        if not src.exists():
            print(f"[!] Data belum ada: {rel}")
            continue
        dest = data_dir / src.name
        shutil.copy2(src, dest)
        copied.append(dest)

    if not copied:
        print("[-] Tidak ada aset yang disalin.")
        return

    ringkasan = ROOT / "rl_pentest" / "results" / "summary_ql.json"
    if ringkasan.exists():
        s = json.loads(ringkasan.read_text())
        print(f"    QL detection rate : {s.get('precision', 'n/a')}")
    ringkasan_dqn = ROOT / "rl_pentest" / "results" / "summary_dqn.json"
    if ringkasan_dqn.exists():
        s = json.loads(ringkasan_dqn.read_text())
        print(f"    DQN detection rate: {s.get('precision', 'n/a')}")

    print(f"[+] {len(copied)} aset disalin:")
    for path in copied:
        print(f"    {path.relative_to(ROOT)}")
    print("\nLangkah berikut (dari root repo utama):")
    print("    git -C thesis add -A")
    print('    git -C thesis commit -m "Update aset hasil eksperimen"')
    print("    git -C thesis push")


if __name__ == "__main__":
    main()