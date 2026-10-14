# 🔍 Panduan Lengkap: ZAP Scan dari Terminal

Panduan ini menjelaskan cara menjalankan OWASP ZAP scan terhadap Juice Shop dari terminal untuk perbandingan dengan Q-Learning & DQN.

---

## 📋 Prerequisites

### 1. Install OWASP ZAP

**Windows (Chocolatey)**:
```powershell
choco install zap
```

**Windows (Manual Download)**:
1. Download dari: https://www.zaproxy.org/download/
2. Install ke `C:\Program Files\ZAP\` (default)
3. Tambahkan ke PATH (optional)

**Verifikasi instalasi**:
```powershell
& "C:\Program Files\ZAP\Zed Attack Proxy\zap.bat" -version
```

### 2. Install Python Dependencies

```powershell
# Pastikan di folder root project
cd "C:\Users\Kevin Setiawan\OneDrive\Desktop\Tugas Akhir"
.\.venv\Scripts\Activate.ps1

# Install ZAP Python API (jika belum)
pip install python-owasp-zap-v2.4
```

---

## 🚀 Metode 1: Pakai Script Python (RECOMMENDED)

Project sudah punya `zap_controlled_scan.py` yang scan **2 endpoint shared** dengan QL/DQN (search & /ftp/).

### Step-by-Step

#### **Terminal 1: Jalankan ZAP Daemon**

```powershell
# Start ZAP in headless mode (no GUI)
& "C:\Program Files\ZAP\Zed Attack Proxy\zap.bat" `
  -daemon `
  -port 8080 `
  -config api.disablekey=true `
  -config api.addrs.addr.name=.* `
  -config api.addrs.addr.regex=true

# Tunggu sampai muncul: "ZAP is now listening on localhost:8080"
```

**Parameter penting**:
- `-daemon` → headless (tanpa GUI)
- `-port 8080` → API port (default)
- `-config api.disablekey=true` → disable API key (untuk testing lokal)
- `-config api.addrs.addr.*` → allow access dari semua IP

#### **Terminal 2: Jalankan Juice Shop**

```powershell
# Opsi A: Docker (preferred)
docker run --rm -p 3000:3000 bkimminich/juice-shop

# Opsi B: Source code lokal
cd juice-shop
npm start
```

#### **Terminal 3: Running ZAP Scan**

```powershell
# 1. Ke folder root project
cd "C:\Users\Kevin Setiawan\OneDrive\Desktop\Tugas Akhir"

# 2. Aktifkan venv
.\.venv\Scripts\Activate.ps1

# 3. Set encoding
$env:PYTHONIOENCODING='utf-8'

# 4. Jalankan controlled scan
python zap_controlled_scan.py
```

**Output yang muncul**:
```
[+] ZAP daemon terdeteksi
[+] Memulai controlled scan (2 endpoint setara RL agent)
     URL: http://localhost:3000/rest/products/search?q=
     Spider scan...
     Progress: 100%
     Active scan...
     Progress: 100%
     URL: http://localhost:3000/ftp/
     Spider scan...
     Progress: 100%
     Active scan...
     Progress: 100%
[+] Total requests: 1585
[+] Alerts ditemukan: 32
[+] Kerentanan terverifikasi (High/Medium, kategori relevan): 2
[+] Report disimpan: rl_pentest/results/zap_controlled_report.json
```

**Hasil tersimpan di**:
- `rl_pentest/results/zap_controlled_report.json`
- Atau symlink di: `dataset/zap/zap_controlled_report.json`

---

## 🎯 Metode 2: ZAP CLI Langsung (Tanpa Python)

### Quick Scan (All Pages)

```powershell
# Scan seluruh site dengan default config
& "C:\Program Files\ZAP\Zed Attack Proxy\zap.bat" `
  -cmd `
  -quickurl http://localhost:3000 `
  -quickout "zap_quickscan_report.html" `
  -quickprogress
```

**Output**: HTML report di `zap_quickscan_report.html`

### Advanced Scan dengan Context

```powershell
# Scan dengan update addon dulu
& "C:\Program Files\ZAP\Zed Attack Proxy\zap.bat" `
  -cmd `
  -addonupdate `
  -addoninstall ascanrules `
  -quickurl http://localhost:3000 `
  -quickout "zap_full_report.json" `
  -quickprogress
```

### Scan dengan Custom Config

```powershell
# Scan dengan max depth & thread control
& "C:\Program Files\ZAP\Zed Attack Proxy\zap.bat" `
  -cmd `
  -quickurl http://localhost:3000 `
  -quickout "zap_report.xml" `
  -quickprogress `
  -config spider.maxDepth=5 `
  -config spider.threadCount=5
```

---

## 🎯 Metode 3: ZAP API Manual (Python REPL)

Jika ingin kontrol penuh via Python:

```python
from zapv2 import ZAPv2
import time

# 1. Connect ke ZAP daemon
zap = ZAPv2(proxies={'http': 'http://localhost:8080', 'https': 'http://localhost:8080'})

# 2. Set target
target = 'http://localhost:3000'

# 3. Spider scan (crawl)
print('Starting spider...')
scan_id = zap.spider.scan(target)
while int(zap.spider.status(scan_id)) < 100:
    print(f'Spider progress: {zap.spider.status(scan_id)}%')
    time.sleep(2)
print('Spider completed')

# 4. Active scan (attack)
print('Starting active scan...')
scan_id = zap.ascan.scan(target)
while int(zap.ascan.status(scan_id)) < 100:
    print(f'Active scan progress: {zap.ascan.status(scan_id)}%')
    time.sleep(5)
print('Active scan completed')

# 5. Get alerts
alerts = zap.core.alerts()
print(f'Total alerts: {len(alerts)}')

# 6. Export report
import json
with open('zap_manual_report.json', 'w') as f:
    json.dump(alerts, f, indent=2)
```

---

## 📊 Metode 4: ZAP Comparison Script

Setelah scan ZAP selesai, bandingkan dengan Q-Learning:

```powershell
# Jalankan comparison (otomatis baca zap_controlled_report.json)
python zap_comparison.py
```

**Output**:
- `dataset/comparison/zap_comparison_report.json`
- Efficiency comparison: QL vs ZAP (apples-to-apples 2 endpoint)
- Bar chart: `figures/vuln_breakdown_ql_zap.png`

**Expected numbers**:
- **QL**: 1226 req / 10 vuln = **122.6 req/vuln**
- **ZAP**: 1585 req / 2 vuln = **792.5 req/vuln**
- **Efficiency**: QL **6.46× lebih efisien**

---

## ⚠️ Troubleshooting

### **Error: "Unable to connect to ZAP API"**

**Penyebab**: ZAP daemon belum jalan atau port salah.

**Solusi**:
```powershell
# 1. Cek apakah ZAP jalan
Test-NetConnection -ComputerName localhost -Port 8080

# 2. Cek process ZAP
Get-Process | Where-Object {$_.Name -like "*zap*"}

# 3. Restart ZAP daemon
# Stop dulu (Ctrl+C di terminal ZAP)
# Lalu start ulang dengan command di atas
```

### **Error: "ZAP API key required"**

**Penyebab**: API key tidak di-disable.

**Solusi**:
```powershell
# Restart ZAP dengan config tambahan
& "C:\Program Files\ZAP\Zed Attack Proxy\zap.bat" `
  -daemon `
  -port 8080 `
  -config api.disablekey=true
```

### **Error: "Target site not responding"**

**Penyebab**: Juice Shop belum jalan.

**Solusi**:
```powershell
# Cek apakah Juice Shop jalan
curl http://localhost:3000

# Jika tidak, start dulu (Docker atau npm)
docker run --rm -p 3000:3000 bkimminich/juice-shop
```

### **Scan terlalu lama (>30 menit)**

**Penyebab**: ZAP full scan semua halaman.

**Solusi**: Pakai `zap_controlled_scan.py` yang hanya scan 2 endpoint (setara RL agent).

### **Alert terlalu banyak (>100)**

**Penyebab**: ZAP melaporkan semua findings (termasuk Informational/Low).

**Solusi**: Script `zap_controlled_scan.py` sudah filter hanya:
- Risk: **High/Medium** (bukan Low/Informational)
- Category: **SQLi/XSS/Path Traversal** (bukan CSP/Header/Tech detection)

---

## 📁 Struktur Output ZAP

### **zap_controlled_report.json**

```json
{
  "scan_type": "controlled",
  "target": "http://localhost:3000",
  "urls_scanned": [
    "http://localhost:3000/rest/products/search?q=",
    "http://localhost:3000/ftp/"
  ],
  "total_requests": 1585,
  "total_alerts": 32,
  "alerts_by_risk": {
    "High": 2,
    "Medium": 5,
    "Low": 10,
    "Informational": 15
  },
  "relevant_vulnerabilities": 2,
  "vulnerabilities": {
    "sqli": 1,
    "xss": 1,
    "path": 0
  },
  "raw_alerts": [ ... ],
  "notes": "Hanya alert High/Medium kategori sqli/xss/path yang dihitung"
}
```

---

## 🎯 Best Practice untuk Laporan

### **1. Gunakan Controlled Scan (2 Endpoint)**

```powershell
python zap_controlled_scan.py
```

**Alasan**: Apples-to-apples comparison dengan QL/DQN yang juga hanya scan 2 endpoint shared.

### **2. Full Scan (8 Endpoint) - Optional**

Jika ingin tahu kemampuan ZAP di seluruh aplikasi:

```python
# Edit zap_controlled_scan.py, ganti CONTROLLED_URLS:
CONTROLLED_URLS = [
    "http://localhost:3000/rest/products/search?q=",
    "http://localhost:3000/ftp/",
    "http://localhost:3000/rest/products/1/reviews",
    "http://localhost:3000/rest/track-order/",
    "http://localhost:3000/rest/user/login",
    # ... tambahkan semua 8 endpoint
]
```

### **3. Multiple Runs untuk Confidence Interval**

```powershell
# Run 3× untuk rata-rata
for ($i=1; $i -le 3; $i++) {
    Write-Host "Run $i/3"
    python zap_controlled_scan.py
    Move-Item rl_pentest\results\zap_controlled_report.json `
              rl_pentest\results\zap_run_$i.json
    Start-Sleep -Seconds 5
}
```

---

## 📊 Checklist Pre-Defense

- [ ] ZAP daemon berjalan di `localhost:8080`
- [ ] Juice Shop berjalan di `localhost:3000`
- [ ] `zap_controlled_scan.py` berhasil scan 2 endpoint
- [ ] `zap_controlled_report.json` berisi ~1585 requests
- [ ] `zap_comparison.py` berhasil generate comparison
- [ ] Efficiency 6.46× terverifikasi (QL 122.6 vs ZAP 792.5 req/vuln)
- [ ] Screenshot ZAP output untuk slide backup

---

## 🔗 Resources

- **ZAP Official**: https://www.zaproxy.org/
- **ZAP Python API**: https://github.com/zaproxy/zap-api-python
- **ZAP Command Line**: https://www.zaproxy.org/docs/desktop/cmdline/
- **ZAP Automation**: https://www.zaproxy.org/docs/automate/

---

**🚀 ZAP scan siap untuk comparison dengan RL agent!** 🎓

Untuk pertanyaan lebih lanjut, hubungi: Kevin Setiawan | Tugas Akhir S1
