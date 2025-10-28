#!/usr/bin/env python3
"""
Plot performance-event deltas from a CSV and print correlations.

Requirements
- Python 3.8+
- pandas, numpy, matplotlib (with LaTeX installed if you want LaTeX rendering)

Usage
  python plot_perf_deltas.py <csv_filename>
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

PLOT_SIGNALS_CANON = [
    "l1 dcache_misses",
    "l1 icache_misses",
    "llc misses",
    "context switches"
]

OPTIONAL_COUNTERS = ["mcycle", "minstret", "l1 dcache_evictions", "DTLB misses"]

PALETTE = ["#6f1d1b", "#bb9457", "#432818", "#99582a", "#ffe6a7"]
# PALETTE = ["#001219","#005f73","#0a9396","#ee9b00","#ca6702","#bb3e03","#ae2012","#9b2226"]
PALETTE= ["#f72585","#7209b7","#3a0ca3","#4361ee","#4cc9f0"]

_SI = [(1e12, 'T'), (1e9, 'G'), (1e6, 'M'), (1e3, 'k'), (1.0, '')]

def _pick_si(x: float) -> tuple[float, str]:
    axv = abs(x)
    for f, s in _SI:
        if axv >= f:
            return f, s
    return 1.0, ''


def sanitize_title_for_filename(title: str) -> str:
    base = re.sub(r"\W+", "_", title.strip()).strip("_")
    return base or "plot"


def normalize_column_name(name: str) -> str:
    s = name.lower()
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def best_effort_column_lookup(df: pd.DataFrame, target: str) -> str | None:
    target_norm = normalize_column_name(target)
    for col in df.columns:
        if normalize_column_name(col) == target_norm:
            return col
    synonyms = {
        "l1 dcache misses": ["l1 dcache_misses", "l1-dcache-misses", "l1-dcache misses"],
        "l1 icache misses": ["l1 icache_misses", "l1-icache-misses", "l1-icache misses"],
        "llc misses": ["llc_misses", "last level cache misses", "llc miss"],
        "llc evictions": ["llc_evictions", "last level cache evictions", "llc eviction"],
        "context switches": ["context switch", "ctx switches", "cswitch", "context_switches"],
        "interrupts": ["irq", "irqs", "interrupt"],
        "software interrupts": ["softirq", "soft irqs", "software interrupt", "software_interrupts"],
        "minor page fault": ["minor page faults", "minor faults", "page-faults-minor", "minor_page_fault"],
        "major page fault": ["major page faults", "major faults", "page-faults-major", "major_page_fault"],
    }
    cand_list = synonyms.get(target_norm, [])
    for cand in cand_list:
        for col in df.columns:
            if normalize_column_name(col) == normalize_column_name(cand):
                return col
    for col in df.columns:
        if target_norm in normalize_column_name(col):
            return col
    return None


def compute_deltas(series: pd.Series) -> pd.Series:
    delta = series.astype("float64").diff()
    delta = delta.clip(lower=0)
    return delta.fillna(0.0)


def try_enable_latex() -> bool:
    try:
        mpl.rcParams.update({
            "text.usetex": True,
            "font.family": "serif",
            "font.serif": ["Computer Modern"],
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "legend.fontsize": 9,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        })
        _ = plt.figure()
        plt.close(_)
        return True
    except Exception:
        mpl.rcParams.update({
            "text.usetex": False,
        })
        return False


def cubic_upsample(x: np.ndarray, y: np.ndarray, factor: int = 8) -> Tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 2 or factor <= 1:
        return x, y
    m = np.zeros(n, dtype=float)
    if n >= 3:
        m[1:-1] = (y[2:] - y[:-2]) / (x[2:] - x[:-2])
    m[0] = (y[1] - y[0]) / (x[1] - x[0]) if n >= 2 and (x[1] - x[0]) != 0 else 0.0
    m[-1] = (y[-1] - y[-2]) / (x[-1] - x[-2]) if n >= 2 and (x[-1] - x[-2]) != 0 else 0.0
    xs, ys = [], []
    for i in range(n - 1):
        x0, x1 = x[i], x[i + 1]
        y0, y1 = y[i], y[i + 1]
        dt = x1 - x0
        if dt <= 0:
            continue
        m0, m1 = m[i], m[i + 1]
        for j in range(factor):
            t = j / float(factor)
            h00 = 2*t**3 - 3*t**2 + 1
            h10 = t**3 - 2*t**2 + t
            h01 = -2*t**3 + 3*t**2
            h11 = t**3 - t**2
            xs.append(x0 + t*dt)
            ys.append(h00*y0 + h10*dt*m0 + h01*y1 + h11*dt*m1)
    xs.append(x[-1]); ys.append(y[-1])
    return np.array(xs), np.array(ys)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot perf event deltas from CSV and print correlations.")
    parser.add_argument("--normalize", choices=["none", "minmax", "zscore", "mean"], default="minmax",
                        help="Normalization for plotting only: 'none' = raw deltas; 'minmax' = (x-min)/(max-min); 'zscore' = (x-mu)/sigma; 'mean' = x/mu.")
    parser.add_argument("csv", type=Path, help="Path to CSV file")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"Error: file not found: {args.csv}", file=sys.stderr)
        return 2

    try:
        title = input("Plot title: ").strip()
    except (EOFError, KeyboardInterrupt):
        title = "Performance Event Deltas"
    if not title:
        title = "Performance Event Deltas"

    base_name = sanitize_title_for_filename(title)

    try:
        df = pd.read_csv(args.csv)
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        return 2

    if df.empty:
        print("Error: CSV has no rows.", file=sys.stderr)
        return 2

    col_map: dict[str, str] = {}
    missing: list[str] = []
    for key in PLOT_SIGNALS_CANON:
        col = best_effort_column_lookup(df, key)
        if col is None:
            missing.append(key)
        else:
            col_map[key] = col

    if missing:
        print("Warning: The following expected columns were not found and will be skipped:")
        for m in missing:
            print(f"  - {m}")
        if not col_map:
            print("Error: None of the required plotting columns were found.", file=sys.stderr)
            return 2

    deltas = {}
    for key, col in col_map.items():
        deltas[key] = compute_deltas(df[col])

    delta_df = pd.DataFrame(deltas)
    t = np.arange(len(delta_df), dtype=float)
    used_latex = try_enable_latex()

    means = delta_df.mean(axis=0)
    stds  = delta_df.std(axis=0, ddof=1)

    def _normalize(col: pd.Series, mode: str) -> pd.Series:
        if mode == "none":
            return col
        if mode == "minmax":
            vmin, vmax = float(np.nanmin(col)), float(np.nanmax(col))
            if vmax > vmin:
                return (col - vmin) / (vmax - vmin)
            return pd.Series(np.zeros(len(col)), index=col.index)
        if mode == "zscore":
            mu = float(np.nanmean(col))
            sd = float(np.nanstd(col, ddof=1)) if len(col) > 1 else 0.0
            if sd > 0:
                return (col - mu) / sd
            return pd.Series(np.zeros(len(col)), index=col.index)
        if mode == "mean":
            mu = float(np.nanmean(col))
            if mu != 0:
                return col / mu
            return pd.Series(np.zeros(len(col)), index=col.index)
        return col

    norm = pd.DataFrame({k: _normalize(delta_df[k], args.normalize) for k in delta_df.columns})

    fig = plt.figure(figsize=(12, 6), dpi=300)
    ax = fig.add_subplot(111)

    for i, key in enumerate(norm.columns):
        col = PALETTE[i % len(PALETTE)]
        x_s, y_s = cubic_upsample(t, norm[key].to_numpy(), factor=8)
        ax.plot(x_s, y_s, label=key, color=col, linewidth=1)

    ax.set_xlabel("Time (s)")
    ylab = {
        "none": "Events per second (delta)",
        "minmax": "Normalized (0-1)",
        "zscore": "Standardized (z-score)",
        "mean": "Mean-scaled (x/$\\mu$)",
    }[args.normalize]
    ax.set_ylabel(ylab)
    ax.set_title(title)
    ax.grid(True, which="both", linestyle=":", linewidth=0.6, alpha=0.7)

    lines = []
    max_mag = float(np.nanmax(np.abs(pd.concat([means.abs(), stds.abs()])))) if len(means) else 1.0
    scale, suf = _pick_si(max_mag)
    for key in delta_df.columns:
        mu = float(means[key])
        sd = float(stds[key]) if not np.isnan(stds[key]) else 0.0
        lines.append(f"{key}: $\\mu$={mu/scale:,.3f} $\\pm$ {sd/scale:,.3f} {suf}/s")
    text = "\n".join(lines)
    ax.text(1.02, 1.0, text, transform=ax.transAxes, va='top', ha='left', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, linewidth=0.5))

    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
    fig.tight_layout(rect=[0, 0, 0.82, 1])

    out_png = Path(f"{base_name}.png")
    out_pdf = Path(f"{base_name}.pdf")

    try:
        fig.savefig(out_png, dpi=300, bbox_inches="tight")
        fig.savefig(out_pdf, dpi=300, bbox_inches="tight")
    finally:
        plt.close(fig)

    print(f"Saved figure: {out_png.resolve()}")
    print(f"Saved figure: {out_pdf.resolve()}")

    if used_latex:
        print("LaTeX rendering: ON")
    else:
        print("LaTeX rendering: OFF (fallback to Matplotlib text)")

    if delta_df.shape[1] >= 2:
        corr = delta_df.corr(method="pearson")
        print("\nCorrelation (Pearson) between plotted signals:")
        corr_rounded = corr.round(3)
        corr_str = corr_rounded.to_string()
        border = "+" + "-" * (max(len(line) for line in corr_str.splitlines())) + "+"
        print(border)
        for line in corr_str.splitlines():
            print("|" + line.ljust(len(border) - 2) + "|")
        print(border)

        # Correlation heatmap
        fig_hm, ax_hm = plt.subplots(figsize=(8, 6), dpi=300)
        cax = ax_hm.imshow(corr_rounded, cmap='coolwarm', vmin=-1, vmax=1)
        fig_hm.colorbar(cax)
        ax_hm.set_xticks(range(len(corr_rounded.columns)))
        ax_hm.set_xticklabels(corr_rounded.columns, rotation=45, ha='right', fontsize=8)
        ax_hm.set_yticks(range(len(corr_rounded.index)))
        ax_hm.set_yticklabels(corr_rounded.index, fontsize=8)
        ax_hm.set_title('Correlation Heatmap')
        fig_hm.tight_layout()
        out_hm_png = Path(f"{base_name}_corr_heatmap.png")
        out_hm_pdf = Path(f"{base_name}_corr_heatmap.pdf")
        try:
            fig_hm.savefig(out_hm_png, dpi=300, bbox_inches='tight')
            fig_hm.savefig(out_hm_pdf, dpi=300, bbox_inches='tight')
        finally:
            plt.close(fig_hm)
        print(f"Saved correlation heatmap: {out_hm_png.resolve()}")
        print(f"Saved correlation heatmap: {out_hm_pdf.resolve()}")
    else:
        print("Not enough signals to compute correlation table.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
