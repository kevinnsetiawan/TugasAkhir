# Paper: Automated Web Penetration Testing with Reinforcement Learning

## JISA (Elsevier, Scopus Q2) — English

| File | Deskripsi |
|------|-----------|
| `manuscript.html` | **BACA INI** — Versi HTML untuk dibaca (buka di browser) |
| `manuscript.tex` | Draft LaTeX (format elsarticle Elsevier) |
| `cover_letter.txt` | Cover letter untuk editor JISA |
| `highlights.txt` | 5 bullet highlights |
| `graphical_abstract.txt` | Deskripsi graphical abstract |
| `../figures/cumulative_reward.png` | Figure 1: Cumulative reward QL vs DQN |
| `../figures/request_count_efficiency.png` | Figure 2: Requests per vulnerability |

### Cara submit JISA (LaTeX)
```bash
# 1. Install elsarticle.cls:
#    https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions
# 2. Compile:
pdflatex manuscript.tex
pdflatex manuscript.tex
# 3. Submit ke: https://www.editorialmanager.com/jisas/
```

## RESTI (Sinta 2/Scopus) — Bahasa Indonesia

**Target:** Jurnal RESTI (Rekayasa Sistem dan Teknologi Informasi), e-ISSN 2580-0760, DOI 10.29207

| File | Deskripsi |
|------|-----------|
| `resti_paper.tex` | Naskah LaTeX untuk RESTI (Bahasa Indonesia) |
| `../figures/cumulative_reward.png` | Gambar 1: Cumulative reward QL vs DQN |
| `../figures/request_count_efficiency.png` | Gambar 2: Requests per vulnerability |

### Format RESTI
- Kertas A4, margin 2,5 cm, spasi 1,5, Times New Roman 12pt
- Judul maks. 12 kata (Bahasa Indonesia)
- Abstrak Indonesia + Inggris (masing-masing ~200 kata)
- Struktur: Pendahuluan → Metode → Hasil & Pembahasan → Kesimpulan
- Referensi: minimal 15, 80% dari jurnal bereputasi, gaya APA
- Halaman: 6–12 halaman

### Cara submit RESTI
RESTI menyediakan template Word (.docx). Gunakan `resti_paper.tex` sebagai sumber konten, lalu:
1. Unduh template RESTI dari: https://jurnal.iaii.or.id (menu Download RESTI Templates)
2. Salin konten ke template Word
3. Daftar/login di: https://jurnal.iaii.or.id/index.php/RESTI
4. Submit melalui OJS (Open Journal Systems)

### Checklist submission RESTI
- [ ] Ganti "Kevin Setiawan" dan "Advisor Name" dengan nama asli
- [ ] Ganti "kevin.setiawan@example.com" dengan email asli
- [ ] Ganti "Universitas Contoh" dengan institusi
- [ ] Generate ulang figures: `python visualize_results.py`
- [ ] Salin ke template Word RESTI (format .docx)
- [ ] Submit via OJS RESTI

## Struktur paper (kedua versi)
1. **Pendahuluan** — Latar belakang, gap, 4 kontribusi
2. **Metode Penelitian** — MDP formulation, 8-dim state, 88 actions, reward, QL & DQN
3. **Hasil dan Pembahasan** — Setup, main results, 8 tabel, 2 figure, diskusi
4. **Kesimpulan** — 4 temuan kunci, future work
