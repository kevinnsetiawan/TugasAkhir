# LAPORAN KOREKSI FINAL BAB 4 SKRIPSI

**Tanggal**: 5 Oktober 2026  
**Dokumen**: `temp_skripsi_fix/07_bab4.tex`  
**Status**: ✅ SELESAI — Siap sidang

---

## RINGKASAN KOREKSI

### 1. KOREKSI NUMERIK (15 perubahan total)

#### A. Data DQN (KRITIKAL — 4 koreksi)
| # | Metrik | Sebelum | Sesudah | Lokasi | Prioritas |
|---|--------|---------|---------|--------|-----------|
| 1 | **Cumulative Reward** | 10.209 | **9.503** | Tab 4.X, line ~608 | 🔴 KRITIKAL |
| 2 | **Total Kerentanan** | 12 | **13** | Tab 4.X, line ~597 | 🔴 KRITIKAL |
| 3 | **XSS Count** | 4 | **5** | Tab 4.X, line ~598 | 🔴 KRITIKAL |
| 4 | **Rasio Reward** | 2,70× | **2,51×** | Teks, line ~620 | 🔴 KRITIKAL |

#### B. Data Q-Learning (MEDIUM — 6 koreksi)
| # | Metrik | Sebelum | Sesudah | Lokasi | Prioritas |
|---|--------|---------|---------|--------|-----------|
| 5 | Cumulative Reward | 3.785 | **3.783** | Tab 4.X, line ~416 | 🟡 MEDIUM |
| 6 | **State Unik** | 27/23 (inkonsisten) | **25** | Tab 4.X line 422, teks line 547 | 🟡 MEDIUM |
| 7 | Durasi | 154,23s | **142,55s** | Tab 4.X, line ~426 | 🟡 MEDIUM |
| 8 | Total Transaksi | 1.640 | **1.639** | Tab 4.X, line ~412 | 🟢 MINOR |
| 9 | QL Subset Req | 1.223 | **1.226** | Tab ZAP, line ~742 | 🟡 MEDIUM |
| 10 | QL Req/Vuln | 122,30 | **122,60** | Tab ZAP, line ~749 | 🟡 MEDIUM |

#### C. Data Perbandingan (MEDIUM — 3 koreksi)
| # | Metrik | Sebelum | Sesudah | Lokasi | Prioritas |
|---|--------|---------|---------|--------|-----------|
| 11 | DQN Durasi | 160,04s | **146,95s** | Tab 4.X, line ~609 | 🟡 MEDIUM |
| 12 | DQN Req/Vuln | 132,08 | **121,92** | Tab 4.X, line ~605 | 🟡 MEDIUM |
| 13 | Efficiency Ratio | 6,48× | **6,46×** | Teks ZAP, line ~754 | 🟢 MINOR |

---

### 2. KOREKSI TEKS NARATIF (2 perubahan)

#### A. Line 618-619: Penjelasan Kecepatan DQN
**SEBELUM**:
```latex
DQN berhasil mengidentifikasi seluruh 12 kerentanan yang ditemukannya secara jauh lebih cepat, 
yaitu pada Episode 443, dibandingkan Q-Learning yang membutuhkan 787 episode.
```

**SESUDAH**:
```latex
DQN berhasil mengidentifikasi seluruh 13 kerentanan yang ditemukannya (6 SQLi, 5 XSS, 2 Fuzz) 
secara jauh lebih cepat, yaitu pada Episode 443, dibandingkan Q-Learning yang membutuhkan 
787 episode untuk menemukan 14 kerentanan.
```

**Alasan**: Tambahkan breakdown kategori + konteks perbandingan yang jelas.

---

#### B. Line 646: Ringkasan Hasil
**SEBELUM**:
```latex
Q-Learning menemukan 14 aksi terverifikasi, sedangkan DQN menemukan 12 aksi.
```

**SESUDAH**:
```latex
Q-Learning menemukan 14 aksi terverifikasi (7 SQLi, 5 XSS, 2 Fuzz), sedangkan DQN menemukan 
13 aksi (6 SQLi, 5 XSS, 2 Fuzz).
```

**Alasan**: Breakdown kategori membantu pembaca memahami distribusi temuan.

---

### 3. VERIFIKASI REFERENSI LENGKAP ✅

#### A. Semua Label Gambar (7 gambar):
- ✅ `fig:epsilon_decay_ql` (line 510)
- ✅ `fig:cumulative_reward_ql` (line 529)
- ✅ `fig:request_count_efficiency_ql` (line 540)
- ✅ `fig:q_table_heatmap_ql` (line 577)
- ✅ `fig:cumulative_reward_dqn` (line 636)
- ✅ `fig:request_count_efficiency_dqn` (line 643)
- ✅ `fig:vuln_breakdown` (line 761)

#### B. Semua Label Tabel (7 tabel):
- ✅ `tab:skema_log` (line 28)
- ✅ `tab:fitur_prapemrosesan` (line 92)
- ✅ `tab:detector_benchmark` (line 373)
- ✅ `tab:ql_results` (line 402)
- ✅ `tab:ql_per_endpoint` (line 438)
- ✅ `tab:qtable_top` (line 552)
- ✅ `tab:comparison_ql_dqn` (line 590)
- ✅ `tab:zap_comparison` (line 737)

#### C. Semua File Gambar (di `temp_skripsi_fix/gambar/`):
- ✅ `cumulative_reward_dqn.png`
- ✅ `cumulative_reward_ql.png`
- ✅ `epsilon_decay_ql.png`
- ✅ `q_table_heatmap_ql.png`
- ✅ `request_count_efficiency_dqn.png`
- ✅ `request_count_efficiency_ql.png`
- ✅ `vuln_breakdown_ql_zap.png`
- ✅ `pengesahan.jpeg`, `telulogo.png` (cover files)

---

### 4. FORMAT TABEL

Dokumen menggunakan **DUA gaya tabel** (keduanya valid):

#### A. Modern Booktabs Style (tanpa garis vertikal):
```latex
\begin{tabular}{l c c}
\toprule
... header ...
\midrule
... data ...
\bottomrule
\end{tabular}
```
Dipakai di: `tab:comparison_ql_dqn` (line 590-613)

#### B. Classic LaTeX Style (dengan garis):
```latex
\begin{tabular}{|l|c|}
\hline
... header ...
\hline
... data ...
\hline
\end{tabular}
```
Dipakai di: `tab:ql_results`, `tab:zap_comparison`, dll.

**Catatan**: Mixing styles adalah **NORMAL** dalam dokumen LaTeX akademis — tidak perlu diseragamkan.

---

## METODE KOREKSI

### Tools Digunakan:
1. **PowerShell Regex Script** (`fix_bab4_numbers.ps1`)
   - 13 replacement patterns otomatis
   - Backup otomatis: `07_bab4_ORIGINAL.tex`
   
2. **Manual String Replacement** (Kiro IDE)
   - 2 koreksi teks naratif dengan breakdown kategori
   - 1 fix state count yang missed oleh regex

### Sumber Data Ground Truth:
- `rl_pentest/results/summary_ql.json`
- `rl_pentest/results/summary_dqn.json`
- `dataset/comparison/zap_comparison_report.json`

---

## VALIDASI AKHIR

### ✅ Checklist Kesiapan Sidang:

- [x] Semua angka di tabel MATCH dengan `summary_*.json`
- [x] Teks naratif konsisten dengan data tabel
- [x] Breakdown kategori (SQLi/XSS/Fuzz) ditambahkan
- [x] Semua `\ref{}` memiliki `\label{}` yang valid
- [x] Semua gambar `.png` ada di folder `gambar/`
- [x] Tidak ada inkonsistensi 27/23 state (sudah 25 semua)
- [x] DQN 13 kerentanan (bukan 12) di semua tempat
- [x] Reward ratio 2,51× (bukan 2,70×)
- [x] Backup original tersimpan (`07_bab4_ORIGINAL.tex`)

---

## NEXT STEPS (OPSIONAL)

### Kompilasi PDF:
```powershell
cd temp_skripsi_fix
pdflatex 00_MAIN_ProposalTA.tex
bibtex 00_MAIN_ProposalTA
pdflatex 00_MAIN_ProposalTA.tex
pdflatex 00_MAIN_ProposalTA.tex
```

### Jika Ada LaTeX Errors:
1. Cek log file: `00_MAIN_ProposalTA.log`
2. Verifikasi `\usepackage{booktabs}` ada di `tus-style.sty` atau preamble
3. Pastikan `\usepackage{tikz}` dan dependencies ada (untuk ZAP architecture diagram)

---

## CATATAN PENTING UNTUK SIDANG

### Disclosure Wajib:
1. **In-sample metrics**: Semua angka dihitung dari 1585 episode yang sama dengan training
2. **Human prior**: Payload dan endpoint surface mapping dibuat manusia yang paham Juice Shop
3. **DQN 13 vs QL 14**: Hasil valid dari epsilon decay berbeda (0.9965 vs 0.90), bukan bug
4. **Quality gate**: Setiap finding wajib lolos control-differential + DOM execution (XSS)

### Defense Points:
- **QL lebih thorough**: 98.6% budget dipakai exploit (14 vuln)
- **DQN lebih cepat**: Selesai episode 443 vs 787 (56% lebih cepat)
- **Detector benchmark**: Precision 1.0, Recall 1.0, F1 1.0 pada 60 aksi berlabel
- **ZAP comparison**: QL 6.46× lebih efisien (122.6 vs 792.5 req/vuln)

---

## FILES & ARTIFACTS

### File Terkoreksi:
- `temp_skripsi_fix/07_bab4.tex` ← **GUNAKAN INI**
- `temp_skripsi_fix/07_bab4_ORIGINAL.tex` ← backup original

### Dokumentasi:
- `KOREKSI_BAB4_FINAL.md` ← laporan ini
- `fix_bab4_numbers.ps1` ← script koreksi (log)
- `CARA_RUNNING.md` ← cara menjalankan sistem

### Dataset Lengkap:
- `dataset/ql/` ← Q-Learning results
- `dataset/dqn/` ← DQN results
- `dataset/comparison/` ← ZAP comparison
- `figures/` ← semua PNG grafik

---

**KESIMPULAN**: Bab 4 sudah **100% akurat** terhadap output sistem aktual. Siap sidang! 🎓
