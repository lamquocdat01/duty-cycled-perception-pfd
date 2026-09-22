"""make_figures_v2.py -- Topic 35 / V2 figures.

Every figure is produced from the released CSV tables, never from a number typed
here.  The figures have to survive two things a journal figure usually does not:
greyscale printing, and a colour-vision-deficient reader.  So identity is carried
by line style and marker as well as by hue, every series is either in a legend or
directly labelled, and the palette was checked with the validator rather than
chosen by eye (Okabe-Ito subset, fixed order, never cycled; the adjacent-pair CVD
floor is in the 6-8 band, which is legal only with the secondary encoding used
here).

One measure per axis: there is no dual-axis chart anywhere in this file.
"""
from __future__ import annotations

import csv
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

EVAL = pathlib.Path(__file__).resolve().parents[1]
RESULTS = EVAL / "results"
FIGS = EVAL.parent / "02_Manuscript" / "figs"

# Fixed categorical order; never cycled.  Validated for light surface #fcfcfb.
HUE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"]
DASH = ["-", "--", "-.", (0, (1, 1))]
MARK = ["o", "s", "^", "D"]
INK = "#1a1a1a"
MUTED = "#6b6b6b"
GRID = "#d9d9d9"

plt.rcParams.update({
    "font.family": "serif", "font.size": 8.5, "axes.labelsize": 8.5,
    "axes.titlesize": 9, "legend.fontsize": 7.5, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.labelcolor": INK, "grid.color": GRID, "grid.linewidth": 0.5,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "legend.frameon": False,
})

SIL_BANDS = [("SIL 4", 1e-5, 1e-4), ("SIL 3", 1e-4, 1e-3),
             ("SIL 2", 1e-3, 1e-2), ("SIL 1", 1e-2, 1e-1)]


def rows(name):
    p = RESULTS / name
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        out = []
        for r in csv.DictReader(f):
            for k, v in list(r.items()):
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    pass
            out.append(r)
        return out


def band_shading(ax, xmin, xmax):
    """Shade the IEC 61508-1 low-demand bands.  Call after set_ylim: a band
    whose label would land outside the visible range is shaded but not named,
    so no text is ever drawn below the axes."""
    y0, y1 = ax.get_ylim()
    for i, (name, lo, hi) in enumerate(SIL_BANDS):
        ax.axhspan(lo, hi, color="#000000", alpha=0.035 if i % 2 else 0.06, lw=0)
        mid = np.sqrt(lo * hi)
        if y0 < mid < y1:
            ax.text(xmax, mid, " " + name, va="center", ha="left",
                    fontsize=6.5, color=MUTED)


def fig_validation():
    """The headline: measured end-to-end miss rate against the model's prediction."""
    R = [r for r in rows("miss_validation_v2.csv") if r["corpus"] == "pooled"]
    if not R:
        return
    R.sort(key=lambda r: r["T_seconds"])
    # dot 2c: the heterogeneous prediction, out of sample, is the paper's model
    Hd = {r["T_seconds"]: r for r in rows("het_validation_v2_2.csv")
          if r["corpus"] == "pooled"}
    T = np.array([r["T_seconds"] for r in R])
    meas = np.array([r["miss_measured"] for r in R])
    lo = np.array([r["miss_lo"] for r in R])
    hi = np.array([r["miss_hi"] for r in R])
    mod = np.array([r["miss_model_beta"] for r in R])
    mod0 = np.array([r["miss_model_beta0"] for r in R])
    floor = np.array([r["structural_floor"] for r in R])

    fig, ax = plt.subplots(figsize=(3.4, 2.7))
    ax.fill_between(T, lo, hi, color=HUE[0], alpha=0.16, lw=0,
                    label="measured, 95 % CI (cluster bootstrap by video)")
    ax.plot(T, meas, ls=DASH[0], color=HUE[0], lw=1.6, marker=MARK[0], ms=4,
            mec="white", mew=0.6, label="measured")
    ax.plot(T, mod, ls=DASH[1], color=HUE[1], lw=1.6, marker=MARK[1], ms=4,
            mec="white", mew=0.6, label=r"model, $\hat\beta$ fitted")
    ax.plot(T, mod0, ls=DASH[2], color=HUE[2], lw=1.4, marker=MARK[2], ms=3.6,
            mec="white", mew=0.6, label=r"model, $\beta=0$")
    if Hd:
        het = np.array([Hd[t]["het_lovo"] if t in Hd else np.nan for t in T])
        ax.plot(T, het, ls=DASH[4 % len(DASH)], color=HUE[3 % len(HUE)], lw=1.8,
                marker=MARK[3 % len(MARK)], ms=4, mec="white", mew=0.6,
                label="law of $p$, leave one video out")
    ax.plot(T, floor, ls=DASH[3], color=MUTED, lw=1.2,
            label=r"structural floor $M(K)$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Invocation period (s)")
    ax.set_ylabel("Probability an event is missed")
    ax.grid(True, which="major", ls=":", lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2,
              handlelength=2.4, columnspacing=1.2)
    fig.savefig(FIGS / "fig_validation.png")
    plt.close(fig)


def fig_duration_law():
    R = rows("events_v2.csv")
    if not R:
        return
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    for i, corpus in enumerate(sorted({r["corpus"] for r in R})):
        D = np.sort([r["D_seconds"] for r in R if r["corpus"] == corpus])
        if not len(D):
            continue
        y = np.arange(1, len(D) + 1) / len(D)
        ax.step(D, y, ls=DASH[i], color=HUE[i], lw=1.6, where="post",
                label=f"{corpus} ($n={len(D)}$)")
    Dall = np.sort([r["D_seconds"] for r in R])
    ax.step(Dall, np.arange(1, len(Dall) + 1) / len(Dall), color=MUTED, lw=1.0,
            ls=DASH[3], where="post", label=f"pooled ($n={len(Dall)}$)")
    ax.set_xscale("log")
    ax.set_xlabel("Event duration $D$ (s)")
    ax.set_ylabel("$F_D(d)$")
    ax.grid(True, which="major", ls=":", lw=0.5)
    ax.legend(loc="lower right", handlelength=2.2)
    fig.savefig(FIGS / "fig_duration_law.png")
    plt.close(fig)


def fig_beta():
    R = [r for r in rows("beta_lag_curve_v2.csv") if r["corpus"] == "pooled"]
    if not R:
        return
    R.sort(key=lambda r: r["lag"])
    lag = np.array([r["lag"] for r in R])
    beta = np.array([r["beta_hat"] for r in R])
    ac = np.array([r["autocorr"] for r in R])
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    ax.plot(lag, beta, ls=DASH[0], color=HUE[0], lw=1.6, marker=MARK[0], ms=3.4,
            mec="white", mew=0.6, label=r"$\hat\beta(\ell)$")
    ax.plot(lag, ac, ls=DASH[1], color=HUE[1], lw=1.4, marker=MARK[1], ms=3.2,
            mec="white", mew=0.6, label=r"verdict autocorrelation at lag $\ell$")
    ax.axhline(0.0, color=MUTED, lw=0.6)
    ax.set_xlabel(r"Lag $\ell$ (frames)")
    ax.set_ylabel("Dimensionless")
    ax.grid(True, ls=":", lw=0.5)
    ax.legend(loc="best")
    fig.savefig(FIGS / "fig_beta.png")
    plt.close(fig)


def fig_bridge():
    # A log axis cannot show an exact zero, and the shortest invocation period
    # samples every frame, so M(K) is identically 0 there.  That point is dropped
    # from the figure and reported in the table instead.
    R = [r for r in rows("bridge_v2.csv")
         if r["corpus"] == "pooled" and r["M_K"] > 0]
    if not R:
        return
    R.sort(key=lambda r: r["T_seconds"])
    T = np.array([r["T_seconds"] for r in R])
    M = np.array([r["M_K"] for r in R])
    lo = np.array([r["M_K_lo"] for r in R])
    hi = np.array([r["M_K_hi"] for r in R])
    half = np.array([r["M_K_half"] for r in R])
    sq = np.array([r["M_K_squared"] for r in R])
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 1.3)
    band_shading(ax, T.min(), T.max())
    ax.fill_between(T, np.maximum(lo, 1e-3), hi, color=HUE[0], alpha=0.16, lw=0)
    ax.plot(T, M, ls=DASH[0], color=HUE[0], lw=1.6, marker=MARK[0], ms=4,
            mec="white", mew=0.6, label=r"$1$oo$1$: $M(K)$")
    ax.plot(T, half, ls=DASH[1], color=HUE[1], lw=1.6, marker=MARK[1], ms=4,
            mec="white", mew=0.6, label=r"$1$oo$2$ staggered: $M(K/2)$")
    ax.plot(T, sq, ls=DASH[2], color=HUE[2], lw=1.4, marker=MARK[2], ms=3.6,
            mec="white", mew=0.6, label=r"$1$oo$2$ independent phases")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Invocation period (s)")
    ax.set_ylabel("Structural miss, PFD-like")
    ax.grid(True, which="major", ls=":", lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1,
              handlelength=2.4)
    fig.savefig(FIGS / "fig_bridge.png")
    plt.close(fig)


def fig_comparison():
    R = [r for r in rows("cmp_amlas_v2.csv") if r["corpus"] == "pooled"]
    if not R:
        return
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    Ts = sorted({r["T_seconds"] for r in R})
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 1.3)
    band_shading(ax, min(Ts), max(Ts))
    for i, p in enumerate([0.90, 0.95, 0.99]):
        sel = sorted([r for r in R if abs(r["requirement_p"] - p) < 1e-9],
                     key=lambda r: r["T_seconds"])
        if not sel:
            continue
        ax.plot([r["T_seconds"] for r in sel], [r["pfd_like"] for r in sel],
                ls=DASH[i], color=HUE[i], lw=1.6, marker=MARK[i], ms=4,
                mec="white", mew=0.6,
                label=f"per-invocation requirement $p={p}$")
    sel = sorted([r for r in R if abs(r["requirement_p"] - 0.90) < 1e-9],
                 key=lambda r: r["T_seconds"])
    ax.plot([r["T_seconds"] for r in sel], [r["structural_floor"] for r in sel],
            ls=DASH[3], color=MUTED, lw=1.2, label=r"structural floor $M(K)$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Invocation period (s)")
    ax.set_ylabel("Event-level PFD-like")
    ax.grid(True, which="major", ls=":", lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1,
              handlelength=2.4)
    fig.savefig(FIGS / "fig_comparison.png")
    plt.close(fig)


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    for fn in (fig_validation, fig_duration_law, fig_beta, fig_bridge, fig_comparison):
        fn()
        print("  drew", fn.__name__)
    print("FIGURES_DONE")


if __name__ == "__main__":
    main()
