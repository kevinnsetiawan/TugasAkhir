# 🚀 Panduan Running RL Pentest - Q-Learning & DQN

Panduan lengkap untuk menjalankan training, visualisasi, dan perbandingan sistem RL-based web penetration testing terhadap OWASP Juice Shop.

---

## 📋 Prasyarat

1. **Python 3.9+** dengan virtual environment aktif
2. **OWASP Juice Shop** berjalan di `http://localhost:3000`
3. **PowerShell** (Windows) dengan encoding UTF-8

---

## ⚙️ Setup Awal (Sekali Saja)

```powershell
# 1. Pindah ke folder root project
cd "C:\Users\Kevin Setiawan\OneDrive\Desktop\Tugas Akhir"

# 2. Aktifkan virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Set encoding UTF-8 untuk box-drawing characters
$env:PYTHONIOENCODING='utf-8'

# 4. Install dependencies (jika belum)
pip install -r rl_pentest\requirements.txt
python -m playwright install chromium

# 5. Jalankan Juice Shop (terminal terpisah)
# Opsi A: Docker (preferred)
docker run --rm -p 3000:3000 bkimminich/juice-shop

# Opsi B: Source code lokal (jika Docker unavailable)
cd juice-shop
npm start
```

---

## 🎯 Training Pipeline

### 1️⃣ Training Q-Learning

```powershell
# Running Q-Learning (1585 episode, ~3-4 menit)
python rl_pentest\main.py
```

**Output yang muncul:**
- Banner ASCII "CyberFortress Q-Learning"
- Progress bar setiap 50 episode
- Notifikasi real-time saat vuln ditemukan
- **3 Tabel ASCII** di akhir:
  1. **DAFTAR KERENTANAN TERVERIFIKASI** (14 vuln)
  2. **DISTRIBUSI PERMINTAAN PER ENDPOINT** (8 endpoint)
  3. **RINGKASAN EKSEKUSI** (anggaran/temuan/efisiensi)

**Hasil tersimpan di:**
- `rl_pentest/results/log_ql.csv` — log per episode
- `rl_pentest/results/summary_ql.json` — metrik agregat
- `rl_pentest/qtable/q_table.json` — Q-table final

**Angka kunci (expected):**
- 14 vuln terverifikasi (6 SQLi, 5 XSS, 3 Fuzz)
- 5 lokasi unik `(endpoint, class)`
- Reward kumulatif ~3793
- 787 episode untuk menemukan semua vuln
- 23 state unik dalam Q-table

---

### 2️⃣ Training DQN

```powershell
# Running DQN (1585 episode, ~4-5 menit)
python rl_pentest\train_dqn.py
```

**Output yang muncul:**
- Banner ASCII "DQN"
- Info arsitektur neural net (MLP 28-X-120)
- Progress bar + epsilon decay + loss monitoring
- **3 Tabel ASCII** yang sama dengan QL

**Hasil tersimpan di:**
- `rl_pentest/results/log_dqn.csv`
- `rl_pentest/results/summary_dqn.json`
- `rl_pentest/qtable/dqn_model.pt` — PyTorch model checkpoint

**Angka kunci (expected):**
- 12 vuln terverifikasi (6 SQLi, 4 XSS, 2 Fuzz)
- 5 lokasi unik
- Reward kumulatif ~10209
- 443 episode untuk menemukan semua vuln
- Epsilon decay: 1.0 → 0.1 (decay 0.9965, bukan 0.90 seperti QL)

---

## 📊 Visualisasi Hasil

### Q-Learning Visualization

```powershell
python visualize_results.py ql
```

**Output:**
- 3 tabel ASCII (sama dengan training output)
- **Figures generated** (disimpan di `figures/`):
  - `cumulative_reward_ql.png` — grafik reward kumulatif
  - `request_count_efficiency_ql.png` — request vs vuln discovery
  - `q_table_heatmap_ql.png` — **heatmap Q-values** (log-scale, sparse labels, red boxes pada max Q per state)

### DQN Visualization

```powershell
python visualize_results.py dqn
```

**Output:**
- 3 tabel ASCII
- **Figures generated**:
  - `cumulative_reward_dqn.png`
  - `request_count_efficiency_dqn.png`
  - (DQN tidak ada heatmap karena neural net, bukan Q-table)

---

## ⚔️ Perbandingan dengan ZAP

### ZAP Controlled Scan (Optional)

Jika ZAP daemon berjalan di `localhost:8080`:

```powershell
python zap_controlled_scan.py
```

Hasil disimpan di `dataset/zap/zap_controlled_report.json`.

### Comparison Report

```powershell
# Bandingkan QL vs ZAP (2 endpoint shared: search & /ftp/)
python zap_comparison.py
```

**Output:**
- JSON report: `dataset/comparison/zap_comparison_report.json`
- Comparison table: karakteristik sistem, temuan indikatif, apples-to-apples efficiency
- **Angka expected**: QL 6.46× lebih efisien (122.6 req/vuln vs 792.5 req/vuln)

---

## 🧪 Testing & Benchmarking

### Unit Tests

```powershell
# Jalankan semua test (QL, DQN, reward, analyzer, metrics, verifier)
python test_agent.py
```

### Detector Benchmark

```powershell
# Evaluasi ResponseAnalyzer (precision/recall/F1) tanpa agent RL
python benchmark_detector.py
```

**Output:** `rl_pentest/results/detector_benchmark.json`

Skor expected (dengan caveat oracle circularity):
- Precision: 1.0 (0 false positive)
- Recall: 1.0 (semua 14 vuln terdeteksi)
- F1: 1.0
- Specificity: 1.0 (0 false positive dari 60 negative)

**Caveat**: Ground truth dibuat dengan mekanisme yang sama (control-differential + DOM execution), sehingga skor sempurna bukan bukti independen.

---

## 🎨 Contoh Output Terminal (dengan UTF-8)

```
================================================================================
  _____      _               ______         _
 / ____|    | |             |  ____|       | |
| |    _   _| |__   ___ _ __| |__ ___  _ __| |_ _ __ ___  ___ ___
| |   | | | | '_ \ / _ \ '__|  __/ _ \| '__| __| '__/ _ \/ __/ __|
| |___| |_| | |_) |  __/ |  | | | (_) | |  | |_| | |  __/\__ \__ \
 \_____\__, |_.__/ \___|_|  |_|  \___/|_|   \__|_|  \___||___/___/
        __/ |
       |___/
  ~~ CyberFortress :: Reinforcement Learning Autonomous Web Pentest :: Q-Learning ~~
================================================================================

  21:39:59 [+] TARGET       : http://localhost:3000
  21:39:59 [+] BUDGET       : 1585 episodes (1 episode = 1 request payload)
  21:39:59 [+] ACTIONS      : 120 (8 endpoint x 15 payload)
  ...

┌────────────────────────────────────────────────────────────────────────────┐
│                DAFTAR KERENTANAN TERVERIFIKASI (14 TEMUAN)                 │
├────┬─────────┬──────────────────────────┬──────────────────┬──────────────┤
│ No │ Episode │ Endpoint                 │ Kategori         │ Payload      │
├────┼─────────┼──────────────────────────┼──────────────────┼──────────────┤
│  1 │       1 │ /rest/products/search    │ SQL Injection    │ ' OR SLEEP.. │
│  2 │       5 │ /rest/products/search    │ SQL Injection    │ ' OR '1'='1  │
...
└────┴─────────┴──────────────────────────┴──────────────────┴──────────────┘
```

---

## ⚠️ Troubleshooting

### Box-drawing characters tampil sebagai `Γöé`?

```powershell
# Set encoding permanent di PowerShell profile
Add-Content $PROFILE "`n`$env:PYTHONIOENCODING='utf-8'"

# Restart PowerShell atau reload
. $PROFILE
```

### ModuleNotFoundError: No module named 'playwright'?

```powershell
pip install -r rl_pentest\requirements.txt
python -m playwright install chromium
```

### Juice Shop error: port 3000 already in use?

```powershell
# Cek proses yang pakai port 3000
Get-NetTCPConnection -LocalPort 3000

# Stop Docker container lama
docker ps
docker stop <container_id>
```

### Script error: "can't open file 'rl_pentest\main.py'"?

Pastikan Anda di **folder root** project, bukan di `juice-shop/`:

```powershell
# Cek lokasi sekarang
Get-Location

# Jika masih di juice-shop/, pindah ke parent
cd ..
```

---

## 📁 Struktur Output Lengkap

```
Tugas Akhir/
├── rl_pentest/
│   ├── results/
│   │   ├── log_ql.csv               # ✅ Q-Learning episode log
│   │   ├── summary_ql.json          # ✅ Q-Learning metrics
│   │   ├── log_dqn.csv              # ✅ DQN episode log
│   │   ├── summary_dqn.json         # ✅ DQN metrics
│   │   └── detector_benchmark.json  # ✅ Detector eval (P/R/F1)
│   └── qtable/
│       ├── q_table.json             # ✅ Q-table (120 actions × 23 states)
│       └── dqn_model.pt             # ✅ PyTorch DQN checkpoint
├── dataset/                         # Mirror of rl_pentest/results/
│   ├── ql/
│   ├── dqn/
│   ├── zap/
│   ├── comparison/
│   └── qtable/
├── figures/
│   ├── cumulative_reward_ql.png     # ✅ Reward graph QL
│   ├── cumulative_reward_dqn.png    # ✅ Reward graph DQN
│   ├── request_count_efficiency_ql.png   # ✅ Efficiency QL
│   ├── request_count_efficiency_dqn.png  # ✅ Efficiency DQN
│   ├── q_table_heatmap_ql.png       # ✅ Q-table heatmap (log-scale, sparse)
│   └── vuln_breakdown_ql_zap.png    # ✅ ZAP comparison bar chart
└── newupdate.zip                    # ✅ Archive semua file penting
```

---

## 📝 Catatan untuk Demo Supervisor

1. **Output terminal sudah profesional** — 3 tabel ASCII box-drawing menggantikan key-value list
2. **Heatmap Q-table sudah scientific** — log-scale colormap, sparse labels (every 5th), red boxes pada max Q
3. **Data sudah konsisten** — `dataset/` vs `rl_pentest/results/` sudah sync
4. **Comparison tables di Bab 4** sudah terstruktur: karakteristik sistem, temuan indikatif, apples-to-apples
5. **Metrik wajib declare** — semua angka IN-SAMPLE, bukan held-out test set
6. **Hyperparameter disclosure** — DQN epsilon decay (0.9965) berbeda dari QL (0.90) dengan justifikasi exploration
7. **Human prior disclosure** — `payloads.json` + surface gating ditulis manusia (bukan fully autonomous)

---

## 🎓 Checklist Pre-Defense

- [ ] Jalankan `python rl_pentest\main.py` → verifikasi 14 vuln QL
- [ ] Jalankan `python rl_pentest\train_dqn.py` → verifikasi 12 vuln DQN
- [ ] Jalankan `python visualize_results.py ql` → cek heatmap log-scale rapi
- [ ] Jalankan `python visualize_results.py dqn` → cek cumulative reward DQN
- [ ] Jalankan `python zap_comparison.py` → verifikasi efficiency 6.46×
- [ ] Jalankan `python benchmark_detector.py` → verifikasi P/R/F1 = 1.0 (dengan caveat)
- [ ] Buka `Template.../07_bab4.tex` → cek 3 tabel comparison
- [ ] Screenshot terminal output dengan box-drawing (untuk backup slide)
- [ ] Siapkan jawaban: "Mengapa epsilon decay QL 0.90 vs DQN 0.9965?" → exploration window berbeda
- [ ] Siapkan jawaban: "Apakah ini zero-knowledge?" → TIDAK, payloads & surface gating human-designed

---

**Semua sistem sudah defense-ready!** 🚀🎓

Untuk pertanyaan lebih lanjut, hubungi: Kevin Setiawan | Tugas Akhir S1 | Telkom University Surabaya
