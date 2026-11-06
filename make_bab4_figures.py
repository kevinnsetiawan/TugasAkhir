"""Membangun gambar-gambar Bab 4 (Pengumpulan Data) untuk dokumen Tugas Akhir.

Menghasilkan tiga berkas PNG 300 dpi di figures/bab4/ dan menyalinnya ke
folder ``gambar/`` milik template LaTeX:

    gambar_4_1_alur_pengumpulan_data.png
    gambar_4_2_alur_verifikasi_kualitas.png
    gambar_4_3_rekap_volume_data.png

Seluruh angka diambil dari artefak hasil eksekusi (summary_*.json dan
zap_controlled_report.json) agar gambar selalu konsisten dengan data.

Jalankan dari root repo:
    python make_bab4_figures.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon
from matplotlib.textpath import TextPath

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "rl_pentest" / "results"
OUT_DIR = BASE / "figures" / "bab4"
TEMPLATE_DIR = BASE / "Template_Proposal_TA_Telkom_University_Surabaya (1)" / "gambar"
DPI = 300

FAMILY = "DejaVu Sans"
plt.rcParams["font.family"] = FAMILY

NAVY = "#1f3864"
BLUE = "#2e5c8a"
LIGHT = "#eaf1f7"
ORANGE = "#c55a11"
ORANGE_L = "#fbe9dc"
GREY = "#5f6b7a"
GREY_L = "#f1f3f5"
GREEN = "#1e6b45"
GREEN_L = "#e6f2eb"
RED = "#9b1c1c"
RED_L = "#f9e6e6"
INK = "#111111"

CHECKS: list[tuple] = []
RECTS: list[tuple] = []


# --------------------------------------------------------------------------- #
# utilitas geometri & teks
# --------------------------------------------------------------------------- #
def canvas(w_cm: float, h_cm: float):
    """Kanvas dengan satuan data = sentimeter (1 unit = 1 cm)."""
    fig = plt.figure(figsize=(w_cm / 2.54, h_cm / 2.54), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w_cm)
    ax.set_ylim(0, h_cm)
    ax.axis("off")
    return fig, ax


def text_width_cm(s: str, fs: float, weight: str = "normal") -> float:
    tp = TextPath((0, 0), s, size=fs, prop=FontProperties(family=FAMILY, weight=weight))
    return tp.get_extents().width / 72.0 * 2.54


def wrap_cm(text: str, fs: float, max_w: float, weight: str = "normal") -> list[str]:
    words, lines, cur = text.split(), [], ""
    for word in words:
        cand = f"{cur} {word}".strip()
        if text_width_cm(cand, fs, weight) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def box(ax, x, y, w, h, fc=LIGHT, ec=NAVY, lw=1.1, ls="-", r=0.12, z=2):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, zorder=z,
    )
    ax.add_patch(patch)
    RECTS.append((x, y, w, h))
    return patch


def fit_fontsize(s, fs, max_w, weight="normal", min_fs=5.2):
    """Perkecil ukuran font sampai lebar baris terpanjang masuk ke max_w."""
    lines = s.split("\n")
    while fs > min_fs:
        widest = max(text_width_cm(line, fs, weight) for line in lines)
        if widest <= max_w:
            break
        fs -= 0.2
    return fs


def ctext(ax, x, y, w, h, s, fs=8.0, weight="normal", color=INK, style="normal", z=6):
    fs = fit_fontsize(s, fs, w - 0.14, weight)
    t = ax.text(
        x + w / 2, y + h / 2, s, ha="center", va="center", fontsize=fs,
        fontweight=weight, color=color, style=style, linespacing=1.25, zorder=z,
    )
    CHECKS.append(("center", t, (x, y, w, h)))
    return t


def bullets(ax, x, y_top, w, h, items, fs0=7.0, color=INK, pt=0.10):
    """Daftar butir dengan pembungkusan baris presisi (diukur, bukan ditebak)."""
    fs = fs0
    while True:
        lh = fs * 1.34 / 28.3465
        rows: list[str | None] = []
        for item in items:
            wrapped = wrap_cm(item, fs, w - 0.45)
            for i, line in enumerate(wrapped):
                rows.append(("• " + line) if i == 0 else ("   " + line))
            rows.append(None)
        rows.pop()
        total = len(rows) * lh + (len(items) - 1) * pt
        if total <= h - 0.22 or fs <= 5.4:
            break
        fs -= 0.1

    y = y_top
    for row in rows:
        if row is None:
            y -= pt
            continue
        ax.text(x, y, row, ha="left", va="top", fontsize=fs, color=color, zorder=6)
        y -= lh
    if total > h - 0.22:
        print(f"    ! teks butir melebihi kotak: butuh {total:.2f} cm, tersedia {h - 0.22:.2f} cm")
    return fs


def arrow(ax, p1, p2, ls="-", color=NAVY, lw=1.0, style="-|>", rad=0.0, conn=None, z=1):
    kwargs = dict(
        arrowstyle=style, mutation_scale=9, lw=lw, color=color, linestyle=ls,
        shrinkA=0, shrinkB=0, zorder=z,
    )
    if conn:
        kwargs["connectionstyle"] = conn
    elif rad:
        kwargs["connectionstyle"] = f"arc3,rad={rad}"
    ax.add_patch(FancyArrowPatch(p1, p2, **kwargs))


def diamond(ax, cx, cy, hw, hh, s, fs=7.6, fc="#fff7e6", ec=ORANGE):
    ax.add_patch(
        Polygon(
            [(cx, cy + hh), (cx + hw, cy), (cx, cy - hh), (cx - hw, cy)],
            closed=True, facecolor=fc, edgecolor=ec, linewidth=1.1, zorder=3,
        )
    )
    fs = fit_fontsize(s, fs, hw * 1.24, min_fs=5.2)
    t = ax.text(cx, cy, s, ha="center", va="center", fontsize=fs,
                color=INK, linespacing=1.2, zorder=6)
    CHECKS.append(("center", t, (cx - hw * 0.62, cy - hh * 0.58, hw * 1.24, hh * 1.16)))


def label(ax, x, y, s, fs=6.4, color=GREY, ha="center", va="center", style="normal"):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color, style=style, zorder=7)


def load_data():
    ql = json.loads((RESULTS / "summary_ql.json").read_text())
    dqn = json.loads((RESULTS / "summary_dqn.json").read_text())
    zap = json.loads((RESULTS / "zap_controlled_report.json").read_text())["zap_results"]
    return ql, dqn, zap


# --------------------------------------------------------------------------- #
# Gambar 4.1 - alur pengumpulan data (empat instrumen)
# --------------------------------------------------------------------------- #
def figure_4_1(data):
    ql, dqn, zap = data
    W, H = 17.0, 13.6
    fig, ax = canvas(W, H)

    # --- lingkungan uji ---------------------------------------------------- #
    ty, th = 12.05, 0.95
    box(ax, 0.35, ty, 16.30, th, fc=NAVY, ec=NAVY)
    ctext(ax, 0.35, ty, 16.30, th,
          "Lingkungan uji terisolasi  ·  OWASP Juice Shop v20.2.0  ·  http://localhost:3000  ·  Docker",
          fs=8.4, weight="bold", color="white")

    # --- kolom tahap ------------------------------------------------------- #
    col_w = 3.60
    xs = [0.35, 4.50, 8.65, 13.05]
    hy, hh = 10.20, 1.00
    by, bh = 4.00, 6.05

    heads = [
        ("1 · Baseline Probing", "acuan awal"),
        ("2 · Pelatihan RL", "data primer"),
        ("3 · Verifikasi Kualitas", "gerbang eksploitasi"),
        ("4 · ZAP Controlled Scan", "pembanding"),
    ]
    body = [
        [
            '1 request netral "hello" untuk setiap endpoint',
            "8 transaksi HTTP (satu per endpoint)",
            "Merekam baseline_length tiap endpoint sebagai acuan significant_change",
            "Keluaran: baseline tersimpan di ResponseAnalyzer",
        ],
        [
            f"{ql['total_episodes']} episode per agen → QL + DQN = "
            f"{ql['total_episodes'] + dqn['total_episodes']} transaksi",
            "Aksi: 8 endpoint × 15 payload = 120",
            "Pemilihan aksi ε-greedy; satu muatan uji per episode",
            "Metadata respons dicatat setiap episode",
            "Keluaran: log_ql.csv dan log_dqn.csv",
        ],
        [
            "Dipicu saat kandidat kerentanan terdeteksi",
            f"SQLi/Fuzzing: probe kontrol netral + mutan ternetralkan "
            f"({ql['verification_requests']} QL / {dqn['verification_requests']} DQN)",
            f"XSS: Chromium headless, kanari DOM "
            f"({ql['browser_navigations']} / {dqn['browser_navigations']} navigasi)",
            "Keluaran: kolom verified pada log",
        ],
        [
            "Hanya 2 endpoint bersama: search dan /ftp/",
            f"Spider + akses {zap['requests_by_phase']['spider_plus_access']} + "
            f"active scan {zap['requests_by_phase']['active_scan']} = "
            f"{zap['total_requests']} request",
            f"{zap['total_alerts_raw']} alert "
            f"({zap['risk_breakdown']['high']} High, "
            f"{zap['risk_breakdown']['medium']} Medium)",
            "Keluaran: zap_controlled_report.json",
        ],
    ]

    for i, x in enumerate(xs):
        arrow(ax, (x + col_w / 2, ty), (x + col_w / 2, hy + hh), color=BLUE, lw=1.0)
        fc = ORANGE if i == 2 else (GREY if i == 3 else NAVY)
        ec = fc
        box(ax, x, hy, col_w, hh, fc=fc, ec=ec, r=0.10)
        ctext(ax, x, hy + 0.40, col_w, 0.55, heads[i][0], fs=8.0, weight="bold", color="white")
        ctext(ax, x, hy + 0.10, col_w, 0.32, heads[i][1], fs=6.4, color="white", style="italic")

        edge = ORANGE if i == 2 else (GREY if i == 3 else NAVY)
        ls = "--" if i == 3 else "-"
        box(ax, x, by, col_w, bh, fc=LIGHT if i != 3 else GREY_L, ec=edge, lw=1.1, ls=ls, r=0.10)
        bullets(ax, x + 0.14, by + bh - 0.18, col_w - 0.10, bh - 0.12, body[i], fs0=7.0)

    # panah antar tahap: 1->2 solid, 2->3 kondisional (putus-putus)
    mid_y = by + bh / 2
    arrow(ax, (xs[0] + col_w, mid_y), (xs[1], mid_y), color=NAVY, lw=1.2)
    arrow(ax, (xs[1] + col_w, mid_y), (xs[2], mid_y), ls="--", color=ORANGE, lw=1.2)

    # pemisah instrumen pembanding
    ax.plot([12.60, 12.60], [1.35, 11.70], color=GREY, lw=0.9, ls=(0, (1, 2)), zorder=0)

    # --- artefak ----------------------------------------------------------- #
    ay, ah = 2.60, 0.85
    box(ax, 0.35, ay, 16.30, ah, fc="#ffffff", ec=NAVY, lw=1.1, r=0.10)
    ctext(ax, 0.35, ay, 16.30, ah,
          "Artefak data:  log_ql.csv  ·  log_dqn.csv  ·  summary_ql.json  ·  "
          "summary_dqn.json  ·  q_table.json  ·  dqn_model.pt  ·  zap_controlled_report.json",
          fs=7.0)

    for i, x in enumerate(xs):
        arrow(ax, (x + col_w / 2, by), (x + col_w / 2, ay + ah), color=BLUE, lw=0.9)

    # --- legenda ----------------------------------------------------------- #
    ly = 1.55
    ax.plot([0.45, 1.25], [ly, ly], color=NAVY, lw=1.2)
    label(ax, 1.33, ly, "alur utama", fs=6.6, ha="left")
    ax.plot([4.05, 4.85], [ly, ly], color=ORANGE, lw=1.2, ls="--")
    label(ax, 4.93, ly, "alur kondisional (bila kandidat kerentanan muncul)",
          fs=6.6, ha="left")
    ax.plot([12.85, 13.45], [ly, ly], color=GREY, lw=0.9, ls=(0, (1, 2)))
    label(ax, 13.53, ly, "pembanding independen", fs=6.6, ha="left")

    return fig, "gambar_4_1_alur_pengumpulan_data.png"


# --------------------------------------------------------------------------- #
# Gambar 4.2 - alur verifikasi kualitas eksploitasi
# --------------------------------------------------------------------------- #
def figure_4_2(data):
    ql, dqn, zap = data
    W, H = 17.0, 15.4
    fig, ax = canvas(W, H)

    # masukan
    box(ax, 3.60, 13.85, 9.80, 0.95, fc=NAVY, ec=NAVY)
    ctext(ax, 3.60, 13.85, 9.80, 0.95,
          "Respons HTTP diterima  →  ResponseAnalyzer.analyze(surface)",
          fs=8.2, weight="bold", color="white")

    # keputusan 1
    diamond(ax, 8.50, 11.85, 3.05, 0.95, "Kandidat\nkerentanan?", fs=7.8)
    arrow(ax, (8.50, 13.85), (8.50, 12.80), color=NAVY)
    label(ax, 8.72, 13.40, "ya", fs=6.6, ha="left", style="italic")

    # cabang "tidak" -> normal
    box(ax, 0.40, 11.05, 4.15, 1.35, fc=GREY_L, ec=GREY, r=0.10)
    ctext(ax, 0.40, 11.05, 4.15, 1.35,
          "Tidak ada indikasi\nreward −1 (normal), −5 (galat)\nlanjut episode berikutnya",
          fs=6.9, color=INK)
    arrow(ax, (5.45, 11.85), (4.55, 11.72), color=GREY)
    label(ax, 4.95, 12.15, "tidak", fs=6.6, color=GREY, style="italic")

    # keputusan 2 - kelas kerentanan
    diamond(ax, 8.50, 10.35, 2.55, 0.78, "Kelas kerentanan?", fs=7.5)
    arrow(ax, (8.50, 10.90), (8.50, 11.13), color=NAVY)
    label(ax, 8.72, 11.02, "ya", fs=6.6, ha="left", style="italic")

    # header cabang
    box(ax, 1.00, 7.95, 6.30, 0.72, fc=ORANGE_L, ec=ORANGE, r=0.08)
    ctext(ax, 1.00, 7.95, 6.30, 0.72, "SQLi / Fuzzing", fs=7.8, weight="bold", color="#7a3608")
    box(ax, 9.70, 7.95, 6.30, 0.72, fc="#e8eef6", ec=BLUE, r=0.08)
    ctext(ax, 9.70, 7.95, 6.30, 0.72, "XSS", fs=7.8, weight="bold", color="#1b3f63")

    arrow(ax, (5.95, 10.35), (4.15, 8.67), color=ORANGE, lw=1.1,
          conn="angle,angleA=180,angleB=90,rad=0")
    arrow(ax, (11.05, 10.35), (12.85, 8.67), color=BLUE, lw=1.1,
          conn="angle,angleA=0,angleB=90,rad=0")

    # --- cabang kiri: kontrol-diferensial ---------------------------------- #
    box(ax, 1.00, 6.85, 6.30, 0.78, fc="#ffffff", ec=ORANGE, r=0.08)
    ctext(ax, 1.00, 6.85, 6.30, 0.78, 'Probe kontrol 1: "hello" (netral)', fs=7.2)
    box(ax, 1.00, 5.60, 6.30, 0.95, fc="#ffffff", ec=ORANGE, r=0.08)
    ctext(ax, 1.00, 5.60, 6.30, 0.95,
          "Probe kontrol 2: neutralize_payload()\n(dilewati bila payload wildcard %s)", fs=7.0)
    diamond(ax, 4.15, 4.35, 2.75, 0.88, "Kontrol mereproduksi\nkelas yang sama?", fs=7.2)
    arrow(ax, (4.15, 6.85), (4.15, 6.55), color=ORANGE, lw=0.9)
    arrow(ax, (4.15, 5.60), (4.15, 5.23), color=ORANGE, lw=0.9)

    # --- cabang kanan: eksekusi DOM --------------------------------------- #
    box(ax, 9.70, 6.85, 6.30, 0.78, fc="#ffffff", ec=BLUE, r=0.08)
    ctext(ax, 9.70, 6.85, 6.30, 0.78, "Injeksi vektor (handler → kanari)", fs=7.2)
    box(ax, 9.70, 5.60, 6.30, 0.95, fc="#ffffff", ec=BLUE, r=0.08)
    ctext(ax, 9.70, 5.60, 6.30, 0.95,
          "Muat halaman SPA + polling\nwindow.__RLP_XSS_CANARY__", fs=7.0)
    diamond(ax, 12.85, 4.35, 2.75, 0.88, "Kanari tereksekusi\ndi DOM?", fs=7.2)
    arrow(ax, (12.85, 6.85), (12.85, 6.55), color=BLUE, lw=0.9)
    arrow(ax, (12.85, 5.60), (12.85, 5.23), color=BLUE, lw=0.9)

    # --- hasil keputusan --------------------------------------------------- #
    box(ax, 1.00, 2.05, 2.95, 1.10, fc=GREEN_L, ec=GREEN, r=0.10)
    ctext(ax, 1.00, 2.05, 2.95, 1.10, "Terverifikasi\nreward +50", fs=7.2,
          weight="bold", color=GREEN)
    box(ax, 4.65, 2.05, 2.65, 1.10, fc=RED_L, ec=RED, r=0.10)
    ctext(ax, 4.65, 2.05, 2.65, 1.10, "Ditolak\n+10 (anomali)", fs=7.2, color=RED)

    box(ax, 9.70, 2.05, 2.90, 1.10, fc=GREEN_L, ec=GREEN, r=0.10)
    ctext(ax, 9.70, 2.05, 2.90, 1.10, "Terverifikasi\nreward +50", fs=7.2,
          weight="bold", color=GREEN)
    box(ax, 13.10, 2.05, 2.90, 1.10, fc=RED_L, ec=RED, r=0.10)
    ctext(ax, 13.10, 2.05, 2.90, 1.10, "Ditolak\n+10 (anomali)", fs=7.2, color=RED)

    arrow(ax, (3.30, 3.85), (2.55, 3.15), color=GREEN, lw=1.0)
    label(ax, 2.55, 3.72, "tidak", fs=6.4, color=GREEN, style="italic")
    arrow(ax, (4.90, 3.85), (5.70, 3.15), color=RED, lw=1.0)
    label(ax, 5.75, 3.72, "ya", fs=6.4, color=RED, style="italic")

    arrow(ax, (12.00, 3.85), (11.25, 3.15), color=GREEN, lw=1.0)
    label(ax, 11.30, 3.72, "ya", fs=6.4, color=GREEN, style="italic")
    arrow(ax, (13.60, 3.85), (14.35, 3.15), color=RED, lw=1.0)
    label(ax, 14.15, 3.72, "tidak", fs=6.4, color=RED, style="italic")

    # --- pencatatan -------------------------------------------------------- #
    box(ax, 1.00, 0.80, 15.00, 0.80, fc=NAVY, ec=NAVY, r=0.10)
    ctext(ax, 1.00, 0.80, 15.00, 0.80,
          "Semua hasil dicatat ke log_ql.csv / log_dqn.csv  "
          "(kolom vulnerability, verified, reward)  →  episode berikutnya",
          fs=7.4, color="white")
    for x in (2.45, 5.95, 11.15, 14.55):
        arrow(ax, (x, 2.05), (x, 1.60), color=GREY, lw=0.9)

    label(ax, 8.50, 0.32,
          f"Beban verifikasi terukur: {ql['verification_requests']} transaksi kontrol (QL) / "
          f"{dqn['verification_requests']} (DQN) · {ql['browser_navigations']} / "
          f"{dqn['browser_navigations']} navigasi peramban",
          fs=6.6, style="italic")

    return fig, "gambar_4_2_alur_verifikasi_kualitas.png"


# --------------------------------------------------------------------------- #
# Gambar 4.3 - rekap volume data terkumpul
# --------------------------------------------------------------------------- #
def figure_4_3(data):
    ql, dqn, zap = data
    W, H = 16.4, 8.6
    fig = plt.figure(figsize=(W / 2.54, H / 2.54), dpi=DPI)
    fig.patch.set_facecolor("white")

    def panel(x, y, w, h):
        return fig.add_axes([x / W, y / H, w / W, h / H])

    # --- panel (a): transaksi HTTP ---------------------------------------- #
    ax = panel(2.45, 1.35, 7.75, 5.95)
    ax.set_facecolor("white")
    cats = ["Q-Learning", "DQN", "ZAP\n(2 endpoint)"]
    base = [ql["baseline_probe_requests"], dqn["baseline_probe_requests"], 0]
    train = [ql["total_requests"], dqn["total_requests"], 0]
    verif = [ql["verification_requests"], dqn["verification_requests"], 0]
    spider = [0, 0, zap["requests_by_phase"]["spider_plus_access"]]
    active = [0, 0, zap["requests_by_phase"]["active_scan"]]
    totals = [sum(v) for v in zip(base, train, verif, spider, active)]

    ypos = [2, 1, 0]
    colors = [
        ("Baseline probing", base, "#9aa5b1"),
        ("Transaksi pelatihan RL", train, "#1f4e79"),
        ("Verifikasi kontrol-diferensial", verif, "#c55a11"),
        ("Spider + akses (ZAP)", spider, "#8fb8d8"),
        ("Active scan (ZAP)", active, "#2f6f8f"),
    ]
    left = [0, 0, 0]
    for name, vals, col in colors:
        ax.barh(ypos, vals, left=left, height=0.52, color=col, edgecolor="white",
                linewidth=0.8, label=name)
        left = [l + v for l, v in zip(left, vals)]

    for y, total in zip(ypos, totals):
        ax.text(total + 35, y, f"{total:,}".replace(",", "."), va="center",
                ha="left", fontsize=8.5, fontweight="bold", color=INK)

    # label segmen besar
    for idx, y in enumerate(ypos):
        acc = 0
        for _, vals, _ in colors:
            v = vals[idx]
            if v >= 200:
                ax.text(acc + v / 2, y, f"{v:,}".replace(",", "."), va="center",
                        ha="center", fontsize=7.4, color="white", fontweight="bold")
            acc += v
    # segmen kecil diberi penunjuk
    ax.annotate(
        f"baseline {base[0]}", xy=(base[0] / 2, 2.30), xytext=(150, 2.72),
        fontsize=6.8, color=GREY, ha="left",
        arrowprops=dict(arrowstyle="-", lw=0.7, color=GREY,
                        connectionstyle="arc3,rad=-0.25"),
    )
    ax.annotate(
        f"verifikasi {verif[0]}", xy=(base[0] + train[0] + verif[0] / 2, 1.72),
        xytext=(1180, 1.55), fontsize=6.8, color=ORANGE, ha="left",
        arrowprops=dict(arrowstyle="-", lw=0.7, color=ORANGE,
                        connectionstyle="arc3,rad=0.3"),
    )

    ax.set_yticks(ypos)
    ax.set_yticklabels(cats, fontsize=8.0)
    ax.set_xlim(0, 1900)
    ax.set_ylim(-0.55, 3.05)
    ax.set_xlabel("Jumlah transaksi HTTP", fontsize=8.2)
    ax.tick_params(axis="x", labelsize=7.4)
    ax.grid(axis="x", ls=":", lw=0.6, color="#c9d2da")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#8a95a1")
    ax.set_title("(a) Volume transaksi HTTP per instrumen dan tahap",
                 fontsize=8.4, fontweight="bold", pad=6)
    ax.legend(fontsize=6.4, loc="lower right", frameon=True, framealpha=0.95,
              edgecolor="#d5dbe1", borderpad=0.5)

    # --- panel (b): navigasi peramban ------------------------------------- #
    axb = panel(10.95, 4.45, 4.55, 2.75)
    axb.set_facecolor("white")
    names = ["Q-Learning", "DQN"]
    nav = [ql["browser_navigations"], dqn["browser_navigations"]]
    axb.barh(names, nav, height=0.45, color="#5b7ea8", edgecolor="white")
    for i, v in enumerate(nav):
        axb.text(v + 0.6, i, str(v), va="center", fontsize=8.0, fontweight="bold")
    axb.set_xlim(0, 36)
    axb.tick_params(labelsize=7.2)
    axb.grid(axis="x", ls=":", lw=0.6, color="#c9d2da")
    axb.set_axisbelow(True)
    for side in ("top", "right"):
        axb.spines[side].set_visible(False)
    axb.set_title("(b) Navigasi peramban Playwright", fontsize=7.8,
                  fontweight="bold", pad=5)

    # --- panel (c): alert ZAP --------------------------------------------- #
    axc = panel(10.95, 1.35, 4.55, 2.60)
    axc.set_facecolor("white")
    risks = ["High", "Medium", "Low", "Info"]
    vals = [zap["risk_breakdown"]["high"], zap["risk_breakdown"]["medium"],
            zap["risk_breakdown"]["low"], zap["risk_breakdown"]["informational"]]
    cols = ["#a11d1d", "#e08a1e", "#f2d16b", "#b8c4ce"]
    axc.barh(risks[::-1], vals[::-1], height=0.55, color=cols[::-1], edgecolor="white")
    for i, v in enumerate(vals[::-1]):
        axc.text(v + 0.4, i, str(v), va="center", fontsize=7.8, fontweight="bold")
    axc.set_xlim(0, 32)
    axc.tick_params(labelsize=7.2)
    axc.grid(axis="x", ls=":", lw=0.6, color="#c9d2da")
    axc.set_axisbelow(True)
    for side in ("top", "right"):
        axc.spines[side].set_visible(False)
    axc.set_title(f"(c) {zap['total_alerts_raw']} alert ZAP per tingkat risiko",
                  fontsize=7.8, fontweight="bold", pad=5)

    return fig, "gambar_4_3_rekap_volume_data.png"


# --------------------------------------------------------------------------- #
# verifikasi otomatis: luapan teks & tumpang tindih
# --------------------------------------------------------------------------- #
def verify(fig, name):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = fig.axes[0].transData.inverted()
    problems = 0
    for kind, artist, rect in CHECKS:
        bb = artist.get_window_extent(renderer=renderer)
        bb = bb.transformed(inv)
        x, y, w, h = rect
        if bb.width > w + 0.02 or bb.height > h + 0.02:
            problems += 1
            print(f"    ! '{artist.get_text()[:34]}' keluar kotak "
                  f"({bb.width:.2f}x{bb.height:.2f} cm vs {w:.2f}x{h:.2f})")

    for i in range(len(RECTS)):
        for j in range(i + 1, len(RECTS)):
            ax1, ay1, aw1, ah1 = RECTS[i]
            ax2, ay2, aw2, ah2 = RECTS[j]
            ox = min(ax1 + aw1, ax2 + aw2) - max(ax1, ax2)
            oy = min(ay1 + ah1, ay2 + ah2) - max(ay1, ay2)
            if ox > 0.05 and oy > 0.05:
                problems += 1
                print(f"    ! kotak bertumpuk: {RECTS[i]} vs {RECTS[j]} "
                      f"(overlap {ox:.2f}x{oy:.2f} cm)")

    print(f"  {name}: {problems} masalah tata letak")
    return problems


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data()

    for builder in (figure_4_1, figure_4_2, figure_4_3):
        CHECKS.clear()
        RECTS.clear()
        fig, fname = builder(data)
        verify(fig, fname)
        out = OUT_DIR / fname
        fig.savefig(out, dpi=DPI, facecolor="white", bbox_inches=None, pad_inches=0)
        plt.close(fig)
        print(f"  → {out}")

        if TEMPLATE_DIR.exists():
            shutil.copy2(out, TEMPLATE_DIR / fname)
            print(f"  → disalin ke {TEMPLATE_DIR / fname}")


if __name__ == "__main__":
    main()
