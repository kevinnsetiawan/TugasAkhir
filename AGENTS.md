# AGENTS.md — Tugas Akhir RL Web Pentest

Automated web penetration testing using Q-Learning / DQN against OWASP Juice Shop at
`http://localhost:3000`. Academic S1 final project.

## Commands (run from repo root, `.venv` must be active)

| Purpose | Command |
|---------|---------|
| Q-Learning training | `python rl_pentest\main.py` |
| DQN training | `python rl_pentest\train_dqn.py` |
| All unit tests | `python test_agent.py` |
| Detector benchmark (no RL agent) | `python benchmark_detector.py` |
| Visualize results | `python visualize_results.py ql` or `python visualize_results.py dqn` (default `ql`) |
| ZAP controlled scan | `python zap_controlled_scan.py` |
| ZAP comparison | `python zap_comparison.py` |
| Streamlit dashboard | `streamlit run rl_pentest\dashboard.py` |
| Install deps | `pip install -r rl_pentest\requirements.txt` then `python -m playwright install chromium` |
| Start Juice Shop (Docker) | `docker run --rm -p 3000:3000 bkimminich/juice-shop` |
| Start Juice Shop (local source) | `cd juice-shop; npm start` — Docker daemon is often unavailable on this machine |

Training pipeline:
- **QL**: `main.py` → `visualize_results.py ql` → `zap_comparison.py`
- **DQN**: `train_dqn.py` → `visualize_results.py dqn`

## Config & key params (`rl_pentest/config.py` is source of truth)

- 1585 episodes (budget setara ZAP, **tanpa early-stop** — training selalu memakai seluruh budget), α=0.1, γ=0.9, ε=1.0→0.1, ε_decay=0.90
- **Action masking HANYA untuk aksi dengan vuln terverifikasi** (discovered_actions). Aksi gagal TIDAK di-mask (tidak ada anti-repetisi). Kebijakan ini membuat discovery bergantung pada pembelajaran, bukan sapuan brute-force — QL dan DQN pun bisa dibandingkan.
- Reward: +50 vuln, +10 anomaly, -1 normal, -5 error; length bonus +0/+0/+5/+10 per cat
- 8 endpoint live + 15 payload (6 sqli, 4 xss, 5 fuzzing) → **120 actions**
- Action encoding: `endpoint = action // 15`, `payload = action % 15`
- Fallback baseline length=2200, OPTIMISTIC_INIT=5.0 (Q-values start at 5), RANDOM_SEED=42
- Initial state: `("2xx", 1, 0, 0, 0, 0, 0, 0)` (8-tuple)
- RANDOM_SEED=42 is hardcoded in both `main.py` and `train_dqn.py` (not in config)

## Endpoint index (config.py) & attack surface

| idx | Method & path | surface | XSS page |
|-----|---------------|---------|----------|
| 0 | GET `/rest/products/search?q=` | sql | `/#/search?q=` |
| 1 | GET `/ftp/` | file | — |
| 2 | GET `/rest/products/1/reviews` | plain | — |
| 3 | GET `/rest/track-order/` | plain | `/#/track-result?id=` |
| 4 | POST `/rest/user/login` | sql | — |
| 5 | PUT `/rest/products/1/reviews` | plain | — |
| 6 | POST `/api/Feedbacks` (captcha via `/rest/captcha`) | plain | — |
| 7 | GET `/api/Challenges` | plain | — |

`surface` gating is declared per endpoint in config; `HTTPClient.surface_of(idx)` and `ResponseAnalyzer.analyze(..., surface=...)` enforce it. Ground-truth boredom sweep = 14 confirmed actions at 5 unique `(endpoint, class)` locations.

## State (8-dim → 28-dim one-hot for DQN)

`(status_category, length_category, error_flag, reflected_flag, vuln_indicator, endpoint_index, response_time_category, content_type_category)`

DQN encoding: `encode_state()` in `rl_pentest/agent/dqn_agent.py` one-hot encodes status (5), length (4), endpoint (8), response time (3), content type (5) + 3 raw scalars = 28.

## Non-obvious facts

- `test_agent.py` inserts `sys.path.insert(0, "rl_pentest")` — run from repo root. Contains test classes under `unittest` (includes QL, reward, payload generator, response analyzer, browser verifier instrumentation, metrics accuracy, DQN, `verified` flag semantics).
- **QL and DQN use SEPARATE result files**: `log_ql.csv`/`summary_ql.json` vs `log_dqn.csv`/`summary_dqn.json`. Running one does not overwrite the other. Legacy `log.csv`/`summary.json` in config.py are aliases pointing to the QL files and are no longer written directly.
- `run_episode`, `verify_vulnerability`, and `probe_endpoint_baselines` live in `rl_pentest/training_loop.py` and are SHARED by `main.py` and `train_dqn.py` (single source; not copy-paste anymore).
- **Single-level action masking**: `main.py` AND `train_dqn.py` mask only `discovered_actions` (verified vulns). There is NO exhausted-actions masking and NO early-stop; both agents always run the full 1585-episode budget so the result reflects learning, not a brute-force sweep.
- `summary_*.json` include `baseline_probe_requests`, `total_requests_with_verification`, `request_budget`, `discovered_actions`, `verified_actions`, `time_to_first_vulnerability`, `episode_all_discovered`, `unique_vuln_locations`. The `unique_vuln_locations` = number of distinct `(endpoint_index, vuln_class)` pairs, so 3 sqli payloads on the search endpoint count as 1 location.
- **Per-endpoint baseline**: before training, `probe_endpoint_baselines` sends benign `"hello"` to each endpoint; `ResponseAnalyzer.set_baselines()` stores them and `significant_change` is computed against that endpoint's baseline (fallback 2200). Avoids inflated `significant_change`/sqli detection from a fixed global baseline.
- **False positive verification (control-differential)**: each finding sends control probes — benign `"hello"` + `neutralize_payload()` mutant when the mutant differs from the payload (wildcard `%s` payloads skip the mutant because neutralization would be a no-op). A finding is verified only if NEITHER control reproduces the same vuln class; connection errors are treated as NOT verified. Inconclusive findings are demoted to +10 anomaly. `verify_vulnerability` returns the actual control count, so `verification_requests` in summaries reflects real probes sent (1-2 per finding), not a hardcoded 2.
- **`verified` column semantics**: `True` ONLY for findings that passed control-differential or browser execution; `False` for normal requests AND rejected candidates. `metrics.compute_metrics` counts vulnerabilities only when `vulnerability ∈ VULN_TYPES AND verified` (an episode whose candidate was rejected is NOT a vulnerability).
- **XSS is verified in a headless Chromium, not by HTTP reflection**: `BrowserVerifier` (Playwright sync API) instruments the vector (same tag/event shape, handler replaced with a global canary `window.__RLP_XSS_CANARY__=1`), loads the SPA page, and returns the finding only if the canary actually executes in the DOM. Reflection in the HTTP body alone is NOT sufficient (JS in `JSON` bodies doesn't execute). `XSS_PAGES` in config maps endpoint → SPA page. All XSS findings on search/track-result are DOM-executed.
- **Browser determinism**: `BrowserVerifier` does (1) a one-time warmup navigation so SPA assets are cached before probing, and (2) bounded polling for the canary instead of a fixed sleep. Without warmup, the first probes on a cold browser race asset downloads and produce flaky verdicts (e.g. `<svg onload>` fired 1/5 on cold, 4/4 warm).
- **Detection requires exploitation evidence, not heuristics**: `ResponseAnalyzer._detect_vulnerability` flags sqli on (a) DB-error+≥4xx or (b) 2xx with significant change vs endpoint baseline (boolean-based, e.g. `' OR '1'='1` dumping the full product table, or admin auth-bypass on login); file disclosure only when the endpoint's surface is `file` AND the response confirms real content or a `%2500` extension-bypass served as non-markdown/pdf type (raw `package.json`, `coupons_2013.md.bak`, `suspicious_errors.yml` on `/ftp/`); fuzzing only when a 5xx echoes the raw probe. Generic 500 pages, /ftp/ directory listing, and reflection alone do NOT count. Surface gating prevents e.g. a `%s` query on `/api/Challenges` (NoSQL, whole-collection dump) from being mislabeled SQLi.
- `summary_*.json` now also include `baseline_probe_requests`, `total_requests_with_verification`, `request_budget`, `discovered_actions`, `verified_actions`, `browser_navigations`, `verification_requests`.
- POST endpoints use JSON body; `sqli_login` and `xss_review` are JSON strings parsed by `HTTPClient._send_post`. `/api/Feedbacks` requires a captcha (fetched via `/rest/captcha`, defaults `rating=1`, `UserId=1`). `/api/Reviews` does NOT exist in current Juice Shop — reviews write via `PUT /rest/products/1/reviews`.
- `visualize_results.py` takes an agent arg (`ql`/`dqn`); uses `matplotlib.use("Agg")`. Figures are saved per-agent (`*_ql.png`/`*_dqn.png`): `cumulative_reward_{agent}.png`, `request_count_efficiency_{agent}.png`, `q_table_heatmap_ql.png` (heatmap only for QL).
- "precision" in metrics.py = `total_vuln / total_episodes` (not ML precision / recall). `requests_per_vulnerability` = `inf` when no vulns.
- `zap_comparison.py` reads ONLY QL data (`summary_ql.json`/`log_ql.csv`) and refuses to run if neither exists. Efficiency comparison uses the 2 shared endpoints (`endpoint_index` 0 and 1: search & /ftp/) so it is apples-to-apples with `zap_controlled_scan.py`.
- `qtable/` and `results/` are NOT gitignored — training artifacts are tracked by default.
- Subpackages (`agent/`, `analyzer/`, `baseline/`, `engine/`, `evaluation/`, `logger/`, `reward/`) and `rl_pentest/` have NO `__init__.py` — Python 3 namespace packages. All imports resolve by having `rl_pentest` on `sys.path` (tests insert it; `main.py`/`train_dqn.py`/`dashboard.py` run with their own dir on path).
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
| Figure | `figures/` (per-agent PNGs: `*_ql.png`/`*_dqn.png`) |
| ZAP comparison | `zap_comparison_report.json` |
| Detector benchmark | `rl_pentest/results/detector_benchmark.json` |

## ZAP integration

- `zap_controlled_scan.py` requires ZAP daemon on `localhost:8080`; targets only the 2 shared endpoints (search & /ftp/), the same ones `zap_comparison.py` uses for the apples-to-apples subset.
- `zap_comparison.py` prioritizes: controlled scan report > live scan report > literature (Sahu et al., 2023).
- `main.py` optionally runs `zap_baseline.py` (python-owasp-zap-v2.4) after training if ZAP daemon is detected.
- `juice-shop/` is gitignored (not a submodule).

## Metrik & methodology (WAJIB dibaca sebelum melapor angka)

Semua angka di `summary_*.json` adalah **IN-SAMPLE**: dihitung dari 1585 episode
yang sama dengan fase training. `summary_*.json` memuat `metrics_scope` yang
menyatakan hal ini eksplisit. Tidak ada split train/test di proyek ini.

### Metrik yang DIHAPUS (bukan lagi dilaporkan)

- `detection_accuracy` — rumusnya `vuln / (vuln + rejected)`, yang **selalu 1.0**
  selama tidak ada kandidat ditolak. Bukan ukuran akurasi, jadi dihapus.
- `precision` — sebenarnya `total_vuln / total_episodes` (hit rate per request),
  bukan precision ML. Diganti nama menjadi **`vuln_hit_rate`**.
- `rejected_candidates` kini dilaporkan sebagai **jumlah**, bukan rasio.

### `benchmark_detector.py` — satu-satunya sumber precision/recall/F1

Menjalankan `ResponseAnalyzer` langsung ke 120 aksi (8 endpoint × 15 payload)
**tanpa agent RL sama sekali**, lalu membandingkannya dengan label di
`rl_pentest/ground_truth.py`. Ini memutus circularity: reward dan "kerentanan
yang ditemukan" biasanya datang dari kode detektor yang sama.

`evaluate_action` di skrip ini **wajib meniru `run_episode`**. Khusus XSS,
`run_episode` melompati deteksi HTTP dan langsung ke browser — `/rest/track-order`
membalas JSON sehingga `served_as_html` False dan `analyze()` selalu "none",
padahal vektornya dieksekusi di `/#/track-result`. Benchmark yang keluar terlalu
awal melaporkan recall XSS = 0 secara palsu.

**Jangan klaim skor 1.0 sebagai bukti detektor sempurna.** Konfirmasi manual
memakai mekanisme yang sama dengan sistem (kontrol-diferensial + DOM), sehingga
kesepakatan oracle↔detektor tidak independen penuh. Yang sah diklaim: nol false
positive pada 60 aksi berlabel negatif + konsistensi terhadap ground truth
terkurasi. `caveat` di `detector_benchmark.json` menyatakan ini.

46 dari 120 aksi berlabel `unknown` (bukan `none`) secara sengaja: endpoint
berpermukaan `sql`/`file` di luar daftar positif tidak diasumsikan aman, supaya
specificity tidak ikut mengembang. `KNOWN_SAFE_ENDPOINTS = {2, 5, 6, 7}`.

### Hyperparameter DQN berbeda dari Q-Learning — dengan alasan

`DQN_EPSILON_DECAY = 0.9965` (bukan `EPSILON_DECAY = 0.90` milik QL). Dengan
decay 0.90, eps mentok di 0.1 pada **episode 22**, jadi 98% anggaran berjalan
hampir deterministik; karena `policy_net` diinisialisasi acak, argmax Q condong
ke satu index dan policy stuck — run sebelumnya membuang 40% budget ke `ep2`
yang bukan lokasi vuln, dan hanya menemukan 10 dari 14 aksi. Decay 0.9965
menurunkan eps ke 0.1 sekitar episode 1000. Nilai TIDAK dibagi dengan QL:
perbandingan tetap adil bila masing-masing agent memakai setting eksplorasi
yang wajar untuk algoritmanya. Nilai lain ada di config: `DQN_LR`,
`DQN_BATCH_SIZE`, `DQN_HIDDEN_DIM`, `DQN_REPLAY_CAPACITY`,
`DQN_TARGET_UPDATE_INTERVAL`.

### Human prior yang wajib disclose di tesis

`payloads.json` dan gating `surface` di `config.py` ditulis manusia yang sudah
tahu struktur Juice Shop. Ini **human prior, bukan data leakage** — agent tetap
harus memilih payload yang tepat dan setiap temuan tetap wajib lolos quality
gate. Declare eksplisit; jangan klaim prosesnya fully otomatis.
