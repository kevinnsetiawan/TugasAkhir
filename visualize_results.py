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
QTABLE_FILE = Path("rl_pentest/qtable/q_table.json")
PAYLOADS_FILE = Path("rl_pentest/data/payloads.json")
CSV_LOG = RESULTS_DIR / "log.csv"
SUMMARY_FILE = RESULTS_DIR / "summary.json"

FIGURES_DIR.mkdir(exist_ok=True)

ACTION_NAMES = [p["name"] for p in json.loads(PAYLOADS_FILE.read_text())]
STATE_LABELS = {
    "2xx|medium|0|0": "Initial (200, medium, OK)",
    "2xx|small|0|0": "200, small, OK",
    "2xx|large|0|0": "200, large, OK",
    "4xx|large|0|0": "403/404, large, blocked",
    "5xx|small|1|0": "500 error, small, SQL err",
}


def load_data():
    log_df = pd.read_csv(CSV_LOG) if CSV_LOG.exists() else pd.DataFrame()
    summary = json.loads(SUMMARY_FILE.read_text()) if SUMMARY_FILE.exists() else {}
    qtable = json.loads(QTABLE_FILE.read_text()) if QTABLE_FILE.exists() else {}
    return log_df, summary, qtable


def plot_cumulative_reward(log_df):
    fig, ax = plt.subplots(figsize=(10, 5))
    log_df["reward"].cumsum().plot(ax=ax, color="royalblue", linewidth=1.5)
    ax.set_title("Cumulative Reward per Request", fontsize=13, fontweight="bold")
    ax.set_xlabel("Request Step")
    ax.set_ylabel("Cumulative Reward")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "cumulative_reward.png", dpi=150)
    plt.close(fig)
    print("[+] Saved figures/cumulative_reward.png")


def plot_request_count_efficiency(log_df):
    fig, ax = plt.subplots(figsize=(10, 5))
    vuln_hits = log_df[log_df["vulnerability"] != "none"]
    if not vuln_hits.empty:
        vuln_hits.groupby(vuln_hits.index).size().cumsum().plot(
            ax=ax, label="Vulnerabilities Found", color="green", linewidth=1.5
        )
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
    fig.savefig(FIGURES_DIR / "request_count_efficiency.png", dpi=150)
    plt.close(fig)
    print("[+] Saved figures/request_count_efficiency.png")


def plot_qtable_heatmap(qtable):
    if not qtable:
        print("[-] No Q-Table to visualize")
        return

    states = list(qtable.keys())
    sample_actions = len(next(iter(qtable.values())))
    n_actions = len(ACTION_NAMES)
    action_labels = [_action_label(i, n_actions) for i in range(sample_actions)]
    data = np.array([qtable[s] for s in states])

    fig, ax = plt.subplots(figsize=(12, max(4, len(states) * 0.6)))
    cmap = LinearSegmentedColormap.from_list("gr", ["#ffcccc", "#ffffff", "#99cc99"], N=256)

    im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=-5, vmax=60)

    ax.set_xticks(range(len(action_labels)))
    ax.set_xticklabels(action_labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(states)))
    state_labels_short = [STATE_LABELS.get(s, s) for s in states]
    ax.set_yticklabels(state_labels_short, fontsize=9)

    for i in range(len(states)):
        for j in range(len(action_labels)):
            val = data[i, j]
            color = "white" if 10 < val < 40 else "black"
            ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=7, color=color)

    ax.set_title("Q-Table Heatmap: Learned Action Values per State",
                 fontsize=13, fontweight="bold")
    fig.colorbar(im, ax=ax, label="Q-Value", shrink=0.8)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "q_table_heatmap.png", dpi=150)
    plt.close(fig)
    print("[+] Saved figures/q_table_heatmap.png")


def _action_label(idx, max_idx):
    base = ACTION_NAMES[idx % len(ACTION_NAMES)]
    ep = idx // len(ACTION_NAMES)
    return f"{base}@ep{ep}"

def print_qtable_analysis(qtable):
    if not qtable:
        return

    print("\n" + "=" * 70)
    print("  ANALISIS Q-TABLE — State-Action Values")
    print("=" * 70)

    n_actions = len(ACTION_NAMES)
    for state_key, values in qtable.items():
        label = STATE_LABELS.get(state_key, state_key)
        values_arr = np.array(values)
        best_idx = int(np.argmax(values_arr))
        best_val = values_arr[best_idx]
        best_action = _action_label(best_idx, n_actions)

        print(f"\n  State: {label}")
        print(f"  {'-' * 50}")
        sorted_idx = np.argsort(values_arr)[::-1]
        for rank, idx in enumerate(sorted_idx[:5], 1):
            if values_arr[idx] > 0:
                print(f"    {rank}. {_action_label(idx, n_actions):>20} -> Q = {values_arr[idx]:>8.2f}")
        print(f"    -> Optimal: {best_action} (Q={best_val:.2f})")


def print_summary_table(log_df, summary, qtable):
    total_req = len(log_df)
    total_vuln = summary.get("total_vulnerabilities", 0)
    det_rate = total_vuln / total_req * 100 if total_req else 0
    req_per_vuln = round(total_req / total_vuln, 2) if total_vuln else float("inf")
    cum_reward = summary.get("cumulative_reward", 0)
    states_visited = len(qtable)

    print("\n" + "=" * 70)
    print("  RINGKASAN HASIL PENTEST")
    print("=" * 70)
    print(f"  {'Total HTTP Requests':35} {total_req}")
    print(f"  {'Total Vulnerabilities':35} {total_vuln}")
    print(f"  {'Detection Rate':35} {det_rate:.1f}%")
    print(f"  {'Requests per Vulnerability':35} {req_per_vuln}")
    print(f"  {'Cumulative Reward':35} {cum_reward}")
    print(f"  {'States Visited (Q-Table)':35} {states_visited}")
    print(f"  {'SQL Injection':35} {summary.get('sql_injection', 0)}")
    print(f"  {'Reflected XSS':35} {summary.get('reflected_xss', 0)}")
    print(f"  {'Fuzzing Anomaly':35} {summary.get('fuzzing_anomaly', 0)}")
    print("=" * 70)


def main():
    log_df, summary, qtable = load_data()
    if log_df.empty:
        print("[-] No log data found. Run 'python rl_pentest\\main.py' first.")
        return

    print(f"[+] Loaded {len(log_df)} log entries, {len(qtable)} Q-Table states")

    plot_cumulative_reward(log_df)
    plot_request_count_efficiency(log_df)
    plot_qtable_heatmap(qtable)
    print_summary_table(log_df, summary, qtable)
    print_qtable_analysis(qtable)

    print("\n[+] All figures saved in figures/")
    print("[+] Q-Table analysis complete\n")


if __name__ == "__main__":
    main()
