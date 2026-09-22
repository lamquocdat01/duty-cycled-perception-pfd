"""case_study_v2.py -- Topic 35 / V2, VIEC 2.

Turns the cached per-frame detections of run_detector.py into every quantity of
EVAL_PROTOCOL_V2.md sections 4, 6 and 8.  Nothing is decided here that is not
written in the frozen protocol; the settings dictionaries below are transcribed
from it and the protocol hash is checked on entry.

Outputs (all under ../results):
    events_v2.csv                 one row per event, primary setting
    fd_summary_v2.csv             duration law summary, in seconds
    p_beta_v2.csv                 p_hat and beta_hat per corpus, with intervals
    beta_lag_curve_v2.csv         beta_hat(l) and verdict autocorrelation
    miss_validation_v2.csv        measured vs modelled miss rate against K
    far_latency_v2.csv            false alarms per hour and latency quantiles
    bridge_v2.csv                 M(K), PFD-like, band, n_req, 1oo2 variants
    sensitivity_v2.csv            every axis of protocol section 8
    numbers_v2.json               everything the manuscript is allowed to quote
"""
from __future__ import annotations

import configparser
import csv
import hashlib
import json
import math
import pathlib
import sys
from collections import defaultdict

import numpy as np

import model_v2 as M

EVAL = pathlib.Path(__file__).resolve().parents[1]
DATA = EVAL / "data"
RESULTS = EVAL / "results"
CACHE = RESULTS / "det_cache"
SEED = 20260921
BOOT = 2000

# ---- transcribed from EVAL_PROTOCOL_V2.md ---------------------------------
ZONES = {
    "Z1": [(0.30, 1.00), (0.70, 1.00), (0.60, 0.60), (0.40, 0.60)],
    "Z2": [(0.00, 0.55), (0.20, 0.55), (0.20, 1.00), (0.00, 1.00)],
    "Z3": [(0.80, 0.55), (1.00, 0.55), (1.00, 1.00), (0.80, 1.00)],
}
# ---- V2.1 primary setting (protocol V2.1 sections 4, 6, 9) ----------------
# gap_s is 0.5 s, up from 0.0 in V2.0: a single incursion that flickers out for
# less than the reaction time is still one demand.  0.5 s is declared as a
# convention, not derived, because ISO 13855 could not be read (action A-W1).
PRIMARY = dict(visibility=0.25, score=0.50, aspect=1.00, gap_s=0.5,
               censored="exclude", urfd_labels=(1,), appearance="all",
               alarm_mode="any_box")
SENS = {
    "score": [0.30, 0.50, 0.70],
    "appearance": ["all", "exclude_occluded"],
    "alarm_mode": ["any_box", "gt_matched"],
    "gap_s": [0.0, 0.1, 0.5, 1.0],
    "censored": ["exclude", "include"],
    "aspect": [0.80, 1.00, 1.20],
    "urfd_labels": [(1,), (0, 1)],
    "visibility": [0.00, 0.25, 0.50],
}
# invocation periods, in seconds -- the common axis across corpora
T_GRID = [1 / 30, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0]
SIL_BANDS = [("SIL 4", 1e-5, 1e-4), ("SIL 3", 1e-4, 1e-3),
             ("SIL 2", 1e-3, 1e-2), ("SIL 1", 1e-2, 1e-1)]


def sil_band(x):
    if x is None or not np.isfinite(x) or x <= 0:
        return "n/a"
    if x >= 1e-1:
        return "below SIL 1"
    if x < 1e-5:
        return "beyond SIL 4"
    for name, lo, hi in SIL_BANDS:
        if lo <= x < hi:
            return name
    return "below SIL 1"


def check_protocol():
    rec = json.load(open(RESULTS / "protocol_v2_1_freeze.json", encoding="utf-8"))
    h = hashlib.sha256((EVAL / "EVAL_PROTOCOL_V2_1.md").read_bytes()).hexdigest()
    if h != rec["sha256"]:
        raise SystemExit("EVAL_PROTOCOL_V2_1.md changed since freeze; see section 11")
    return rec


# ---------------------------------------------------------------- geometry

def point_in_poly(x, y, poly):
    """Ray casting; poly is a list of (x, y) in the same units as x, y."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                inside = not inside
    return inside


def points_in_poly(xs, ys, poly):
    return np.array([point_in_poly(x, y, poly) for x, y in zip(xs, ys)], dtype=bool)


# ---------------------------------------------------------------- loading

def load_mot17():
    """-> dict seq -> dict(fps, n_frames, w, h, gt=(frame,x,y,w,h,vis), det=...)"""
    root = DATA / "MOT17Det" / "train"
    out = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        cp = configparser.ConfigParser()
        cp.read(d / "seqinfo.ini")
        s = cp["Sequence"]
        gt = []
        with open(d / "gt" / "gt.txt", encoding="utf-8") as f:
            for row in csv.reader(f):
                if not row:
                    continue
                fr, _id, x, y, w, h, conf, cls = (float(v) for v in row[:8])
                vis = float(row[8]) if len(row) > 8 else 1.0
                if int(conf) == 1 and int(cls) == 1:
                    gt.append((int(fr), x, y, w, h, vis))
        cache = np.load(CACHE / f"MOT17Det__{d.name}.npz")
        out[d.name] = dict(fps=float(s["frameRate"]), n_frames=int(s["seqLength"]),
                           w=float(s["imWidth"]), h=float(s["imHeight"]),
                           gt=np.array(gt, dtype=np.float64),
                           det_frame=cache["frame"], det_box=cache["box"],
                           det_score=cache["score"])
    return out


def _urfd_labels(path):
    lab = defaultdict(dict)
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            lab[row[0]][int(row[1])] = int(row[2])
    return lab


def load_urfd():
    root = DATA / "URFall"
    if not (root / "urfall-cam0-falls.csv").exists():
        return {}
    falls = _urfd_labels(root / "urfall-cam0-falls.csv")
    adls = _urfd_labels(root / "urfall-cam0-adls.csv")
    out = {}
    for name, lab in list(falls.items()) + list(adls.items()):
        cache_f = CACHE / f"URFD__{name}.npz"
        if not cache_f.exists():
            continue
        cache = np.load(cache_f)
        # frame rate from the timestamp column of <seq>-data.csv
        fps, resid = 30.0, None
        dfile = root / "_zips" / f"{name}-data.csv"
        if dfile.exists():
            fr, ms = [], []
            with open(dfile, encoding="utf-8") as f:
                for row in csv.reader(f):
                    if len(row) >= 2:
                        try:
                            fr.append(float(row[0])); ms.append(float(row[1]))
                        except ValueError:
                            pass
            if len(fr) > 5:
                A = np.vstack([np.array(ms) / 1000.0, np.ones(len(ms))]).T
                sol, res, *_ = np.linalg.lstsq(A, np.array(fr), rcond=None)
                fps = float(sol[0])
                pred = A @ sol
                resid = float(np.sqrt(np.mean((pred - np.array(fr)) ** 2)))
        out[name] = dict(kind="fall" if name.startswith("fall") else "adl",
                         fps=fps, fps_resid=resid, labels=lab,
                         det_frame=cache["frame"], det_box=cache["box"],
                         det_score=cache["score"])
    return out


# ---------------------------------------------------- per-frame series

def mot17_boxes_by_frame(seq, visibility=0.0):
    """frame -> list of (x1, y1, x2, y2) annotated person boxes, in pixels."""
    from collections import defaultdict as _dd
    out = _dd(list)
    gt = seq["gt"]
    if not len(gt):
        return out
    g = gt[gt[:, 5] >= visibility]
    for fr, x, y, w, h, _v in g:
        out[int(fr)].append((x, y, x + w, y + h))
    return out


def mot17_series(seq, zone, visibility, score, alarm_mode="any_box"):
    """(frames, hazard, alarm) over the whole sequence, for one (seq, zone).

    alarm_mode is the axis added by protocol Amendment 2': under gt_matched a
    firing detection must also match an annotated person at IoU >= 0.3, so a
    static false positive sitting inside a zone cannot raise every alarm.
    """
    import caviar_v2_1 as CV
    n = seq["n_frames"]
    W, H = seq["w"], seq["h"]
    poly = ZONES[zone]
    hazard = np.zeros(n + 1, dtype=bool)
    gt = seq["gt"]
    if len(gt):
        keep = gt[:, 5] >= visibility
        g = gt[keep]
        fx = (g[:, 1] + g[:, 3] / 2.0) / W
        fy = (g[:, 2] + g[:, 4]) / H
        ins = points_in_poly(fx, fy, poly)
        for fr in g[ins, 0].astype(int):
            if 1 <= fr <= n:
                hazard[fr] = True
    alarm = np.zeros(n + 1, dtype=bool)
    ds = seq["det_score"]
    if len(ds):
        keep = ds >= score
        b = seq["det_box"][keep]
        fr = seq["det_frame"][keep]
        fx = ((b[:, 0] + b[:, 2]) / 2.0) / W
        fy = b[:, 3] / H
        ins = points_in_poly(fx, fy, poly)
        gtbf = mot17_boxes_by_frame(seq, visibility) if alarm_mode == "gt_matched" else None
        for f_, box in zip(fr[ins], b[ins]):
            if not (1 <= f_ <= n):
                continue
            if gtbf is not None and not any(
                    CV.iou(box, gb) >= CV.GT_MATCH_IOU for gb in gtbf.get(int(f_), [])):
                continue
            alarm[f_] = True
    idx = np.arange(1, n + 1)
    return idx, hazard[1:], alarm[1:]


def urfd_series(seq, score, aspect, labels):
    frames = np.array(sorted(seq["labels"].keys()), dtype=int)
    if not len(frames):
        return frames, np.zeros(0, bool), np.zeros(0, bool)
    hazard = np.array([seq["labels"][f] in labels for f in frames], dtype=bool)
    fire = set()
    ds = seq["det_score"]
    if len(ds):
        keep = ds >= score
        b = seq["det_box"][keep]
        fr = seq["det_frame"][keep]
        w = b[:, 2] - b[:, 0]
        h = np.maximum(b[:, 3] - b[:, 1], 1e-6)
        fire.update(fr[(w / h) >= aspect].tolist())
    alarm = np.array([f in fire for f in frames], dtype=bool)
    return frames, hazard, alarm


# ---------------------------------------------------------------- events

def runs(mask):
    """Maximal runs of True: list of (start_index, end_index) inclusive."""
    out = []
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def merge_runs(rr, gap_frames):
    if gap_frames <= 0 or not rr:
        return rr
    out = [list(rr[0])]
    for s, e in rr[1:]:
        if s - out[-1][1] - 1 <= gap_frames:
            out[-1][1] = e
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def build_events(frames, hazard, alarm, fps, gap_s, corpus, channel, video, zone):
    rr = merge_runs(runs(hazard), int(round(gap_s * fps)))
    evs = []
    n = len(frames)
    for k, (i, j) in enumerate(rr):
        censored = (i == 0) or (j == n - 1)
        evs.append(dict(corpus=corpus, channel=channel, video=video, zone=zone,
                        event_id=k, i0=i, i1=j, start_frame=int(frames[i]),
                        end_frame=int(frames[j]), n_frames=j - i + 1, fps=fps,
                        D_seconds=(j - i + 1) / fps, censored=censored,
                        n_alarm=int(alarm[i:j + 1].sum())))
    return evs


# ------------------------------------------------------- estimators

def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    hw = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - hw), min(1.0, c + hw))


def cluster_bootstrap(per_video, stat, rng, B=BOOT):
    """per_video: dict video -> payload; stat(list_of_payloads) -> float."""
    keys = list(per_video)
    if not keys:
        return (float("nan"), float("nan"))
    vals = []
    for _ in range(B):
        pick = [per_video[keys[i]] for i in rng.integers(0, len(keys), len(keys))]
        v = stat(pick)
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def beta_from_pairs(verdicts, lag, q):
    """Moment estimator of the beta-factor at a given lag.
    verdicts: list of boolean arrays (alarm) restricted to hazard-active frames
    of one event.  P2 = P(both invocations miss).  beta = (P2 - q^2)/(q - q^2)."""
    both, tot = 0, 0
    for v in verdicts:
        if len(v) <= lag:
            continue
        a = ~v[:-lag]
        b = ~v[lag:]
        both += int((a & b).sum())
        tot += len(a)
    if tot == 0 or q <= 0 or q >= 1:
        return float("nan"), tot, float("nan")
    p2 = both / tot
    denom = q - q * q
    return (p2 - q * q) / denom if denom > 0 else float("nan"), tot, p2


def autocorr(verdicts, lag):
    xs, ys = [], []
    for v in verdicts:
        if len(v) <= lag:
            continue
        xs.append(v[:-lag].astype(float))
        ys.append(v[lag:].astype(float))
    if not xs:
        return float("nan")
    x = np.concatenate(xs); y = np.concatenate(ys)
    if x.std() < 1e-12 or y.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def measured_miss(events_alarm, K):
    """Exact enumeration over all K phases.  events_alarm: list of bool arrays."""
    if K < 1:
        K = 1
    miss, tot = 0, 0
    for a in events_alarm:
        n = len(a)
        for phi in range(K):
            s = a[phi::K]
            tot += 1
            if not s.any():
                miss += 1
    return (miss / tot) if tot else float("nan"), tot


def first_hit_latency(alarm, K, fps):
    """Time from event onset to the first firing invocation, one value per
    schedule phase in which the event is detected at all."""
    lat = []
    for phi in range(K):
        idx = np.arange(phi, len(alarm), K)
        hit = idx[alarm[idx]]
        if len(hit):
            lat.append(hit[0] / fps)
    return lat


# ------------------------------------------------------------ channels

# Protocol V2.1 section 3: only these MOT17Det sequences are static, and they are
# a secondary stratum -- never pooled into the primary analysis.
MOT17_STATIC = ("MOT17-02", "MOT17-04", "MOT17-09")


def build_channels(mot, urfd, setting, caviar=None, scope="primary"):
    """One entry per monitoring channel, with its per-frame series.

    `scope` decides which corpora are in play, because V2.1 keeps them apart:
      primary  -- the static-camera CAVIAR sites (protocol section 2)
      contrast -- URFD, the long-hazard case of section 8
      stratum  -- the three static MOT17Det sequences, reported but never pooled
    """
    import caviar_v2_1 as CV
    chans = []

    if scope in ("primary", "all") and caviar:
        for key, seq in caviar.items():
            for zone in CV.ZONES_SITE[seq["site"]]:
                fr, hz, al, edge = CV.caviar_series(
                    seq, zone, setting["score"], setting.get("appearance", "all"),
                    setting.get("alarm_mode", "any_box"))
                if not len(fr):
                    continue
                chans.append(dict(corpus=seq["site"], video=seq["video"], zone=zone,
                                  channel=f"{seq['video']}/{zone}", fps=seq["fps"],
                                  frames=fr, hazard=hz, alarm=al, edge_px=edge,
                                  zone_scale_px=CV.zone_scale_px(
                                      CV.ZONES_SITE[seq["site"]][zone])))

    if scope in ("contrast", "all"):
        for name, seq in urfd.items():
            fr, hz, al = urfd_series(seq, setting["score"], setting["aspect"],
                                     setting["urfd_labels"])
            if not len(fr):
                continue
            chans.append(dict(corpus="URFD", video=name, zone=seq["kind"],
                              channel=name, fps=seq["fps"],
                              frames=fr, hazard=hz, alarm=al))

    if scope in ("stratum", "all"):
        for name, seq in mot.items():
            if name not in MOT17_STATIC:
                continue
            for zone in ZONES:
                fr, hz, al = mot17_series(seq, zone, setting["visibility"],
                                          setting["score"],
                                          setting.get("alarm_mode", "any_box"))
                chans.append(dict(corpus="MOT17Det-static", video=name, zone=zone,
                                  channel=f"{name}/{zone}", fps=seq["fps"],
                                  frames=fr, hazard=hz, alarm=al))
    return chans


def _events_of(chans, setting, keep_censored):
    out = []
    for c in chans:
        for e in build_events(c["frames"], c["hazard"], c["alarm"], c["fps"],
                              setting["gap_s"], c["corpus"], c["channel"],
                              c["video"], c["zone"]):
            if not keep_censored and e["censored"]:
                continue
            out.append((e, c["alarm"][e["i0"]:e["i1"] + 1]))
    return out


def analyse(chans, setting, rng, full=False, light=False):
    """Every quantity of protocol sections 6 and 7, for one setting.

    `light` is for the sensitivity sweep of protocol section 8, which compares
    *point estimates* across settings: it drops the cluster bootstraps and
    restricts the invocation-period grid to the two periods the sensitivity
    table reports.  It changes no estimator -- the point estimates it returns
    are bit-identical to the full run's -- only what is computed alongside them.
    """
    res = {}
    tgrid = [0.5, 1.0] if light else T_GRID
    # V2.1: the corpus list follows the channels rather than being hard-coded,
    # because which corpora are in play now depends on the scope.
    corpora = ["pooled"] + sorted({c["corpus"] for c in chans})
    res["corpora"] = corpora

    def boot(pv, stat, B=BOOT):
        if light:
            return (float("nan"), float("nan"))
        return cluster_bootstrap(pv, stat, rng, B=B)

    keep_c = setting["censored"] == "include"
    pairs = _events_of(chans, setting, keep_c)
    events = [e for e, _ in pairs]
    ev_alarm = [a for _, a in pairs]
    ev_corpus = [e["corpus"] for e in events]

    res["n_events"] = len(events)
    res["n_events_censored"] = sum(
        1 for e, _ in _events_of(chans, setting, True) if e["censored"])

    D = np.array([e["D_seconds"] for e in events]) if events else np.zeros(0)
    if len(D):
        for q, lab in ((5, "q05"), (25, "q25"), (50, "median"), (75, "q75"), (95, "q95")):
            res[f"D_{lab}"] = float(np.percentile(D, q))
        res["D_mean"] = float(D.mean())
        res["D_min"] = float(D.min())
        res["D_max"] = float(D.max())

    # ---- p_hat, per corpus and pooled
    per_video_p = defaultdict(lambda: [0, 0])
    for c in chans:
        m = c["hazard"]
        key = (c["corpus"], c["video"])
        per_video_p[key][0] += int(m.sum())
        per_video_p[key][1] += int((c["alarm"] & m).sum())

    def p_for(corpus=None):
        n = k = 0
        pv = {}
        for (cp, vid), (nn, kk) in per_video_p.items():
            if corpus and cp != corpus:
                continue
            n += nn
            k += kk
            a, b = pv.get(vid, (0, 0))
            pv[vid] = (a + nn, b + kk)
        if n == 0:
            return None
        lo, hi = wilson(k, n)

        def stat(pick):
            nn = sum(x[0] for x in pick)
            kk = sum(x[1] for x in pick)
            return kk / nn if nn else None

        clo, chi = boot(pv, stat)
        return dict(n_active_frames=n, n_alarm=k, p_hat=k / n,
                    wilson_lo=lo, wilson_hi=hi, boot_lo=clo, boot_hi=chi)

    res["p"] = {c: (p_for() if c == "pooled" else p_for(c)) for c in corpora}

    # ---- beta curve, per corpus
    res["beta_curve"] = {}
    for corpus in corpora:
        pr = res["p"][corpus]
        if not pr:
            continue
        q = 1.0 - pr["p_hat"]
        vv = [a for a, cp in zip(ev_alarm, ev_corpus)
              if corpus == "pooled" or cp == corpus]
        curve = []
        for lag in range(1, 31):
            b, tot, p2 = beta_from_pairs(vv, lag, q)
            curve.append(dict(lag=lag, beta_hat=b, n_pairs=tot, p_both_miss=p2,
                              autocorr=autocorr(vv, lag)))
        res["beta_curve"][corpus] = curve

    def beta_at(corpus, K):
        curve = res["beta_curve"].get(corpus)
        if not curve:
            return 0.0
        v = curve[min(max(K, 1), 30) - 1]["beta_hat"]
        return float(np.clip(v, 0.0, 1.0)) if np.isfinite(v) else 0.0

    # ---- measured vs modelled miss, against the invocation period in seconds
    rows = []
    for T in tgrid:
        for corpus in corpora:
            sel = [(a, e) for a, e, cp in zip(ev_alarm, events, ev_corpus)
                   if corpus == "pooled" or cp == corpus]
            pr = res["p"][corpus]
            if not sel or not pr:
                continue
            p_hat = pr["p_hat"]
            num = den = 0
            model_b, model_0, floor = [], [], []
            for a, e in sel:
                K = max(1, int(round(T * e["fps"])))
                m, t = measured_miss([a], K)
                num += m * t
                den += t
                model_b.append(float(M.p_miss_exact(e["n_frames"], K, p_hat,
                                                    beta_at(corpus, K))))
                model_0.append(float(M.p_miss_exact(e["n_frames"], K, p_hat, 0.0)))
                floor.append(max(0.0, 1.0 - e["n_frames"] / K))
            pv = defaultdict(list)
            for a, e in sel:
                pv[e["video"]].append((a, e))

            def stat(pick):
                nu = de = 0
                for grp in pick:
                    for a, e in grp:
                        K = max(1, int(round(T * e["fps"])))
                        m, t = measured_miss([a], K)
                        nu += m * t
                        de += t
                return nu / de if de else None

            lo, hi = boot(pv, stat, B=400)
            rows.append(dict(T_seconds=T, corpus=corpus, n_events=len(sel),
                             miss_measured=num / den if den else float("nan"),
                             miss_lo=lo, miss_hi=hi,
                             miss_model_beta=float(np.mean(model_b)),
                             miss_model_beta0=float(np.mean(model_0)),
                             structural_floor=float(np.mean(floor)),
                             p_hat=p_hat, beta_used=beta_at(corpus,
                                 max(1, int(round(T * 30))))))
    res["miss_rows"] = rows

    # ---- false alarms
    fa = []
    for corpus in [c for c in corpora if c != "pooled"]:
        n_neg = n_fa = 0
        fpss = []
        for c in chans:
            if c["corpus"] != corpus:
                continue
            neg = ~c["hazard"]
            n_neg += int(neg.sum())
            n_fa += int((c["alarm"] & neg).sum())
            fpss.append(c["fps"])
        if n_neg == 0:
            continue
        rate = n_fa / n_neg
        for T in tgrid:
            fa.append(dict(corpus=corpus, T_seconds=T, n_negative_frames=n_neg,
                           n_false_alarm_frames=n_fa, fa_frame_rate=rate,
                           alarms_per_hour=rate * 3600.0 / T,
                           mean_fps=float(np.mean(fpss))))
    res["fa_rows"] = fa

    # ---- latency
    lat = []
    for T in tgrid:
        for corpus in corpora:
            vals, bounds = [], []
            for a, e, cp in zip(ev_alarm, events, ev_corpus):
                if corpus != "pooled" and cp != corpus:
                    continue
                K = max(1, int(round(T * e["fps"])))
                vals += first_hit_latency(a, K, e["fps"])
                bounds.append((K - 1) / e["fps"])
            if not vals:
                continue
            v = np.array(vals)
            lat.append(dict(T_seconds=T, corpus=corpus, n=len(v),
                            mean_s=float(v.mean()), median_s=float(np.median(v)),
                            q95_s=float(np.percentile(v, 95)), max_s=float(v.max()),
                            bound_s=float(np.mean(bounds)),
                            frac_over_bound=float(np.mean(
                                v > float(np.mean(bounds))))))
    res["latency_rows"] = lat

    # ---- bridge quantities
    br = []
    for T in tgrid:
        for corpus in corpora:
            sel = [e for e, cp in zip(events, ev_corpus)
                   if corpus == "pooled" or cp == corpus]
            if not sel:
                continue
            Kf = [max(1, int(round(T * e["fps"]))) for e in sel]
            nF = [e["n_frames"] for e in sel]
            MK = float(np.mean([max(0.0, 1 - n / k) for n, k in zip(nF, Kf)]))
            MKh = float(np.mean([max(0.0, 1 - n / max(1, k / 2.0))
                                 for n, k in zip(nF, Kf)]))
            MKsq = float(np.mean([max(0.0, 1 - n / k) ** 2 for n, k in zip(nF, Kf)]))
            pv = defaultdict(list)
            for e, n, k in zip(sel, nF, Kf):
                pv[e["video"]].append(max(0.0, 1 - n / k))
            lo, hi = boot(
                pv, lambda pick: float(np.mean([x for g in pick for x in g])))
            br.append(dict(T_seconds=T, corpus=corpus, n_events=len(sel),
                           M_K=MK, M_K_lo=lo, M_K_hi=hi, band=sil_band(MK),
                           M_K_half=MKh, M_K_squared=MKsq,
                           gain_staggered=(MKh / MK) if MK > 0 else float("nan"),
                           gain_independent=(MKsq / MK) if MK > 0 else float("nan")))
    res["bridge_rows"] = br
    if full:
        res["events"] = events
    return res
