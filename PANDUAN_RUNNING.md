# 📖 Panduan Menjalankan Sistem RL Web Pentest

Panduan langkah demi langkah untuk menjalankan sistem **Automated Web Penetration Testing**
menggunakan Q-Learning / DQN terhadap OWASP Juice Shop.

---

## ⚙️ Prasyarat

Pastikan sudah terinstall:
- **Python** (dengan `.venv` di folder project)
- **Node.js** v18+ (untuk menjalankan Juice Shop lokal)
- Folder `juice-shop/` sudah ada di dalam project

---

## 🖥️ Langkah 1 — Jalankan Juice Shop (Terminal 1)

Buka terminal pertama, lalu jalankan:

```powershell
cd "C:\Users\Kevin Setiawan\OneDrive\Desktop\Tugas Akhir\juice-shop"
node build/app
```

Tunggu hingga muncul pesan:
```
info: Server listening on port 3000
```

> ⚠️ **Jangan tutup terminal ini.** Juice Shop harus tetap berjalan selama training berlangsung.

### Jika muncul error `Port 3000 is in use`:
```powershell
# Kill proses yang memakai port 3000
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process -Force

# Lalu jalankan ulang
node build/app
```

---

## 🚀 Langkah 2 — Jalankan Pipeline Training (Terminal 2)

Buka **terminal baru** (Terminal 1 tetap terbuka), lalu:

```powershell
cd "C:\Users\Kevin Setiawan\OneDrive\Desktop\Tugas Akhir"
.venv\Scripts\activate.ps1
```

> Prompt akan berubah menjadi `(.venv) PS C:\...\Tugas Akhir>`

---

## 🤖 Pipeline Q-Learning (Utama)

Jalankan **satu per satu**, tunggu setiap perintah selesai:

### Step 1 — Training
```powershell
python rl_pentest\main.py
```
- ⏱️ Durasi: ~1-2 menit (200 episodes)
- 📁 Output: `rl_pentest/results/log_ql.csv`, `rl_pentest/results/summary_ql.json`
- 📁 Q-Table: `rl_pentest/qtable/q_table.json`

### Step 2 — Visualisasi Hasil
```powershell
python visualize_results.py ql
```
- 📁 Output: `figures/cumulative_reward_ql.png`, `figures/request_count_efficiency_ql.png`, `figures/q_table_heatmap_ql.png`

### Step 3 — Perbandingan dengan ZAP
```powershell
python zap_comparison.py
```
- 📁 Output: `zap_comparison_report.json`

---

## 🧠 Pipeline DQN (Opsional)

```powershell
# Training DQN
python rl_pentest\train_dqn.py

# Visualisasi DQN
python visualize_results.py dqn
```
- 📁 Model: `rl_pentest/qtable/dqn_model.pt`
- 📁 Log: `rl_pentest/results/log_dqn.csv`

---

## 🧪 Unit Test (Opsional)

```powershell
python test_agent.py
```
Menjalankan 7 test class: QL agent, reward, payload generator, response analyzer, DQN.

---

## 📊 Dashboard Streamlit (Opsional)

```powershell
streamlit run rl_pentest\dashboard.py
```
Buka browser di `http://localhost:8501`

---

## 📁 Ringkasan Output yang Dihasilkan

| Artifact | Lokasi |
|----------|--------|
| QL Q-Table | `rl_pentest/qtable/q_table.json` |
| QL Training Log | `rl_pentest/results/log_ql.csv` |
| QL Summary | `rl_pentest/results/summary_ql.json` |
| DQN Model | `rl_pentest/qtable/dqn_model.pt` |
| DQN Training Log | `rl_pentest/results/log_dqn.csv` |
| DQN Summary | `rl_pentest/results/summary_dqn.json` |
| Figures | `figures/*_ql.png` / `figures/*_dqn.png` |
| ZAP Comparison | `zap_comparison_report.json` |

---

## ⚡ Copy-Paste Siap Pakai

### Terminal 1 — Juice Shop
```powershell
cd "C:\Users\Kevin Setiawan\OneDrive\Desktop\Tugas Akhir\juice-shop"
node build/app
```

### Terminal 2 — Full Q-Learning Pipeline
```powershell
cd "C:\Users\Kevin Setiawan\OneDrive\Desktop\Tugas Akhir"
.venv\Scripts\activate.ps1
python rl_pentest\main.py
python visualize_results.py ql
python zap_comparison.py
```

---

## ❗ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `Port 3000 is in use` | `Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess \| Stop-Process -Force` |
| `ModuleNotFoundError` | Pastikan `.venv` aktif: `.venv\Scripts\activate.ps1` |
| `ConnectionRefusedError` ke localhost:3000 | Juice Shop belum jalan, pastikan `node build/app` sudah running di Terminal 1 |
| `summary_ql.json not found` di `zap_comparison.py` | Jalankan `main.py` dulu sebelum `zap_comparison.py` |
| `visualize_results.py` error | Jalankan `main.py` dulu agar `log_ql.csv` ada |
