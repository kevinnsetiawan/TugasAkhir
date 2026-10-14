import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

RESULTS_DIR = Path("rl_pentest/results")
FIGURES_DIR = Path("figures")
QL_QTABLE_FILE = Path("rl_pentest/qtable/q_table.json")
PAYLOADS_FILE = Path("rl_pentest/data/payloads.json")

FIGURES_DIR.mkdir(exist_ok=True)

LOG_FILES = {
    "ql": RESULTS_DIR / "log_ql.csv",
    "dqn": RESULTS_DIR / "log_dqn.csv",
}
SUMMARY_FILES = {
    "ql": RESULTS_DIR / "summary_ql.json",
    "dqn": RESULTS_DIR / "summary_dqn.json",
}
QTABLE_FILES = {
    "ql": QL_QTABLE_FILE,
    "dqn": None,
}

ACTION_NAMES = [p["name"] for p in json.loads(PAYLOADS_FILE.read_text())]


def load_data(agent):
    log_df = pd.read_csv(LOG_FILES[agent]) if LOG_FILES[agent].exists() else pd.DataFrame()
    summary = json.loads(SUMMARY_FILES[agent].read_text()) if SUMMARY_FILES[agent].exists() else {}
    qtable_file = QTABLE_FILES[agent]
    qtable = json.loads(qtable_file.read_text()) if qtable_file and qtable_file.exists() else {}
    return log_df, summary, qtable


def plot_cumulative_reward(log_df, agent):
    fig, ax = plt.subplots(figsize=(10, 5))
    log_df["reward"].cumsum().plot(ax=ax, color="royalblue", linewidth=1.5)
    ax.set_title("Cumulative Reward per Request", fontsize=13, fontweight="bold")
    ax.set_xlabel("Request Step")
    ax.set_ylabel("Cumulative Reward")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    filename = f"cumulative_reward_{agent}.png"
    fig.savefig(FIGURES_DIR / filename, dpi=150)
    plt.close(fig)
    print(f"[+] Saved figures/{filename}")


def plot_request_count_efficiency(log_df, agent):
    fig, ax = plt.subplots(figsize=(10, 5))
    vuln_hits = log_df[log_df["vulnerability"] != "none"]
    if not vuln_hits.empty:
        cumulative = vuln_hits.copy()
        cumulative["count"] = 1
        cumulative["count"] = cumulative["count"].cumsum()
        cumulative["count"].plot(ax=ax, label="Vulnerabilities Found", color="green", linewidth=1.5)
        det_rate = len(vuln_hits) / len(log_df) * 100
        ax.set_title(f"Request Count Efficiency (Detection Rate: {det_rate:.1f}%)",
                     fontsize=13, fontweight="bold")
    else:
        ax.set_title("Request Count Efficiency (No vulnerabilities detected)",
                     fontsize=13, fontweight="bold")
    ax.set_xlabel("Request Step")
    ax.set_ylabel("Cumulative Vulnerabilities")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    filename = f"request_count_efficiency_{agent}.png"
    fig.savefig(FIGURES_DIR / filename, dpi=150)
    plt.close(fig)
    print(f"[+] Saved figures/{filename}")


def _humanize_state(key):
    parts = str(key).split("|")
    if len(parts) == 8:
        status, length_cat, error, reflected, vuln, endpoint, resp_time, content = parts
        return (
            f"HTTP {status}, len_cat {length_cat}, err {error}, refl {reflected}, "
            f"vuln {vuln}, ep{endpoint}, rt {resp_time}, ct {content}"
        )
    return key


def plot_qtable_heatmap(qtable, agent):
    if not qtable:
        print("[-] No Q-Table to visualize")
        return

    states      = list(qtable.keys())
    n_actions   = len(ACTION_NAMES)
    n_states    = len(states)
    data        = np.array([qtable[s] for s in states])   # shape (n_states, 120)
    n_cols      = data.shape[1]

    # ── 1. NORMALISASI WARNA: pakai log-scale agar gradasi Q kecil tetap terlihat
    # Q-value range: optimistic_init=5, reward_vuln=50+bonus → max ~60
    # Geser ke ≥0 sebelum log (min bisa −5)
    shift      = abs(data.min()) + 1          # pastikan semua positif
    data_pos   = data + shift                  # semua ≥ 1
    data_log   = np.log1p(data_pos)            # log(1 + x) smooth di dekat 0

    cmap = LinearSegmentedColormap.from_list(
        "rl_heatmap",
        ["#f7f7f7", "#a8d5a2", "#2e8b57", "#1a4d2e"],   # putih → hijau muda → hijau tua
        N=512,
    )

    # ── 2. UKURAN CANVAS: lebar proporsional dengan jumlah aksi
    fig_w = max(28, n_cols * 0.22)
    fig_h = max(6,  n_states * 0.55)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    im = ax.imshow(data_log, cmap=cmap, aspect="auto")

    # ── 3. SUMBU X: tampilkan hanya setiap 5 aksi, label pendek "ep{ep}\n{payload}"
    x_tick_positions = list(range(0, n_cols, 5))
    x_tick_labels    = []
    for idx in x_tick_positions:
        ep      = idx // n_actions
        pl_idx  = idx % n_actions
        pl_name = ACTION_NAMES[pl_idx] if pl_idx < len(ACTION_NAMES) else str(pl_idx)
        # Potong nama payload agar tidak terlalu panjang
        short   = pl_name.replace("sqli_", "sqli:").replace("xss_", "xss:") \
                         .replace("lfi_", "lfi:").replace("fuzz_", "fuzz:")
        x_tick_labels.append(f"a{idx}\n{short}\n@ep{ep}")

    ax.set_xticks(x_tick_positions)
    ax.set_xticklabels(x_tick_labels, fontsize=7.5, ha="center")

    # ── 4. SUMBU Y: label state yang lebih ringkas
    y_labels = [_short_state(s) for s in states]
    ax.set_yticks(range(n_states))
    ax.set_yticklabels(y_labels, fontsize=8.5)

    # ── 5. TANPA ANNOTASI ANGKA DI DALAM SEL (annot=False equivalent)
    #       Hanya tandai sel dengan Q-value tertinggi per state
    for i in range(n_states):
        best_j = int(np.argmax(data[i]))
        best_v = data[i, best_j]
        ax.add_patch(plt.Rectangle(
            (best_j - 0.5, i - 0.5), 1, 1,
            fill=False, edgecolor="red", linewidth=1.5, zorder=3,
        ))
        ax.text(
            best_j, i, f"{best_v:.1f}",
            ha="center", va="center", fontsize=7, fontweight="bold",
            color="white", zorder=4,
        )

    # ── 6. COLORBAR dengan skala asli (bukan log) sebagai tick reference
    cb = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("Q-Value (log-scaled)", fontsize=9)
    # Tambahkan tick referensi di nilai Q asli yang penting
    ref_vals   = [-5, 0, 5, 10, 20, 35, 50, 60]
    ref_log    = [np.log1p(v + shift) for v in ref_vals]
    cb.set_ticks(ref_log)
    cb.set_ticklabels([str(v) for v in ref_vals], fontsize=8)

    ax.set_xlabel("Action Index  (setiap 5 aksi ditampilkan; sel merah = nilai Q tertinggi per state)",
                  fontsize=9, labelpad=8)
    ax.set_ylabel("State", fontsize=10, labelpad=6)
    ax.set_title(
        "Heatmap Nilai Q pada Pasangan State–Action  (Q-Learning, 1585 Episode)\n"
        "Warna hijau tua = Q-Value tinggi (aksi produktif) · Warna putih = Q-Value rendah/optimistic init",
        fontsize=11, fontweight="bold", pad=12,
    )

    fig.tight_layout()
    filename = f"q_table_heatmap_{agent}.png"
    fig.savefig(FIGURES_DIR / filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved figures/{filename}")


def _short_state(key):
    """Label state ringkas untuk sumbu Y heatmap."""
    parts = str(key).strip("()").split("|")
    if len(parts) == 8:
        status, lcat, err, refl, vuln, ep, rt, ct = parts
        flags = []
        if err  == "1": flags.append("ERR")
        if refl == "1": flags.append("REFL")
        if vuln == "1": flags.append("VULN")
        flag_str = "+" + "+".join(flags) if flags else ""
        return f"HTTP-{status} L{lcat} ep{ep}{flag_str}"
    return key


def _action_name(idx, n_actions):
    """Nama aksi ringkas: payload@ep untuk print_qtable_analysis."""
    ep      = idx // n_actions
    pl_idx  = idx % n_actions
    base    = ACTION_NAMES[pl_idx] if pl_idx < len(ACTION_NAMES) else str(pl_idx)
    return f"{base}@ep{ep}"



def print_qtable_analysis(qtable):
    if not qtable:
        return

    print("\n" + "=" * 70)
    print("  ANALISIS Q-TABLE - State-Action Values")
    print("=" * 70)

    n_actions = len(ACTION_NAMES)
    for state_key, values in qtable.items():
        label = _humanize_state(state_key)
        values_arr = np.array(values)
        best_idx = int(np.argmax(values_arr))
        best_val = values_arr[best_idx]
        best_action = _action_name(best_idx, n_actions)

        print(f"\n  State: {label}")
        print(f"  {'-' * 50}")
        sorted_idx = np.argsort(values_arr)[::-1]
        for rank, idx in enumerate(sorted_idx[:5], 1):
            if values_arr[idx] > 0:
                print(f"    {rank}. {_action_name(idx, n_actions):>20} -> Q = {values_arr[idx]:>8.2f}")
        print(f"    -> Optimal: {best_action} (Q={best_val:.2f})")


def print_summary_table(log_df, summary, qtable):
    """Cetak tabel ringkasan hasil (dipanggil dari visualize_results.py)."""
    import sys
    sys.path.insert(0, "rl_pentest")
    import cyber_output as cyber
    cyber.init()
    records = log_df.to_dict("records")
    agent_label = summary.get("agent_type", "UNKNOWN").upper()
    
    cyber.table_vuln_findings(records)
    cyber.table_per_endpoint(records, n_endpoints=8)
    cyber.table_summary(agent_label, summary, records)


def main():
    parser = argparse.ArgumentParser(description="Visualisasi hasil training RL Pentest")
    parser.add_argument(
        "agent",
        nargs="?",
        default="ql",
        choices=["ql", "dqn"],
        help="Pipeline yang divisualisasi: ql (Q-Learning) atau dqn (DQN). Default: ql",
    )
    args = parser.parse_args()

    log_df, summary, qtable = load_data(args.agent)
    if log_df.empty:
        print(f"[-] Tidak ada data log untuk agent '{args.agent}'. Jalankan training dulu.")
        print("    Q-Learning: python rl_pentest\\main.py | DQN: python rl_pentest\\train_dqn.py")
        return

    print(f"[+] Agent: {args.agent.upper()} | {len(log_df)} log entries, {len(qtable)} Q-Table states")

    plot_cumulative_reward(log_df, args.agent)
    plot_request_count_efficiency(log_df, args.agent)
    if qtable:
        plot_qtable_heatmap(qtable, args.agent)
        print_qtable_analysis(qtable)
    else:
        print("[-] Tidak ada Q-Table untuk agent DQN (heatmap hanya untuk Q-Learning)")
    print_summary_table(log_df, summary, qtable)

    print("\n[+] All figures saved in figures/")
    print(f"[+] Ringkasan agent '{args.agent}' selesai\n")


if __name__ == "__main__":
    main()