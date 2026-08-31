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
    ax.set_yticklabels([_humanize_state(s) for s in states], fontsize=9)

    for i in range(len(states)):
        for j in range(len(action_labels)):
            val = data[i, j]
            color = "white" if 10 < val < 40 else "black"
            ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=7, color=color)

    ax.set_title("Q-Table Heatmap: Learned Action Values per State",
                 fontsize=13, fontweight="bold")
    fig.colorbar(im, ax=ax, label="Q-Value", shrink=0.8)
    fig.tight_layout()
    filename = f"q_table_heatmap_{agent}.png"
    fig.savefig(FIGURES_DIR / filename, dpi=150)
    plt.close(fig)
    print(f"[+] Saved figures/{filename}")


def _action_label(idx, max_idx):
    base = ACTION_NAMES[idx % len(ACTION_NAMES)]
    ep = idx // len(ACTION_NAMES)
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
    states_visited = len(qtable) if qtable else 0

    print("\n" + "=" * 70)
    print("  RINGKASAN HASIL PENTEST")
    print("=" * 70)
    print(f"  {'Total HTTP Requests (payload)':40} {total_req}")
    print(f"  {'Total Vulnerabilities':40} {total_vuln}")
    print(f"  {'Detection Rate':40} {det_rate:.1f}%")
    print(f"  {'Requests per Vulnerability':40} {req_per_vuln}")
    print(f"  {'Cumulative Reward':40} {cum_reward}")
    print(f"  {'States Visited (Q-Table)':40} {states_visited}")
    print(f"  {'SQL Injection':40} {summary.get('sql_injection', 0)}")
    print(f"  {'Reflected XSS':40} {summary.get('reflected_xss', 0)}")
    print(f"  {'Fuzzing Anomaly':40} {summary.get('fuzzing_anomaly', 0)}")
    print(f"  {'Verification Requests':40} {summary.get('verification_requests', 0)}")
    print(f"  {'Baseline Probe Requests':40} {summary.get('baseline_probe_requests', 0)}")
    print(f"  {'Total w/ Verification':40} {summary.get('total_requests_with_verification', total_req)}")
    print("=" * 70)


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