# AGENTS.md — Tugas Akhir RL Web Pentest

Automated web penetration testing using Q-Learning / DQN against OWASP Juice Shop at
`http://localhost:3000`. Academic S1 final project.

## Commands (run from repo root, `.venv` must be active)

| Purpose | Command |
|---------|---------|
| Q-Learning training | `python rl_pentest\main.py` |
| DQN training | `python rl_pentest\train_dqn.py` |
| All unit tests | `python test_agent.py` |
| Visualize results | `python visualize_results.py` |
| ZAP controlled scan | `python zap_controlled_scan.py` |
| ZAP comparison | `python zap_comparison.py` |
| Streamlit dashboard | `streamlit run rl_pentest\dashboard.py` |
| Install deps | `pip install -r rl_pentest\requirements.txt` |
| Start Juice Shop | `docker run --rm -p 3000:3000 bkimminich/juice-shop` |

Training pipeline:
- **QL**: `main.py` → `visualize_results.py` → `zap_comparison.py`
- **DQN**: `train_dqn.py` → `visualize_results.py`

## Config & key params (`rl_pentest/config.py` is source of truth)

- 200 episodes, α=0.1, γ=0.9, ε=1.0→0.1, **ε_decay=0.90** (README says 0.95 — trust code)
- Reward: +50 vuln, +10 anomaly, -1 normal, -5 error; length bonus +0/+0/+5/+10 per cat
- 8 endpoints (5 GET, 3 POST), 11 payloads (4 sqli, 3 xss, 4 fuzzing) → **88 actions**
- Action encoding: `endpoint = action // 11`, `payload = action % 11`
- Baseline length=2200, OPTIMISTIC_INIT=5.0 (Q-values start at 5), RANDOM_SEED=42
- Initial state: `("2xx", 1, 0, 0, 0, 0, 0, 0)` (8-tuple)
- RANDOM_SEED=42 is hardcoded in both `main.py` and `train_dqn.py` (not in config)

## State (8-dim → 28-dim one-hot for DQN)

`(status_category, length_category, error_flag, reflected_flag, vuln_indicator, endpoint_index, response_time_category, content_type_category)`

DQN encoding: `encode_state()` in `rl_pentest/agent/dqn_agent.py` one-hot encodes status (5), length (4), endpoint (8), response time (3), content type (5) + 3 raw scalars = 28.

## Non-obvious facts

- `test_agent.py` inserts `sys.path.insert(0, "rl_pentest")` — run from repo root. Contains 4 test classes under `unittest`.
- **False positive verification**: benign `"hello"` sent alongside each finding. If benign also flags, reward demoted to +10 anomaly.
- QL and DQN training loops in `main.py` / `train_dqn.py` are structurally identical (copy-paste coupling; fix in one = fix in both).
- POST endpoints (`/rest/user/login`, `/api/Reviews`, `/api/Feedbacks`) use JSON body. Payloads `sqli_login` and `xss_review` are JSON strings parsed by `HTTPClient._send_post`.
- `visualize_results.py` uses `matplotlib.use("Agg")` — no display required. Produces 3 figures: `cumulative_reward.png`, `request_count_efficiency.png`, `q_table_heatmap.png`.
- "precision" in metrics.py = `total_vuln / total_episodes` (not ML precision / recall).
- `qtable/` and `results/` are NOT gitignored — training artifacts are tracked by default.
- Agent subpackage `__init__.py` files are empty (no re-exports).
- No lint/typecheck scripts exist.

## Outputs

| Artifact | Location |
|----------|----------|
| QL Q-table | `rl_pentest/qtable/q_table.json` (plain JSON) |
| DQN model | `rl_pentest/qtable/dqn_model.pt` (PyTorch checkpoint) |
| Training log | `rl_pentest/results/log.csv` |
| Summary | `rl_pentest/results/summary.json` |
| Figures | `figures/` (3 PNGs) |
| ZAP comparison | `zap_comparison_report.json` |

## ZAP integration

- `zap_controlled_scan.py` requires ZAP daemon on `localhost:8080`; targets only the 2 QL endpoints.
- `zap_comparison.py` prioritizes: controlled scan report > live scan report > literature (Sahu et al., 2023).
- `main.py` optionally runs `zap_baseline.py` (python-owasp-zap-v2.4) after training if ZAP daemon is detected.
- `juice-shop/` is gitignored (not a submodule).
