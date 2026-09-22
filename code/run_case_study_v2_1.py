"""run_case_study_v2_1.py -- Topic 35 / V2.1 driver (đợt 2b).

Replaces run_case_study.py, which is kept unchanged as the record of the V2.0
run.  The estimators are the same; what is new is that V2.1 keeps three groups
of corpora apart instead of pooling them:

    primary   the static-camera CAVIAR sites          -> the paper's numbers
    contrast  URFD, on the include-censored axis      -> the long-hazard case
    stratum   the three static MOT17Det sequences     -> reported, never pooled

plus the static-camera gate, the same-camera check, the flicker diagnostics and
the V2.0 -> V2.1 comparison the protocol makes mandatory.
"""
from __future__ import annotations

import csv
import json
import pathlib
from collections import defaultdict

import numpy as np

import case_study_v2 as C
import caviar_v2_1 as CV
import model_v2 as M

RESULTS = C.RESULTS


def write_csv(path, rows, fields=None):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fields or list(rows[0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def self_test():
    bad = [(n, K) for n in range(1, 41) for K in range(1, 41)
           if abs(C.measured_miss([np.ones(n, dtype=bool)], K)[0]
                  - float(M.p_miss_exact(n, K, 1.0))) > 1e-12]
    if bad:
        raise SystemExit(f"phase enumeration disagrees with the closed form at {bad[:5]}")
    print("self-test: phase enumeration == closed form on 1600 (n,K) cells", flush=True)


def aspect_rows(caviar):
    """Median ground-truth box aspect per site.  DESCRIPTIVE ONLY.

    An earlier Amendment 2 gated on this quantity; Amendment 2' withdrew the
    gate, because the detector boxes it was compared against turned out to be
    dominated by one static false positive.  Nothing is selected here.
    """
    rows = []
    for site in ("INRIA", "LISBON"):
        d = C.DATA / "CAVIAR" / site
        if not d.exists():
            continue
        med, n = CV.site_aspect(d)
        rows.append(dict(site=f"CAVIAR-{site}", median_aspect=med, n_boxes=n,
                         role="primary -- no site is excluded (Amendment 2')"))
    return rows


URFD_W, URFD_H = 640.0, 480.0        # cam0 RGB, verified on the frames


def detector_audit(caviar, mot, urfd, score):
    """Protocol section 11, Amendment 2': recall and precision of the detector
    against the annotation, and the share of its detections falling in the
    single most frequent cell, for EVERY corpus -- not only the one whose
    numbers looked wrong."""
    rows = []
    for s_ in caviar.values():
        r = CV.detector_quality(s_, score)
        r["corpus"] = s_["site"]
        rows.append(r)
    for name, s_ in mot.items():
        if name not in C.MOT17_STATIC:
            continue
        boxes = C.mot17_boxes_by_frame(s_, 0.0)
        r = CV.detector_quality_generic(boxes, s_["det_frame"], s_["det_box"],
                                        s_["det_score"], score, s_["w"], s_["h"],
                                        name, zones=C.ZONES,
                                        n_frames=s_["n_frames"])
        r["corpus"] = "MOT17Det-static"
        rows.append(r)
    for name, s_ in urfd.items():
        # URFD is annotated with a per-frame posture class and no boxes, so
        # recall and precision are undefined there and come back as NaN.  The
        # concentration statistic still applies.
        # URFD has no zones either -- its hazard is a posture label, so a
        # static false positive cannot "stand in a zone" there; the cell
        # statistics are still reported.
        r = CV.detector_quality_generic({}, s_["det_frame"], s_["det_box"],
                                        s_["det_score"], score, URFD_W, URFD_H,
                                        name, zones=None,
                                        n_frames=len(s_["labels"]))
        r["corpus"] = "URFD"
        rows.append(r)
    return rows


def gt_box_area_px(site_dir):
    """Median annotated person area, px^2 -- the ODD statement's evidence."""
    import xml.etree.ElementTree as _ET
    a = []
    for d in sorted(x for x in site_dir.iterdir() if (x / "gt.xml").exists()):
        for fr in _ET.parse(d / "gt.xml").getroot().iter("frame"):
            for o in fr.iter("object"):
                b = o.find("box")
                if b is None:
                    continue
                try:
                    a.append(float(b.get("w")) * float(b.get("h")))
                except (TypeError, ValueError):
                    pass
    return float(np.median(a)) if a else None


def static_gate(caviar, motion):
    """Protocol V2.1 section 3.  Returns (kept, rejected_rows)."""
    mot = {r["sequence"]: r for r in motion}
    kept, rejected = {}, []
    for key, seq in caviar.items():
        name = f"{seq['site'].replace('CAVIAR-', 'CAVIAR-')}/{seq['video']}"
        r = mot.get(name)
        if r is None:
            rejected.append(dict(sequence=key, reason="camera motion not measured",
                                 median_pct_diag=None))
            continue
        if r["median_pct_diag"] >= CV.STATIC_THRESHOLD_PCT_DIAG:
            rejected.append(dict(sequence=key, reason="fails the static-camera gate",
                                 median_pct_diag=r["median_pct_diag"]))
            continue
        seq["motion_pct"] = r["median_pct_diag"]
        kept[key] = seq
    return kept, rejected


def flicker_rows(chans, setting):
    """Protocol V2.1 section 7.3: events shorter than 0.2 s, and events that hug
    the zone boundary for their whole length."""
    rows = []
    for c in chans:
        if "edge_px" not in c:
            continue
        for e in C.build_events(c["frames"], c["hazard"], c["alarm"], c["fps"],
                                setting["gap_s"], c["corpus"], c["channel"],
                                c["video"], c["zone"]):
            if setting["censored"] == "exclude" and e["censored"]:
                continue
            seg = c["edge_px"][e["i0"]:e["i1"] + 1]
            seg = seg[np.isfinite(seg)]
            maxd = float(seg.max()) if seg.size else float("nan")
            scale = c["zone_scale_px"]
            rows.append(dict(corpus=c["corpus"], channel=c["channel"],
                             D_seconds=e["D_seconds"],
                             short=bool(e["D_seconds"] < 0.2),
                             max_edge_px=maxd, zone_scale_px=scale,
                             edge_flicker=bool(np.isfinite(maxd)
                                               and maxd < 0.05 * scale)))
    return rows


def main():
    freeze = C.check_protocol()
    self_test()
    rng = np.random.default_rng(C.SEED)
    print("protocol V2.1 frozen", freeze["frozen_at_utc"], freeze["sha256"][:16],
          flush=True)

    motion = json.loads((RESULTS / "camera_motion_v2_1.json").read_text(encoding="utf-8"))
    mot = C.load_mot17()
    urfd = C.load_urfd()
    caviar_all = CV.load_caviar(motion)
    caviar_static, rejected = static_gate(caviar_all, motion)
    write_csv(RESULTS / "static_gate_v2_1.csv", rejected)
    caviar = caviar_static          # Amendment 2': no site is excluded
    vp_rows = aspect_rows(caviar)
    write_csv(RESULTS / "site_aspect_v2_1.csv", vp_rows)
    for r in vp_rows:
        print(f"  site aspect (descriptive only): {r['site']} median GT h/w = "
              f"{r['median_aspect']:.2f} over {r['n_boxes']} boxes", flush=True)
    vp_numbers = {f"aspect_{r['site']}": r["median_aspect"] for r in vp_rows}
    print(f"corpora: CAVIAR {len(caviar)} primary / {len(caviar_all)} scored, "
          f"URFD {len(urfd)}, MOT17Det {len(mot)}", flush=True)

    N = dict(vp_numbers)
    N["protocol_sha256"] = freeze["sha256"]
    N["protocol_frozen_at"] = freeze["frozen_at_utc"]
    N["protocol_supersedes_sha256"] = freeze["supersedes"]["sha256"]
    N["seed"] = C.SEED
    N["bootstrap_reps"] = C.BOOT
    N["gap_merge_s"] = C.PRIMARY["gap_s"]
    N["static_threshold_pct_diag"] = CV.STATIC_THRESHOLD_PCT_DIAG
    N["n_caviar_sequences"] = len(caviar)
    N["n_caviar_rejected"] = len(rejected)
    N["caviar_fps"] = CV.FPS
    for site in ("CAVIAR-INRIA", "CAVIAR-LISBON"):
        seqs = [s for s in caviar.values() if s["site"] == site]
        N[f"n_seq_{site}"] = len(seqs)
        if seqs:
            N[f"motion_max_{site}"] = max(s["motion_pct"] for s in seqs)
    N["n_zones"] = 3
    N["n_channels_primary"] = sum(
        len(CV.ZONES_SITE[s["site"]]) for s in caviar.values())
    N["mot17_static_sequences"] = list(C.MOT17_STATIC)
    N["mot17_moving_excluded"] = [k for k in mot if k not in C.MOT17_STATIC]
    for k in mot:
        r = next((x for x in motion if x["sequence"] == f"MOT17Det/{k}"), None)
        if r:
            N[f"motion_{k}"] = r["median_pct_diag"]

    # ---------------- PRIMARY: the static CAVIAR sites
    chans = C.build_channels(mot, urfd, C.PRIMARY, caviar=caviar, scope="primary")
    res = C.analyse(chans, C.PRIMARY, rng, full=True)
    print(f"primary: {res['n_events']} uncensored events "
          f"({res['n_events_censored']} censored dropped) over "
          f"{len(chans)} channels", flush=True)

    write_csv(RESULTS / "events_v2.csv", res["events"],
              ["corpus", "channel", "video", "zone", "event_id", "start_frame",
               "end_frame", "n_frames", "fps", "D_seconds", "censored", "n_alarm"])
    write_csv(RESULTS / "miss_validation_v2.csv", res["miss_rows"])
    write_csv(RESULTS / "far_latency_v2.csv", res["fa_rows"])
    write_csv(RESULTS / "latency_v2.csv", res["latency_rows"])
    write_csv(RESULTS / "bridge_v2.csv", res["bridge_rows"])
    write_csv(RESULTS / "p_beta_v2.csv",
              [dict(corpus=k, **v) for k, v in res["p"].items() if v])
    write_csv(RESULTS / "beta_lag_curve_v2.csv",
              [dict(corpus=k, **r) for k, curve in res["beta_curve"].items()
               for r in curve])
    # The duration law needs only the ground truth, so it is computed on both
    # sites and reported per site as well as pooled (protocol s11, item 1).
    fd = [dict(corpus="pooled", stat=k, seconds=v) for k, v in res.items()
          if isinstance(k, str) and k.startswith("D_")]
    fd.append(dict(corpus="pooled", stat="n_events", seconds=res["n_events"]))
    for corpus in [c for c in res["corpora"] if c != "pooled"]:
        d = np.array([e["D_seconds"] for e in res["events"]
                      if e["corpus"] == corpus])
        if not len(d):
            continue
        tag = corpus.replace("CAVIAR-", "").replace("-", "").lower()
        for q, lab in ((5, "q05"), (25, "q25"), (50, "median"), (75, "q75"),
                       (95, "q95")):
            v = float(np.percentile(d, q))
            fd.append(dict(corpus=corpus, stat=f"D_{lab}", seconds=v))
            N[f"D_{lab}_{tag}_seconds"] = v
        for lab, v in (("D_mean", float(d.mean())), ("D_min", float(d.min())),
                       ("D_max", float(d.max()))):
            fd.append(dict(corpus=corpus, stat=lab, seconds=v))
            N[f"{lab}_{tag}_seconds"] = v
        fd.append(dict(corpus=corpus, stat="n_events", seconds=len(d)))
        N[f"n_events_{tag}"] = int(len(d))
    write_csv(RESULTS / "fd_summary_v2.csv", fd,
              ["corpus", "stat", "seconds"])

    # cluster counts, printed beside every interval (protocol 7.1)
    clusters = defaultdict(set)
    for c in chans:
        clusters[c["corpus"]].add(c["video"])
        clusters["pooled"].add(c["video"])
    write_csv(RESULTS / "clusters_v2_1.csv",
              [dict(corpus=k, n_clusters=len(v),
                    indicative_only=bool(len(v) < 10))
               for k, v in sorted(clusters.items())])
    for k, v in clusters.items():
        N[f"n_clusters_{k}"] = len(v)

    # ---------------- flicker diagnostics (protocol 7.3)
    fl = flicker_rows(chans, C.PRIMARY)
    write_csv(RESULTS / "flicker_v2_1.csv", fl)
    if fl:
        N["n_events_short"] = sum(1 for r in fl if r["short"])
        N["pct_events_short"] = 100.0 * N["n_events_short"] / len(fl)
        N["n_events_edge_flicker"] = sum(1 for r in fl if r["edge_flicker"])
        N["pct_events_edge_flicker"] = 100.0 * N["n_events_edge_flicker"] / len(fl)

    # ---------------- CONTRAST: URFD on the include-censored axis
    urfd_setting = dict(C.PRIMARY, censored="include")
    uch = C.build_channels(mot, urfd, urfd_setting, scope="contrast")
    ures = C.analyse(uch, urfd_setting, rng, full=True)
    rows = []
    for r in ures["miss_rows"]:
        if r["corpus"] != "pooled":
            continue
        rows.append(dict(kind="all", **r))
    for kind in ("fall", "adl"):
        sub = [c for c in uch if c["zone"] == kind]
        if not sub:
            continue
        sres = C.analyse(sub, urfd_setting, rng, light=True)
        for r in sres["miss_rows"]:
            if r["corpus"] == "pooled":
                rows.append(dict(kind=kind, **r))
    write_csv(RESULTS / "urfd_contrast_v2_1.csv", rows)
    N["n_events_urfd_include"] = ures["n_events"]
    pu = ures["p"].get("pooled")
    if pu:
        N["p_hat_urfd_include"] = pu["p_hat"]
    for r in ures["bridge_rows"]:
        if r["corpus"] == "pooled" and abs(r["T_seconds"] - 2.0) < 1e-9:
            N["urfd_M_T2"] = r["M_K"]
            N["urfd_band_T2"] = r["band"]

    # ---------------- STRATUM: the three static MOT17Det sequences
    sch = C.build_channels(mot, urfd, C.PRIMARY, scope="stratum")
    sres = C.analyse(sch, C.PRIMARY, rng, light=True)
    write_csv(RESULTS / "mot17_static_v2_1.csv", sres["miss_rows"])
    N["n_events_mot17_static"] = sres["n_events"]

    # ---------------- Amendment 2': the detector audit, for EVERY corpus
    dq = detector_audit(caviar, mot, urfd, C.PRIMARY["score"])
    write_csv(RESULTS / "detector_quality_v2_1.csv", dq,
              ["corpus", "site", "video", "n_frames", "n_gt", "n_det", "recall",
               "precision", "top_cell_x", "top_cell_y", "top_cell_n",
               "top_cell_share", "top_cell_frame_share", "top_cluster_share",
               "top_cluster_frame_share", "cluster_match_rate",
               "persistent_cluster", "static_fp", "top_cell_zone"])
    N["gt_match_iou"] = CV.GT_MATCH_IOU
    N["audit_grid"] = [CV.GRID_X, CV.GRID_Y]
    for corpus in sorted({r["corpus"] for r in dq}):
        sub = [r for r in dq if r["corpus"] == corpus]
        tag = corpus.replace("CAVIAR-", "").replace("MOT17Det-", "mot17")                     .replace("-", "").lower()
        for field in ("recall", "precision", "top_cell_share",
                      "top_cell_frame_share", "top_cluster_share",
                      "top_cluster_frame_share"):
            v = [r[field] for r in sub if np.isfinite(r[field])]
            if not v:
                continue
            N[f"{field}_min_{tag}"] = float(min(v))
            N[f"{field}_max_{tag}"] = float(max(v))
            N[f"{field}_median_{tag}"] = float(np.median(v))
        N[f"n_audit_sequences_{tag}"] = len(sub)
        N[f"n_persistent_cluster_{tag}"] = sum(
            1 for r in sub if r["persistent_cluster"])
        N[f"n_static_fp_{tag}"] = sum(1 for r in sub if r["static_fp"])
        inz = [r for r in sub if r["static_fp"]
               and r["top_cell_zone"] not in ("", "none")]
        N[f"n_static_fp_in_zone_{tag}"] = len(inz)
        N[f"static_fp_zones_{tag}"] = sorted({r["top_cell_zone"] for r in inz})
        pinz = [r for r in sub if r["persistent_cluster"]
                and r["top_cell_zone"] not in ("", "none")]
        N[f"n_persistent_in_zone_{tag}"] = len(pinz)
        r0 = N.get(f"recall_median_{tag}")
        print(f"  audit {corpus}: {len(sub)} sequences, median recall "
              f"{r0 if r0 is None else round(r0, 3)}, max single-cell share "
              f"{round(N.get('top_cell_share_max_' + tag, float('nan')), 3)} "
              f"(3x3 median {round(N.get('top_cluster_share_median_' + tag, float('nan')), 3)}), "
              f"persistent cluster in {N[f'n_persistent_cluster_{tag}']}/{len(sub)}"
              f" ({N[f'n_persistent_in_zone_{tag}']} inside a zone), of which "
              f"{N[f'n_static_fp_{tag}']} are false positives "
              f"({N[f'n_static_fp_in_zone_{tag}']} inside a zone "
              f"{N[f'static_fp_zones_{tag}']})", flush=True)

    # the ODD statement's own evidence: how big an annotated person is
    for site in ("INRIA", "LISBON"):
        d = C.DATA / "CAVIAR" / site
        if d.exists():
            a = gt_box_area_px(d)
            if a:
                N[f"gt_area_px_CAVIAR-{site}"] = a

    # ---------------- Amendment 2': the same numbers under the GT-matched alarm
    gm = dict(C.PRIMARY, alarm_mode="gt_matched")
    am_rows = []
    for scope in ("primary", "stratum"):
        ch_gm = C.build_channels(mot, urfd, gm, caviar=caviar, scope=scope)
        r_gm = C.analyse(ch_gm, gm, rng, light=True)
        r_any = (res if scope == "primary"
                 else C.analyse(C.build_channels(mot, urfd, C.PRIMARY,
                                                 caviar=caviar, scope=scope),
                                C.PRIMARY, rng, light=True))
        for corpus in r_gm["corpora"]:
            if corpus == "pooled" and scope != "primary":
                continue          # a stratum's pool is not the primary pool
            row = dict(scope=scope, corpus=corpus)
            for mode, r in (("any_box", r_any), ("gt_matched", r_gm)):
                pr = r["p"].get(corpus)
                row[f"p_hat_{mode}"] = (pr or {}).get("p_hat")
                row[f"n_events_{mode}"] = r["n_events"]
                for T, lab in ((0.5, "Thalf"), (1.0, "T1")):
                    mrow = next((x for x in r["miss_rows"]
                                 if x["corpus"] == corpus
                                 and x["T_seconds"] == T), None)
                    row[f"miss_{lab}_{mode}"] = (mrow or {}).get("miss_measured")
                    fa = next((x for x in r["fa_rows"] if x["corpus"] == corpus
                               and x["T_seconds"] == T), None)
                    row[f"alarms_per_hour_{lab}_{mode}"] = (
                        fa or {}).get("alarms_per_hour")
                fa1 = next((x for x in r["fa_rows"] if x["corpus"] == corpus
                            and x["T_seconds"] == 1.0), None)
                row[f"fa_frame_rate_{mode}"] = (fa1 or {}).get("fa_frame_rate")
            am_rows.append(row)
    # URFD carries no box annotation, so the GT-matched alarm is undefined there
    am_rows.append(dict(scope="contrast", corpus="URFD",
                        p_hat_any_box=N.get("p_hat_urfd_include"),
                        note="no box annotation: gt_matched undefined"))
    write_csv(RESULTS / "alarm_mode_v2_1.csv", am_rows,
              ["scope", "corpus", "p_hat_any_box", "p_hat_gt_matched",
               "n_events_any_box", "n_events_gt_matched",
               "miss_Thalf_any_box", "miss_Thalf_gt_matched",
               "miss_T1_any_box", "miss_T1_gt_matched",
               "alarms_per_hour_Thalf_any_box",
               "alarms_per_hour_Thalf_gt_matched",
               "alarms_per_hour_T1_any_box", "alarms_per_hour_T1_gt_matched",
               "fa_frame_rate_any_box", "fa_frame_rate_gt_matched", "note"])
    for r in am_rows:
        if r.get("p_hat_gt_matched") is None:
            continue
        tag = r["corpus"].replace("CAVIAR-", "").replace("MOT17Det-", "mot17")                          .replace("-", "").lower()
        N[f"p_hat_{tag}_gtmatched"] = r["p_hat_gt_matched"]
        N[f"miss_T1p0_{tag}_gtmatched"] = r["miss_T1_gt_matched"]
        print(f"  alarm mode {r['corpus']}: p_hat {r['p_hat_any_box']:.3f} "
              f"(any_box) vs {r['p_hat_gt_matched']:.3f} (gt_matched)", flush=True)

    # ---------------- cross-site prediction, within the primary
    xrows = []
    sites = sorted({c["corpus"] for c in chans})
    for fit_on in sites:
        for predict_on in sites:
            if fit_on == predict_on:
                continue
            pr = res["p"].get(fit_on)
            tgt = [r for r in res["miss_rows"] if r["corpus"] == predict_on]
            if not pr or not tgt:
                continue
            curve = res["beta_curve"].get(fit_on) or []
            for r in tgt:
                T = r["T_seconds"]
                preds = []
                for e in res["events"]:
                    if e["corpus"] != predict_on:
                        continue
                    K = max(1, int(round(T * e["fps"])))
                    b = 0.0
                    if curve:
                        bv = curve[min(max(K, 1), 30) - 1]["beta_hat"]
                        b = float(np.clip(bv, 0.0, 1.0)) if np.isfinite(bv) else 0.0
                    preds.append(float(M.p_miss_exact(e["n_frames"], K,
                                                      pr["p_hat"], b)))
                if not preds:
                    continue
                xrows.append(dict(fit_on=fit_on, predict_on=predict_on,
                                  T_seconds=T, p_fit=pr["p_hat"],
                                  n_events=len(preds),
                                  miss_measured=r["miss_measured"],
                                  miss_lo=r["miss_lo"], miss_hi=r["miss_hi"],
                                  miss_predicted=float(np.mean(preds)),
                                  inside_ci=bool(r["miss_lo"] <= np.mean(preds)
                                                 <= r["miss_hi"])))
    write_csv(RESULTS / "cross_corpus_v2.csv", xrows)
    if xrows:
        N["xcorpus_n"] = len(xrows)
        N["xcorpus_inside"] = sum(1 for r in xrows if r["inside_ci"])

    # ---------------- sensitivity (point estimates only)
    sens = []
    for axis, values in C.SENS.items():
        if axis in ("aspect", "urfd_labels", "visibility"):
            continue          # those axes belong to the contrast/stratum corpora
        for v in values:
            s = dict(C.PRIMARY)
            s[axis] = v
            rebuild = axis in ("score", "appearance")
            ch = (C.build_channels(mot, urfd, s, caviar=caviar, scope="primary")
                  if rebuild else chans)
            r = C.analyse(ch, s, rng, light=True)
            for T in (0.5, 1.0):
                row = next((x for x in r["bridge_rows"]
                            if x["T_seconds"] == T and x["corpus"] == "pooled"), None)
                mrow = next((x for x in r["miss_rows"]
                             if x["T_seconds"] == T and x["corpus"] == "pooled"), None)
                if not row:
                    continue
                sens.append(dict(axis=axis, value=str(v), T_seconds=T,
                                 is_primary=(v == C.PRIMARY[axis]),
                                 n_events=r["n_events"],
                                 p_hat=(r["p"]["pooled"] or {}).get("p_hat"),
                                 M_K=row["M_K"], band=row["band"],
                                 miss_measured=(mrow or {}).get("miss_measured"),
                                 miss_model=(mrow or {}).get("miss_model_beta")))
            print(f"  sens {axis}={v}: {r['n_events']} events", flush=True)
    write_csv(RESULTS / "sensitivity_v2.csv", sens)

    # ---------------- numbers
    for corpus in res["corpora"]:
        pr = res["p"].get(corpus)
        if pr:
            tag = corpus.replace("CAVIAR-", "").replace("-", "").lower()
            N[f"p_hat_{tag}"] = pr["p_hat"]
            N[f"p_hat_{tag}_lo"] = pr["boot_lo"]
            N[f"p_hat_{tag}_hi"] = pr["boot_hi"]
            N[f"n_active_frames_{tag}"] = pr["n_active_frames"]
    N["n_events_primary"] = res["n_events"]
    N["n_events_censored"] = res["n_events_censored"]
    for k in ("D_q05", "D_q25", "D_median", "D_q75", "D_q95", "D_mean", "D_max"):
        if k in res:
            N[k + "_seconds"] = res[k]
    for r in res["miss_rows"]:
        if r["corpus"] == "pooled":
            t = str(r["T_seconds"]).replace(".", "p")
            N[f"miss_measured_T{t}"] = r["miss_measured"]
            N[f"miss_model_T{t}"] = r["miss_model_beta"]
            N[f"miss_model0_T{t}"] = r["miss_model_beta0"]
            N[f"miss_lo_T{t}"] = r["miss_lo"]
            N[f"miss_hi_T{t}"] = r["miss_hi"]
    for r in res["bridge_rows"]:
        if r["corpus"] == "pooled":
            t = str(r["T_seconds"]).replace(".", "p")
            N[f"M_T{t}"] = r["M_K"]
            N[f"M_T{t}_band"] = r["band"]
            N[f"gain_staggered_T{t}"] = r["gain_staggered"]
            N[f"gain_independent_T{t}"] = r["gain_independent"]
    mc = json.load(open(RESULTS / "model_mc_validation.json", encoding="utf-8"))
    N["mc_cells"] = mc["n_cells"]
    N["mc_events"] = mc["n_events"]
    N["mc_max_abs_err"] = mc["max_abs_err"]
    N["mc_n_fail"] = mc["n_fail"]
    det = json.load(open(RESULTS / "detector_manifest.json", encoding="utf-8"))
    N["detector"] = det["architecture"]
    N["detector_weights_sha256"] = det["weights_sha256"]
    N["torch_version"] = det["torch"]
    N["torchvision_version"] = det["torchvision"]

    json.dump(N, open(RESULTS / "numbers_v2.json", "w"), indent=1, default=str)
    print("wrote numbers_v2.json with", len(N), "keys")
    print("CASE_STUDY_V2_1_DONE")


if __name__ == "__main__":
    main()
