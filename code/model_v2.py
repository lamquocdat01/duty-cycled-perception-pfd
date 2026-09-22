"""model_v2.py -- Topic 35 / V2, VIEC 1 (U1-U3).

Sampling-miss model for a duty-cycled perception monitor, written in the
vocabulary of periodic-inspection reliability modelling.

Correspondence (see symbol_map()):

    delay-time model              SIS demand mode            this paper
    delay time            h       demand duration            event duration   D
    inspection interval   T       proof-test interval tau    invocation period K
    b(T)                          PFD contribution           M(K) = E_D[(1-D/K)_+]
    inspection imperfection r     proof-test coverage        per-invocation p

Quantities
----------
1.1  exact miss probability under a uniformly random schedule phase.
     With D = m K + phi K, m = floor(D/K), phi = D/K - m,

         P(miss | D) = (1 - phi) (1-p)^m + phi (1-p)^(m+1)

     The m = 0 case collapses to (1 - D/K) + (D/K)(1-p); p = 1 gives the
     structural floor (1 - D/K)_+ ; the V1 bound (1-p)^floor(D/K) is the
     phi -> 0 corner and is kept as a corollary (an upper bound).
1.2  within-event dependence as an IEC 61508-6 style beta-factor:

         g(k) = beta (1-p) + (1 - beta) (1-p)^k   for k >= 1,   g(0) = 1

     beta = 0 recovers 1.1, beta = 1 gives 1 - p for every k >= 1.  The two
     extremes reproduce the two bounds of V1, which closes the open defeater.
1.3  1oo2 redundancy: (a) two independent random phases, (b) schedules
     staggered by K/2, (c) a shared phase; plus the fixed-phase best/worst
     range, which is what randomising the phase buys.

Everything here is analytic.  verify_model_mc() checks every closed form
against an independent Monte-Carlo simulation of the schedule before any of it
is used downstream.
"""
from __future__ import annotations

import csv
import json
import pathlib

import numpy as np
from scipy.special import gammaln

SEED = 20260921
RESULTS = pathlib.Path(__file__).resolve().parents[1] / "results"


# ------------------------------------------------------------------ 1.1, 1.2

def g_beta(k, p, beta=0.0):
    """Miss probability of an event that receives exactly k invocations."""
    k = np.asarray(k, dtype=float)
    dep = beta * (1.0 - p) + (1.0 - beta) * (1.0 - p) ** np.maximum(k, 0.0)
    return np.where(k <= 0, 1.0, dep)


def p_miss_exact(D, K, p, beta=0.0):
    """Exact P(miss | D), one channel, uniformly random schedule phase."""
    D = np.asarray(D, dtype=float)
    m = np.floor(D / K)
    phi = D / K - m
    return (1.0 - phi) * g_beta(m, p, beta) + phi * g_beta(m + 1.0, p, beta)


# ------------------------------------------------- 1.2b heterogeneous p (V2.2)
#
# The layer added in dot 2c.  The exact phase result above conditions on ONE
# detection probability p.  Events do not share one: measured per event,
# p_e = (alarms in the event) / (frames in the event) has 70 % of its mass at
# zero on one site and 7 % on the other.  Writing F for the law of (D, p),
#
#     P(miss) = E_{(D,p) ~ F} [ (1 - phi)(1 - p)^m + phi (1 - p)^(m+1) ],
#               m = floor(D/K),  phi = D/K - m,
#
# which is the same integrand, integrated over one more variable.  Two
# consequences, both used in the paper:
#
#   (i)  x -> (1 - x)^k is convex, so by Jensen E[(1-p)^k] >= (1 - E[p])^k:
#        plugging a single mean p into the homogeneous formula gives a value no
#        larger than the truth.  The homogeneous model is therefore a LOWER
#        bound on the miss probability -- optimistic, not conservative.
#   (ii) the two-point mixture of the beta-factor model, p in {0, p}, is the
#        special case of a two-atom F, which is why beta-hat came out above 1:
#        the data wanted more dispersion than that mixture can express.


def p_miss_het_empirical(D, K, p_samples, beta=0.0):
    """P(miss | D, K) averaged over an empirical sample of p.

    D may be an array of event lengths; p_samples is the sample of detection
    probabilities to integrate over.  Returns one value per element of D.
    """
    D = np.atleast_1d(np.asarray(D, dtype=float))
    ps = np.atleast_1d(np.asarray(p_samples, dtype=float))
    out = np.empty(D.shape, dtype=float)
    for i, d in enumerate(D.ravel()):
        out.ravel()[i] = float(np.mean(p_miss_exact(d, K, ps, beta)))
    return out


def beta_moments(p_samples):
    """Method-of-moments Beta(a, b) for a sample of detection probabilities.

    Returns (a, b, mean, var).  a and b are None when the sample has no spread
    (or too little of it for a Beta to be defined), in which case the caller
    should fall back on the homogeneous formula.
    """
    ps = np.asarray(p_samples, dtype=float)
    mu = float(ps.mean())
    var = float(ps.var(ddof=1)) if ps.size > 1 else 0.0
    lim = mu * (1.0 - mu)
    if not (0.0 < mu < 1.0) or var <= 0.0 or var >= lim:
        return None, None, mu, var
    conc = lim / var - 1.0
    return mu * conc, (1.0 - mu) * conc, mu, var


def beta_with_mean(mu, conc):
    """Beta(a, b) with mean mu and concentration a + b = conc.

    Used on the design side to carry a *measured* amount of dispersion to a
    *required* mean detection probability, so that a requirement stated as a
    mean can be read at the event level.
    """
    return mu * conc, (1.0 - mu) * conc


def _e_one_minus_p_pow(k, a, b):
    """E[(1-p)^k] for p ~ Beta(a, b) = B(a, b+k) / B(a, b), in logs."""
    k = np.asarray(k, dtype=float)
    return np.exp(gammaln(a + b) + gammaln(b + k)
                  - gammaln(b) - gammaln(a + b + k))


def p_miss_het_beta(D, K, a, b):
    """P(miss | D, K) with p ~ Beta(a, b), in closed form."""
    D = np.asarray(D, dtype=float)
    m = np.floor(D / K)
    phi = D / K - m
    lo = np.where(m <= 0, 1.0, _e_one_minus_p_pow(np.maximum(m, 0.0), a, b))
    hi = _e_one_minus_p_pow(m + 1.0, a, b)
    return (1.0 - phi) * lo + phi * hi


def p_miss_1oo2_staggered_het(D, K, p_samples, beta=0.0):
    """Staggered 1oo2 under heterogeneous p: one schedule of period K/2."""
    return p_miss_het_empirical(D, K / 2.0, p_samples, beta)


def p_miss_1oo2_independent_het(D, K, p_samples, beta=0.0):
    """Two independent phases, heterogeneous p.  The two channels share the
    event, hence the same p_e: the square is taken inside the expectation."""
    D = np.atleast_1d(np.asarray(D, dtype=float))
    ps = np.atleast_1d(np.asarray(p_samples, dtype=float))
    out = np.empty(D.shape, dtype=float)
    for i, d in enumerate(D.ravel()):
        a = p_miss_exact(d, K, ps, beta)
        out.ravel()[i] = float(np.mean(a * a))
    return out


def p_miss_bound(D, K, p):
    """V1 corollary bound (1-p)^floor(D/K); an upper bound on p_miss_exact."""
    D = np.asarray(D, dtype=float)
    return (1.0 - p) ** np.floor(D / K)


def structural_floor(D, K):
    """Integrand of M(K): the p -> 1 limit of 1.1, i.e. (1 - D/K)_+ ."""
    D = np.asarray(D, dtype=float)
    return np.maximum(0.0, 1.0 - D / K)


# ------------------------------------------------------------------ 1.3

def p_miss_1oo2_independent(D, K, p, beta=0.0):
    """Two channels of period K with independent uniform phases."""
    a = p_miss_exact(D, K, p, beta)
    return a * a


def p_miss_1oo2_staggered(D, K, p, beta=0.0):
    """Two channels of period K offset by exactly K/2: the union of the two
    schedules is a single schedule of period K/2."""
    return p_miss_exact(D, K / 2.0, p, beta)


def p_miss_1oo2_common_phase(D, K, p, beta=0.0):
    """Both channels fire at the same instants; per instant the pair misses
    with probability (1-p)^2 when the channels fail independently."""
    return p_miss_exact(D, K, 1.0 - (1.0 - p) ** 2, beta)


def fixed_phase_range(D, K):
    """Structural miss (p = 1) of a *deterministic* phase.  An event shorter
    than K can be missed with probability 1 if its onset is adversarially
    aligned with the schedule, or 0 if favourably aligned; randomising the
    phase is what buys the average (1 - D/K)_+ ."""
    D = np.asarray(D, dtype=float)
    worst = np.where(D < K, 1.0, 0.0)
    return np.zeros_like(worst), worst


# ------------------------------------------------------------------ MC check

def _n_invocations(D, K, u):
    """Invocations of a channel with phase u inside the window [0, D)."""
    return np.maximum(0, np.ceil((D - u) / K)).astype(np.int64)


def _channel_miss(k, p, beta, rng):
    """Miss indicator per event given the invocation count k (vector)."""
    n = k.shape[0]
    kmax = int(max(k.max(), 1))
    tied = rng.random(n) < beta
    det_tied = rng.random(n) < p
    draws = rng.random((n, kmax)) < p
    live = np.arange(kmax)[None, :] < k[:, None]
    det_indep = (draws & live).any(axis=1)
    detected = np.where(tied, det_tied & (k > 0), det_indep)
    return ~detected


def _simulate(D, K, p, beta, n, rng, mode):
    if mode == "single":
        k = _n_invocations(D, K, rng.random(n) * K)
        return float(_channel_miss(k, p, beta, rng).mean())
    if mode == "1oo2_independent":
        k1 = _n_invocations(D, K, rng.random(n) * K)
        k2 = _n_invocations(D, K, rng.random(n) * K)
        m1 = _channel_miss(k1, p, beta, rng)
        m2 = _channel_miss(k2, p, beta, rng)
        return float((m1 & m2).mean())
    if mode == "1oo2_staggered":
        u = rng.random(n) * K
        k = _n_invocations(D, K, u) + _n_invocations(D, K, (u + K / 2.0) % K)
        return float(_channel_miss(k, p, beta, rng).mean())
    if mode == "1oo2_common_phase":
        k = _n_invocations(D, K, rng.random(n) * K)
        return float(_channel_miss(k, 1.0 - (1.0 - p) ** 2, beta, rng).mean())
    raise ValueError(mode)


GRID = dict(p=[0.60, 0.90, 0.95, 0.99], K=[5, 15, 30],
            D=[1, 3, 7, 15, 22, 40, 90], beta=[0.0, 0.1, 0.5])
GRID_RED = dict(p=[0.90, 0.99], K=[15, 30], D=[3, 10, 22, 40], beta=[0.0, 0.2])


def _se(an, n):
    """Standard error of the MC estimate under the analytic value (so that a
    cell whose simulated count happens to be zero still gets a finite yardstick;
    the +1/n floor is the usual rule-of-three correction)."""
    v = max(an * (1.0 - an), 1.0 / n)
    return float(np.sqrt(v / n))


def verify_model_mc(n_per_cell=200_000, verbose=True):
    """Check every closed form against simulation on a p x K x D x beta grid."""
    rng = np.random.default_rng(SEED)
    rows = []
    for p in GRID["p"]:
        for K in GRID["K"]:
            for D in GRID["D"]:
                for beta in GRID["beta"]:
                    mc = _simulate(D, K, p, beta, n_per_cell, rng, "single")
                    an = float(p_miss_exact(D, K, p, beta))
                    rows.append(dict(model="single", p=p, K=K, D=D, beta=beta,
                                     analytic=an, mc=mc, abs_err=abs(an - mc),
                                     se=_se(an, n_per_cell)))
    fns = {"1oo2_independent": p_miss_1oo2_independent,
           "1oo2_staggered": p_miss_1oo2_staggered,
           "1oo2_common_phase": p_miss_1oo2_common_phase}
    for p in GRID_RED["p"]:
        for K in GRID_RED["K"]:
            for D in GRID_RED["D"]:
                for beta in GRID_RED["beta"]:
                    for mode, fn in fns.items():
                        mc = _simulate(D, K, p, beta, n_per_cell, rng, mode)
                        an = float(fn(D, K, p, beta))
                        rows.append(dict(model=mode, p=p, K=K, D=D, beta=beta,
                                         analytic=an, mc=mc, abs_err=abs(an - mc),
                                         se=_se(an, n_per_cell)))
    n_cells = len(rows)
    tol = lambda r: max(4.0 * r["se"], 2e-3)
    fails = [r for r in rows if r["abs_err"] > tol(r)]
    worst = max(rows, key=lambda r: r["abs_err"] / max(r["se"], 1e-9))
    summary = dict(n_cells=n_cells, n_per_cell=n_per_cell,
                   n_events=n_cells * n_per_cell, n_fail=len(fails),
                   worst_abs_err=worst["abs_err"],
                   worst_z=worst["abs_err"] / max(worst["se"], 1e-9),
                   worst_cell={k: worst[k] for k in ("model", "p", "K", "D", "beta")},
                   max_abs_err=max(r["abs_err"] for r in rows), seed=SEED,
                   tolerance="max(4 standard errors, 0.002)")
    if verbose:
        print(f"MC validation: {n_cells} cells x {n_per_cell:,} events "
              f"= {summary['n_events']:,} simulated events")
        print(f"  max |analytic - MC|          : {summary['max_abs_err']:.5f}")
        print(f"  worst cell in s.e. units     : {summary['worst_z']:.2f}  "
              f"at {summary['worst_cell']}")
        print(f"  cells outside tolerance      : {len(fails)}")
        for r in fails[:10]:
            print("   FAIL", r)
    return rows, summary


# ------------------------------------------------------------------ tables

def symbol_map():
    """Rows of the delay-time / SIS / this-paper correspondence table (1.4)."""
    return [
        ("Defect arrival", "-", "Demand onset", "-", "Event onset", "t_0"),
        ("Delay time", "h", "Demand duration", "tau_D", "Event duration", "D"),
        ("Inspection interval", "T", "Proof-test interval", "tau",
         "Invocation period", "K"),
        ("Delay-time p.d.f.", "f(h)", "Demand-duration distribution", "F_D",
         "Event-duration law", "F_D"),
        ("Prob. defect missed", "b(T)", "PFD from test policy", "PFD_avg",
         "Structural sampling miss", "M(K)"),
        ("Imperfect inspection", "r", "Proof-test coverage", "c_PT",
         "Per-invocation detection", "p"),
        ("-", "-", "Common-cause beta-factor", "beta",
         "Within-event dependence", "beta"),
        ("-", "-", "Staggered proof testing", "-",
         "Staggered 1oo2 schedules", "K/2"),
        ("Dangerous undetected rate", "-", "lambda_DU", "lambda_DU",
         "Not required: M(K) > 0 at lambda_DU = 0", "-"),
    ]


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows, summary = verify_model_mc()
    with open(RESULTS / "model_mc_validation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(RESULTS / "model_mc_validation.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    print("wrote", RESULTS / "model_mc_validation.csv")
    if summary["n_fail"]:
        raise SystemExit("MC validation FAILED -- do not use the closed forms")


if __name__ == "__main__":
    main()
