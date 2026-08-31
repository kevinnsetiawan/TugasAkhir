# AGENTS.md — Tugas Akhir RL Web Pentest

Automated web penetration testing using Q-Learning / DQN against OWASP Juice Shop at
`http://localhost:3000`. Academic S1 final project.

## Commands (run from repo root, `.venv` must be active)

| Purpose | Command |
|---------|---------|
| Q-Learning training | `python rl_pentest\main.py` |
| DQN training | `python rl_pentest\train_dqn.py` |
| All unit tests | `python test_agent.py` |
| Visualize results | `python visualize_results.py ql` or `python visualize_results.py dqn` (default `ql`) |
| ZAP controlled scan | `python zap_controlled_scan.py` |
| ZAP comparison | `python zap_comparison.py` |
| Streamlit dashboard | `streamlit run rl_pentest\dashboard.py` |
| Install deps | `pip install -r rl_pentest\requirements.txt` |
| Start Juice Shop | `docker run --rm -p 3000:3000 bkimminich/juice-shop` |

Training pipeline:
- **QL**: `main.py` → `visualize_results.py ql` → `zap_comparison.py`
- **DQN**: `train_dqn.py` → `visualize_results.py dqn`

## Config & key params (`rl_pentest/config.py` is source of truth)

- 200 episodes, α=0.1, γ=0.9, ε=1.0→0.1, **ε_decay=0.90**
- Reward: +50 vuln, +10 anomaly, -1 normal, -5 error; length bonus +0/+0/+5/+10 per cat
- 8 endpoints (5 GET, 3 POST), 11 payloads (4 sqli, 3 xss, 4 fuzzing) → **88 actions**
- Action encoding: `endpoint = action // 11`, `payload = action % 11`
- Fallback baseline length=2200, OPTIMISTIC_INIT=5.0 (Q-values start at 5), RANDOM_SEED=42
- Initial state: `("2xx", 1, 0, 0, 0, 0, 0, 0)` (8-tuple)
- RANDOM_SEED=42 is hardcoded in both `main.py` and `train_dqn.py` (not in config)

## State (8-dim → 28-dim one-hot for DQN)

`(status_category, length_category, error_flag, reflected_flag, vuln_indicator, endpoint_index, response_time_category, content_type_category)`

DQN encoding: `encode_state()` in `rl_pentest/agent/dqn_agent.py` one-hot encodes status (5), length (4), endpoint (8), response time (3), content type (5) + 3 raw scalars = 28.

## Non-obvious facts

- `test_agent.py` inserts `sys.path.insert(0, "rl_pentest")` — run from repo root. Contains 7 test classes under `unittest` (includes QL, reward, payload generator, response analyzer, DQN).
- **QL and DQN use SEPARATE result files**: `log_ql.csv`/`summary_ql.json` vs `log_dqn.csv`/`summary_dqn.json`. Running one does not overwrite the other. Legacy `log.csv`/`summary.json` in config.py are aliases pointing to the QL files and are no longer written directly.
- `run_episode`, `verify_vulnerability`, and `probe_endpoint_baselines` live in `rl_pentest/training_loop.py` and are SHARED by `main.py` and `train_dqn.py` (single source; not copy-paste anymore).
- **Per-endpoint baseline**: before training, `probe_endpoint_baselines` sends benign `"hello"` to each endpoint; `ResponseAnalyzer.set_baselines()` stores them and `significant_change` is computed against that endpoint's baseline (fallback 2200). Avoids inflated `significant_change`/sqli detection from a fixed global baseline.
- **False positive verification**: benign `"hello"` sent alongside each finding. If benign also flags, reward demoted to +10 anomaly. Verification adds 1 request per finding, tracked as `verification_requests` in summary (not included in `total_requests`).
- `summary_*.json` now also include `baseline_probe_requests` and `total_requests_with_verification`.
- POST endpoints (`/rest/user/login`, `/api/Reviews`, `/api/Feedbacks`) use JSON body. Payloads `sqli_login` and `xss_review` are JSON strings parsed by `HTTPClient._send_post`.
- `visualize_results.py` takes an agent arg (`ql`/`dqn`); uses `matplotlib.use("Agg")`. Figures are saved per-agent (`*_ql.png`/`*_dqn.png`): `cumulative_reward_{agent}.png`, `request_count_efficiency_{agent}.png`, `q_table_heatmap_ql.png` (heatmap only for QL).
- "precision" in metrics.py = `total_vuln / total_episodes` (not ML precision / recall). `requests_per_vulnerability` = `inf` when no vulns.
- `zap_comparison.py` reads ONLY QL data (`summary_ql.json`/`log_ql.csv`) and refuses to run if neither exists. Efficiency comparison uses the 2 shared endpoints (`endpoint_index` 0 and 1: search & /ftp/) so it is apples-to-apples with `zap_controlled_scan.py`.
- `qtable/` and `results/` are NOT gitignored — training artifacts are tracked by default.
- Agent subpackage `__init__.py` files are empty (no re-exports).
- No lint/typecheck scripts exist.

## Outputs

| Artifact | Location |
|----------|----------|
| QL Q-table | `rl_pentest/qtable/q_table.json` (plain JSON) |
| QL training log | `rl_pentest/results/log_ql.csv` |
| QL summary | `rl_pentest/results/summary_ql.json` |
| DQN model | `rl_pentest/qtable/dqn_model.pt` (PyTorch checkpoint) |
| DQN training log | `rl_pentest/results/log_dqn.csv` |
| DQN summary | `rl_pentest/results/summary_dqn.json` |
| Figures | `figures/` (per-agent PNGs: `*_ql.png`/`*_dqn.png`) |
| ZAP comparison | `zap_comparison_report.json` |

## ZAP integration

- `zap_controlled_scan.py` requires ZAP daemon on `localhost:8080`; targets only the 2 shared endpoints (search & /ftp/), the same ones `zap_comparison.py` uses for the apples-to-apples subset.
- `zap_comparison.py` prioritizes: controlled scan report > live scan report > literature (Sahu et al., 2023).
- `main.py` optionally runs `zap_baseline.py` (python-owasp-zap-v2.4) after training if ZAP daemon is detected.
- `juice-shop/` is gitignored (not a submodule).
