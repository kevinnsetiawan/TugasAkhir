# Automated Web Penetration Testing Berbasis Q-Learning
**Tugas Akhir — Integrasi Reinforcement Learning dalam Automated Web Penetration Testing: Studi Kasus OWASP Juice Shop**

---

## Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────┐
│                     main.py (Training Loop)                  │
│  Episode 1..N                                               │
│  ┌──────────┐   action    ┌─────────────────────────────┐  │
│  │  Agent   │ ──────────► │       Environment           │  │
│  │(Q-Table) │             │  ┌──────────────────────┐   │  │
│  │          │ ◄────────── │  │  pentest_engine.py   │   │  │
│  │  learn() │  (s',r)     │  │  (HTTP GET Request)  │   │  │
│  │  Bellman │             │  └──────────┬───────────┘   │  │
│  └──────────┘             │             │ response       │  │
│                           │  ┌──────────▼───────────┐   │  │
│                           │  │    analyzer.py        │   │  │
│                           │  │  - analyze_response() │   │  │
│                           │  │  - get_error_ind()    │   │  │
│                           │  │  - get_reflection()   │   │  │
│                           │  │                           │  └──────────┬───────────┘   │  │
│                           │             │ state (5-dim)  │  │
│                           │  ┌──────────▼───────────┐   │  │
│                           │  │   Reward Computation  │   │  │
│                           │  │  +50 / +10 / -1 / -5  │   │  │
│                           │  └──────────────────────┘   │  │
│                           └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Komponen Sistem

| File | Peran | Keterangan |
|------|-------|------------|
| `rl_pentest/` | Produk Akhir | Paket modular utama (agent, engine, analyzer, reward) |
| `rl_pentest/agent/q_learning_agent.py` | RL Agent | Q-Learning dengan epsilon-greedy |
| `rl_pentest/main.py` | Training Loop | Orkestrasi training RL |
| `rl_pentest/config.py` | Konfigurasi | Hyperparameter, target, dan path |
| `rl_pentest/reward/reward_system.py` | Reward | Komputasi reward 4 tier |
| `rl_pentest/analyzer/response_analyzer.py` | Analyzer | Deteksi vuln + state features |
| `rl_pentest/engine/http_client.py` | HTTP Module | Eksekusi HTTP GET request |
| `visualize_results.py` | Visualisasi | Generate grafik untuk Bab 4 |
| `zap_comparison.py` | Komparasi | Q-Learning vs ZAP |
| `test_agent.py` | Unit Tests | Pengujian regresi otomatis |

---

## State Representation (5 Dimensi)

```python
state = (
    status_category,      # '2xx' | '3xx' | '4xx' | '5xx' | 'error'
    length_category,      # 0 (0-1499) | 1 (1500-2499) | 2 (2500-3499) | 3 (3500+)
    error_flag,           # 1 jika ada keyword error SQL, else 0
    reflected_flag,       # 1 jika payload tercermin di response, else 0
    vuln_indicator,       # 1 jika vulnerability terdeteksi, else 0
)
```

---

## Action Space (10 Actions)

| ID | Nama | Kategori | Payload |
|----|------|----------|---------|
| 0 | sqli_basic | sqli | `' OR '1'='1` |
| 1 | sqli_union | sqli | `' UNION SELECT NULL--` |
| 2 | sqli_time | sqli | `' OR SLEEP(5)--` |
| 3 | xss_script | xss | `<script>alert('test')</script>` |
| 4 | xss_img | xss | `<img src=x onerror=alert('xss')>` |
| 5 | xss_event | xss | `<svg/onload=alert('xss')>` |
| 6 | fuzz_unicode | fuzzing | `\"'><script>\n` |
| 7 | fuzz_long | fuzzing | `AAAA...` (100x A) |
| 8 | fuzz_format | fuzzing | `%s%s%s%s%s` |
| 9 | fuzz_brutal | fuzzing | `<iframe src=javascript:alert('xss')>` |

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

Length categories: 0 (0-1499), 1 (1500-2499), 2 (2500-3499), 3 (3500+)

---

## Q-Learning Update Rule

```
Q(s, a) ← Q(s, a) + α [ r + γ · max_a' Q(s', a') − Q(s, a) ]

α (learning rate)   = 0.1
γ (discount factor) = 0.9
ε (initial)         = 1.0
ε_min               = 0.1
ε_decay             = 0.95 (per episode)
```

---

## Cara Menjalankan

### Prasyarat
- OWASP Juice Shop berjalan di `http://localhost:3000`
- Python virtual environment aktif

### 1. Training Utama
```bash
python rl_pentest\main.py
```
Output: `rl_pentest/results/log.csv`, `rl_pentest/results/summary.json`, `rl_pentest/qtable/q_table.json`

### 2. Visualisasi (untuk Bab 4)
```bash
python visualize_results.py
```
Output: folder `figures/` berisi grafik Cumulative Reward & Request Count Efficiency

### 3. Komparasi ZAP
Anda dapat melakukan komparasi menggunakan dua cara:
- **Cara A (Literatur Benchmark):** Cukup jalankan `python zap_comparison.py`. Script otomatis menggunakan data benchmark literatur jika file laporan riil tidak terdeteksi.
- **Cara B (Live Scan OWASP ZAP):**
  1. Jalankan pemindaian (Active Scan) pada OWASP Juice Shop (`http://localhost:3000`) menggunakan OWASP ZAP GUI.
  2. Ekspor hasil pemindaian ke format JSON: **Report -> Generate Report -> Template: Traditional JSON Report**.
  3. Simpan file laporan tersebut dengan nama `zap_report.json` di direktori `rl_pentest/`.
  4. Jalankan script `python zap_comparison.py`.

Output: `zap_comparison_report.json`

### 4. Unit Tests
```bash
python test_agent.py
```

### 5. Dashboard
```bash
streamlit run rl_pentest\dashboard.py
```

---

## Output Files

| File | Isi |
|------|-----|
| `rl_pentest/results/log.csv` | Log per-step RL agent |
| `rl_pentest/results/summary.json` | Ringkasan evaluasi akhir |
| `rl_pentest/qtable/q_table.json` | Q-Table hasil training |
| `figures/cumulative_reward.png` | Grafik Cumulative Reward |
| `figures/request_count_efficiency.png` | Grafik efisiensi Request Count |
| `zap_comparison_report.json` | Laporan komparasi vs ZAP |

---

## Catatan Akademis

- **Detection Rate** = total_vuln / total_episodes (bukan "precision" ML)
- **Perbandingan ZAP** menggunakan nilai dari literatur (Sahu et al., 2023), bukan live execution
- **Produk akhir** berada di folder `rl_pentest/` sebagai paket modular
- **Reward System** mengacu Tabel 3.5 proposal: +50 (vuln), +10 (anomali), -1 (normal), -5 (gagal)
