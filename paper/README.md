# Paper: Automated Web Penetration Testing with Reinforcement Learning

**Target jurnal:** Journal of Information Security and Applications (Elsevier, Scopus Q2)

## Berkas
| File | Deskripsi |
|------|-----------|
| `manuscript.html` | **BACA INI** — Versi HTML untuk dibaca (buka di browser) |
| `manuscript.tex` | Draft LaTeX untuk submission (format elsarticle Elsevier) |
| `cover_letter.txt` | Cover letter untuk editor |
| `highlights.txt` | 5 bullet highlights |
| `graphical_abstract.txt` | Deskripsi graphical abstract |
| `../figures/cumulative_reward.png` | Figure 1: Cumulative reward QL vs DQN |
| `../figures/request_count_efficiency.png` | Figure 2: Requests per vulnerability |

## Cara baca
1. Buka `manuscript.html` di browser (double-click)
2. Semua tabel, gambar, dan referensi sudah termuat

## Cara submit (LaTeX)
```bash
# 1. Install elsarticle.cls dari:
#    https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions
# 2. Compile:
pdflatex manuscript.tex
pdflatex manuscript.tex
# 3. Submit ke: https://www.editorialmanager.com/jisas/
```

## Struktur paper
1. **Introduction** — Latar belakang, gap, 4 kontribusi
2. **Related Work** — 4 sub-bagian + tabel perbandingan SOTA
3. **Methodology** — MDP formulation, 8-dim state, 88 actions, reward, QL & DQN
4. **Experiments and Results** — Setup, main results, 8 tabel, 2 figure
5. **Discussion** — Sample efficiency, XSS analysis, threats to validity
6. **Conclusion** — 4 temuan kunci, future work, CRediT

## Checklist submission
- [ ] Ganti "Kevin Setiawan" dan "Advisor Name" dengan nama asli
- [ ] Ganti "kevin.setiawan@example.com" dengan email asli
- [ ] Ganti "Universitas Contoh" dengan institusi
- [ ] Generate ulang figures: `python visualize_results.py`
- [ ] Compile LaTeX untuk veriksi
- [ ] Submit via Editorial Manager
