# Automated Web Penetration Testing Berbasis Reinforcement Learning
**Tugas Akhir — Integrasi Reinforcement Learning dalam Automated Web Penetration Testing: Studi Kasus OWASP Juice Shop**

Dua pendekatan agent: **Q-Learning** (`rl_pentest/main.py`) dan **Deep Q-Network (DQN)** (`rl_pentest/train_dqn.py`), dievaluasi terhadap **OWASP ZAP**.

---

## Arsitektur Sistem

```
┌──────────────────────────────────────────────────────────────┐
│               main.py / train_dqn.py (Training Loop)          │
│  Episode 1..N                                                 │
│  ┌──────────┐   action    ┌──────────────────────────────┐   │
│  │  Agent   │ ──────────► │        Environment            │   │
│  │(Q-Table/ │             │  ┌────────────────────────┐   │   │
│  │   DQN)   │             │  │   pentest_engine       │   │   │
│  │  learn() │ ◄────────── │  │  (HTTP GET & POST)     │   │   │
│  └──────────┘  (s',r)     │  └──────────┬─────────────┘   │   │
│                           │             │ response           │   │
│                           │  ┌──────────▼─────────────┐   │   │
│                           │  │    analyzer.py          │   │   │
│                           │  │  - analyze_response()   │   │   │
│  training_loop.py         │  │  - baseline per endpoint│   │   │
│  - run_episode            │  │  - verifikasi "hello"   │   │   │
│  - probe baseline         │  └──────────┬─────────────┘   │   │
├───────────────────────────┤             │ state (8-dim)   │   │
│                           │  ┌──────────▼─────────────┐   │   │
│                           │  │   Reward Computation    │   │   │
│                           │  │  +50 / +10 / -1 / -5    │   │   │
│                           │  └────────────────────────┘   │   │
│                           └──────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Sumber kebenaran kode: `rl_pentest/config.py` (8 endpoint: 5 GET, 3 POST; 11 payload → **88 aksi**).

---

## Komponen Sistem

| File | Peran | Keterangan |
|------|-------|------------|
| `rl_pentest/` | Produk Akhir | Paket modular (agent, engine, analyzer, reward) |
| `rl_pentest/agent/q_learning_agent.py` | RL Agent QL | Q-Learning epsilon-greedy, optimistic init |
| `rl_pentest/agent/dqn_agent.py` | RL Agent DQN | DQN dengan replay buffer + target network |
| `rl_pentest/training_loop.py` | Shared loop | `run_episode`, verifikasi false positive, probe baseline (dipakai QL & DQN) |
| `rl_pentest/main.py` | Training QL | Orkestrasi training Q-Learning |
| `rl_pentest/train_dqn.py` | Training DQN | Orkestrasi training DQN |
| `rl_pentest/config.py` | Konfigurasi | Hyperparameter, target, path |
| `rl_pentest/reward/reward_system.py` | Reward | Komputasi reward 4 tier + length bonus |
| `rl_pentest/analyzer/response_analyzer.py` | Analyzer | Deteksi vuln + state features + baseline per endpoint |
| `rl_pentest/engine/http_client.py` | HTTP Module | Eksekusi HTTP GET/POST |
| `rl_pentest/engine/payload_generator.py` | Payload | Mapping aksi → (payload, endpoint) |
| `visualize_results.py` | Visualisasi | Generate grafik untuk Bab 4 (`ql`/`dqn`) |
| `zap_comparison.py` | Komparasi | Q-Learning vs ZAP (2 endpoint bersama) |
| `test_agent.py` | Unit Tests | Pengujian regresi otomatis |

---

## State Representation (8 Dimensi)

```python
state = (
    status_category,      # '2xx' | '3xx' | '4xx' | '5xx' | 'error'
    length_category,      # 0 (0-1499) | 1 (1500-2499) | 2 (2500-3499) | 3 (3500+)
    error_flag,           # 1 jika ada keyword error SQL
    reflected_flag,       # 1 jika payload tercermin di response
    vuln_indicator,       # 1 jika vulnerability terdeteksi
    endpoint_index,       # 0..7 (indeks endpoint)
    response_time_category,  # 0 cepat | 1 medium | 2 lambat
    content_type_category,   # 0 json | 1 html | 2 text | 3 xml | 4 other
)
```

DQN meng-encode state ini menjadi vektor 28 dimensi (one-hot) lewat `encode_state()` di `agent/dqn_agent.py`.

---

## Action Space (88 Aksi)

| Kategori | Jumlah | Contoh Payload |
|----------|--------|----------------|
| SQL Injection | 4 | `' OR '1'='1`, `' UNION SELECT NULL--`, `' OR SLEEP(5)--`, login JSON |
| Reflected XSS | 3 | `<script>alert(document.domain)</script>`, `<img src=x onerror=...>`, review JSON |
| Fuzzing | 4 | `../../../etc/passwd`, fuzz panjang, `%s%s%s%s`, `admin%00` |

Encoding aksi: `endpoint = action // 11`, `payload = action % 11`.
Sumber: `rl_pentest/data/payloads.json`

---

## Reward System (Base + Length Bonus)

**Reward = Base (vuln/anomali/normal/error) + Length Bonus**

| Kondisi | Base | Length Bonus (per kategori) |
|---------|------|---------------------------|
| Vulnerability detected | **+50** | Cat 0: 0, Cat 1: 0, Cat 2: +5, Cat 3: +10 |
| Anomaly indication | **+10** | Cat 0: 0, Cat 1: 0, Cat 2: +5, Cat 3: +10 |
| Normal request | **-1** | Cat 0: 0, Cat 1: 0, Cat 2: +5, Cat 3: +10 |
| Hard failure | **-5** | (no length bonus) |

**Verifikasi false positive**: setiap temuan dikirim ulang payload benign `"hello"` ke endpoint yang sama; jika benign juga terdeteksi, reward diturunkan ke **+10 (anomali)**.

**Baseline per endpoint**: sebelum training, panjang respons benign di-probe untuk tiap endpoint; `significant_change` dihitung terhadap baseline endpoint tersebut (bukan konstanta global) agar deteksi tidak terinflasi.

---

## Q-Learning Update Rule

```
Q(s, a) ← Q(s, a) + α [ r + γ · max_a' Q(s', a') − Q(s, a) ]

α (learning rate)   = 0.1
γ (discount factor) = 0.9
ε (initial)         = 1.0
ε_min               = 0.1
ε_decay             = 0.90 (per episode)
```

---

## Cara Menjalankan

### Prasyarat
- OWASP Juice Shop (atau target setara) aktif di `http://localhost:3000`
  ```bash
  docker run --rm -p 3000:3000 bkimminich/juice-shop
  ```
- Python virtual environment aktif + `pip install -r rl_pentest\requirements.txt`

### 1. Training
- **Q-Learning** (output `log_ql.csv`, `summary_ql.json`, `q_table.json`):
  ```bash
  python rl_pentest\main.py
  ```
- **DQN** (output `log_dqn.csv`, `summary_dqn.json`, `dqn_model.pt`):
  ```bash
  python rl_pentest\train_dqn.py
  ```

Kedua agent memakai file output terpisah sehingga hasil tidak saling menimpa.

### 2. Visualisasi (untuk Bab 4)
```bash
python visualize_results.py ql     # atau 'dqn'
```
Output: folder `figures/` menyimpan figure per-agent (`*_ql.png`/`*_dqn.png`): Cumulative Reward & Request Count Efficiency untuk tiap agent (+ Q-Table heatmap untuk QL) — hasil QL dan DQN tidak saling menimpa.

### 3. Komparasi ZAP
- **Cara A (Literatur Benchmark):** `python zap_comparison.py` — memakai data Q-Learning (`summary_ql.json`/`log_ql.csv`) dan membandingkan dengan laporan ZAP controlled scan bila ada, fallback ke literatur (Sahu et al., 2023).
- **Cara B (Live/Controlled Scan):** jalankan `python zap_controlled_scan.py` (butuh ZAP daemon di `localhost:8080`), lalu `python zap_comparison.py`.

### 4. Ekspor aset & sinkron naskah ke Overleaf
```bash
python scripts/export_thesis_assets.py
powershell -ExecutionPolicy Bypass -File thesis\watch.ps1   # sinkron otomatis saat file naskah berubah
```
`thesis/` adalah nested repo dengan remote `overleaf` — file naskah yang diedit
di VS Code otomatis commit + pull + push ke project Overleaf Anda saat watcher
berjalan (atau `thesis\sync.ps1` untuk manual). Login sekali via Git Credential
Manager (email Overleaf + Git token). Setup lengkap di `thesis/README.md`.

Perbandingan utama memakai **2 endpoint yang sama** antara Q-Learning dan ZAP (`/rest/products/search?q=` dan `/ftp/`) agar adil.

### 4. Unit Tests
```bash
python test_agent.py
```

### 5. Dashboard
```bash
streamlit run rl_pentest\dashboard.py
```
Dashboard punya pilihan agent (Q-Learning / DQN).

---

## Output Files

| File | Isi |
|------|-----|
| `rl_pentest/results/log_ql.csv` | Log per-step agent Q-Learning |
| `rl_pentest/results/summary_ql.json` | Ringkasan evaluasi Q-Learning |
| `rl_pentest/results/log_dqn.csv` | Log per-step agent DQN |
| `rl_pentest/results/summary_dqn.json` | Ringkasan evaluasi DQN |
| `rl_pentest/qtable/q_table.json` | Q-Table hasil training QL |
| `rl_pentest/qtable/dqn_model.pt` | Model PyTorch DQN |
| `figures/*_ql.png` / `*_dqn.png` | Grafik cumulative reward & efisiensi per agent (+ heatmap QL) |
| `zap_comparison_report.json` | Laporan komparasi vs ZAP |
| `thesis/figures/*` , `thesis/data/*` | Aset untuk naskah (tersinkron ke Overleaf) |

Catatan: file lama `log.csv` / `summary.json` tidak lagi ditulis; path tersebut hanya alias ke varian Q-Learning.

---

## Catatan Akademis

- **Detection Rate** = total_vuln / total_requests (bukan "precision" ML — lihat `summary_ql.json.precision`).
- **Metrik jujur jumlah request**: `total_requests` hanya menghitung request payload. Request verifikasi benign (`verification_requests`), probe baseline (`baseline_probe_requests`), dan total keseluruhan (`total_requests_with_verification`) dicatat terpisah di summary.
- **Perbandingan ZAP**: subset 2 endpoint bersama (`/rest/products/search?q=`, `/ftp/`) untuk menghindari perbandingan scope yang tidak adil; keterbatasan lain dicantumkan di `limitations` pada laporan.
- **Produk akhir** berada di folder `rl_pentest/` sebagai paket modular.
- **Reward System** mengacu Tabel 3.5 proposal: +50 (vuln), +10 (anomali), -1 (normal), -5 (gagal).