#!/usr/bin/env python3
"""
Plot four metrics across three LLC sizes from three CSVs (no correlation output).

- Accepts exactly three CSV files (e.g., for 128k, 256k, 512k).
- Plots four metrics (see PLOT_SIGNALS_CANON) in a 2x2 figure, with one line per LLC size.
- Supports normalization modes: none, minmax, zscore, mean (applied per-series for plotting only).
- Computes and displays per-series mean and variance (of deltas) for each metric on its subplot.
- Saves PNG and PDF.
"""

from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from typing import Tuple, List, Dict

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

# ---- Configuration ----

PLOT_SIGNALS_CANON = [
    "l1 dcache_misses",
    "l1 icache_misses",
    "llc misses",
    "context switches",
]

PALETTE = ["#f72585", "#4361ee", "#4cc9f0"]  # one color per LLC size

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
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "legend.fontsize": 9,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        })
        _ = plt.figure()
        plt.close(_)
        return True
    except Exception:
        mpl.rcParams.update({"text.usetex": False})
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


def load_and_prepare(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    deltas = {}
    for key in PLOT_SIGNALS_CANON:
        col = best_effort_column_lookup(df, key)
        if col is None:
            continue
        deltas[key] = compute_deltas(df[col])
    if not deltas:
        raise ValueError(f"No expected columns found in {csv_path}")
    return pd.DataFrame(deltas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot four metrics across three LLC sizes from three CSVs (no correlation).")
    parser.add_argument("--normalize", choices=["none", "minmax", "zscore", "mean"], default="minmax",
                        help="Normalization for plotting only.")
    parser.add_argument("--labels", type=str, default="128k,256k,512k",
                        help="Comma-separated labels for the three sizes (order matches CSVs).")
    parser.add_argument("csvs", nargs=3, type=Path, help="Three CSV files (e.g., 128k 256k 512k).")
    args = parser.parse_args()

    labels = [s.strip() for s in args.labels.split(",")]
    if len(labels) != 3:
        print("Error: --labels must provide exactly three comma-separated labels.", file=sys.stderr)
        return 2

    try:
        title = input("Plot title: ").strip()
    except (EOFError, KeyboardInterrupt):
        title = ""
    if not title:
        title = "Perf deltas: 3 LLC sizes"

    base_name = sanitize_title_for_filename(title)

    # Load data
    data_frames: List[pd.DataFrame] = []
    for p in args.csvs:
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            return 2
        try:
            df = load_and_prepare(p)
        except Exception as e:
            print(f"Error reading {p}: {e}", file=sys.stderr)
            return 2
        data_frames.append(df)

    # Establish common time index based on shortest series length
    min_len = min(len(df) for df in data_frames)
    t = np.arange(min_len, dtype=float)

    used_latex = try_enable_latex()

    # 2x2 subplots for the four metrics
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), dpi=300, squeeze=False)
    axes = axes.ravel()

    # For each metric, plot a line per size and show mean/variance
    for ax, metric in zip(axes, PLOT_SIGNALS_CANON):
        lines = []
        stats_lines = []
        for idx, (df, lab) in enumerate(zip(data_frames, labels)):
            if metric not in df.columns:
                continue
            series = df[metric].iloc[:min_len]
            # For plotting: normalize per-series
            series_norm = _normalize(series, args.normalize)
            xs, ys = cubic_upsample(t, series_norm.to_numpy(), factor=8)
            ln, = ax.plot(xs, ys, label=lab, color=PALETTE[idx % len(PALETTE)], linewidth=1.1)
            lines.append(ln)

        # Axes cosmetics
        ylab = {
            "none": f"{metric} (delta)",
            "minmax": f"{metric} (normalized 0–1)",
            "zscore": f"{metric} (z-score)",
            "mean": f"{metric} (x/μ)",
        }[args.normalize]
        ax.set_title(metric)
        ax.set_xlabel("Time (samples)")
        ax.set_ylabel(ylab)
        ax.grid(True, which="both", linestyle=":", linewidth=0.6, alpha=0.7)

        # Compute mean/variance on raw deltas (not normalized) for interpretability
        # Display a small text box on the subplot
        # Align labels with provided labels order; handle missing metric gracefully
        # Build stats text
        scale_ref = 0.0
        for df in data_frames:
            if metric in df.columns:
                scale_ref = max(scale_ref, float(np.nanmax(np.abs(df[metric].iloc[:min_len]))))
        scale, suf = _pick_si(scale_ref if scale_ref > 0 else 1.0)

        stats_lines = []
        for lab, df in zip(labels, data_frames):
            if metric not in df.columns:
                stats_lines.append(f"{lab}: n/a")
                continue
            raw = df[metric].iloc[:min_len].astype(float)
            mu = float(raw.mean())
            var = float(raw.var(ddof=1)) if len(raw) > 1 else 0.0
            if used_latex:
                stats_lines.append(f"{lab}: $\\mu$={mu/scale:,.3f}, $\\sigma^2$={var/(scale**2):,.3f} {suf}$^2$/s$^2$")
            else:
                stats_lines.append(f"{lab}: mu={mu/scale:,.3f}, sigma^2={var/(scale**2):,.3f} {suf}^2/s^2")

        text = "\n".join(stats_lines)
        ax.text(1.02, 1.0, text, transform=ax.transAxes, va='top', ha='left', fontsize=8.5,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.85, linewidth=0.5))

        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)

    fig.suptitle(title)
    fig.tight_layout(rect=[0, 0, 0.82, 0.96])

    out_png = Path(f"{base_name}_llc3_4win.png")
    out_pdf = Path(f"{base_name}_llc3_4win.pdf")
    try:
        fig.savefig(out_png, dpi=300, bbox_inches="tight")
        fig.savefig(out_pdf, dpi=300, bbox_inches="tight")
    finally:
        plt.close(fig)

    print(f"Saved figure: {out_png.resolve()}")
    print(f"Saved figure: {out_pdf.resolve()}")
    print("LaTeX rendering:", "ON" if used_latex else "OFF (fallback to Matplotlib text)")

    return 0


if __name__ == "__main__":
    sys.exit(main())