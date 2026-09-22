"""caviar_v2_1.py -- CAVIAR loading and the V2.1 zone geometry.

Kept separate from case_study_v2.py so that the estimators tested in V2 are not
disturbed by the corpus change.  Everything here is transcribed from
EVAL_PROTOCOL_V2_1.md sections 2-4.
"""
from __future__ import annotations

import pathlib
import xml.etree.ElementTree as ET

import numpy as np

EVAL = pathlib.Path(__file__).resolve().parents[1]
DATA = EVAL / "data"
RESULTS = EVAL / "results"
CACHE = RESULTS / "det_cache"

FPS = 25.0          # published for both sites
W, H = 384.0, 288.0  # half-resolution PAL, published for both sites

# Protocol section 4.2.  One zone set per CAMERA, fixed from frame 0 of the site
# before any ground truth, detector output or event count was consulted.
ZONES_SITE = {
    "CAVIAR-INRIA": {
        "Z1": [(0.00, 0.70), (0.40, 0.68), (0.48, 1.00), (0.00, 1.00)],
        "Z2": [(0.30, 0.30), (0.75, 0.30), (0.80, 0.70), (0.32, 0.70)],
        "Z3": [(0.55, 0.72), (0.95, 0.62), (1.00, 1.00), (0.58, 1.00)],
    },
    "CAVIAR-LISBON": {
        "Z1": [(0.15, 1.00), (0.38, 1.00), (0.30, 0.42), (0.19, 0.42)],
        "Z2": [(0.38, 1.00), (0.70, 1.00), (0.45, 0.40), (0.32, 0.40)],
        "Z3": [(0.70, 1.00), (0.95, 0.92), (0.62, 0.42), (0.47, 0.42)],
    },
}

# Protocol section 3: a sequence is static if the median global frame-to-frame
# shift is below this fraction of the image diagonal, at a stride of 5 frames.
STATIC_THRESHOLD_PCT_DIAG = 0.1

# Protocol section 11 (Amendment 2'): there is NO viewpoint gate.  An earlier
# amendment excluded a site whose median annotation aspect h/w was below 1; its
# evidence turned out to compare annotated people against a static false
# positive, so it excluded a site because the detector fails there.  Withdrawn.
# site_aspect() below survives as a descriptive statistic and gates nothing.


def site_aspect(site_dir):
    """Median ground-truth box aspect h/w over every annotated box of a site."""
    import xml.etree.ElementTree as _ET
    w, h = [], []
    for d in sorted(p for p in site_dir.iterdir() if (p / "gt.xml").exists()):
        for fr in _ET.parse(d / "gt.xml").getroot().iter("frame"):
            for o in fr.iter("object"):
                b = o.find("box")
                if b is None:
                    continue
                try:
                    w.append(float(b.get("w")))
                    h.append(float(b.get("h")))
                except (TypeError, ValueError):
                    continue
    if not w:
        return None, 0
    a = np.asarray(h) / np.asarray(w)
    return float(np.median(a)), len(a)


def parse_cvml(path):
    """-> dict frame_number -> list of (foot_x, foot_y, appearance, box_px).

    foot_x / foot_y are normalised; box_px is (x1, y1, x2, y2) in pixels, which
    the GT-matched alarm mode of the protocol needs for an IoU test.
    """
    out = {}
    root = ET.parse(path).getroot()
    for fr in root.iter("frame"):
        try:
            n = int(fr.get("number"))
        except (TypeError, ValueError):
            continue
        people = []
        for obj in fr.iter("object"):
            box = obj.find("box")
            if box is None:
                continue
            try:
                xc = float(box.get("xc")); yc = float(box.get("yc"))
                w = float(box.get("w")); h = float(box.get("h"))
            except (TypeError, ValueError):
                continue
            app = (obj.findtext("appearance") or "").strip().lower()
            people.append((xc / W, (yc + h / 2.0) / H, app,
                           (xc - w / 2.0, yc - h / 2.0, xc + w / 2.0, yc + h / 2.0)))
        out[n] = people
    return out


def iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    ua = ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)
    return inter / ua if ua > 0 else 0.0


GT_MATCH_IOU = 0.3


def static_ok(name, motion):
    """motion: the list written by camera_motion_check.py."""
    for r in motion:
        if r["sequence"].endswith("/" + name.split("__")[-1]) and \
           r["sequence"].split("/")[0] == name.split("__")[0]:
            return r["median_pct_diag"] < STATIC_THRESHOLD_PCT_DIAG, r["median_pct_diag"]
    return None, None            # not measured


def load_caviar(motion=None):
    """-> dict seq_key -> dict(site, fps, labels, det_*, motion_pct)."""
    out = {}
    root = DATA / "CAVIAR"
    if not root.exists():
        return out
    mot = {r["sequence"]: r for r in (motion or [])}
    for site in ("INRIA", "LISBON"):
        sroot = root / site
        if not sroot.exists():
            continue
        for d in sorted(p for p in sroot.iterdir() if p.is_dir()):
            key = f"CAVIAR-{site}__{d.name}"
            cache_f = CACHE / f"{key}.npz"
            if not cache_f.exists() or not (d / "gt.xml").exists():
                continue
            m = mot.get(f"CAVIAR-{site}/{d.name}")
            cache = np.load(cache_f)
            out[key] = dict(site=f"CAVIAR-{site}", video=d.name, fps=FPS,
                            labels=parse_cvml(d / "gt.xml"),
                            det_frame=cache["frame"], det_box=cache["box"],
                            det_score=cache["score"],
                            motion_pct=(m or {}).get("median_pct_diag"))
    return out


def _poly_px(poly):
    return np.array([[x * W, y * H] for x, y in poly], dtype=np.float32)


def point_in_poly(x, y, poly):
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


def edge_distance_px(x, y, poly):
    """Unsigned distance from a normalised point to the polygon boundary, px."""
    import cv2
    return abs(float(cv2.pointPolygonTest(_poly_px(poly), (x * W, y * H), True)))


def zone_scale_px(poly):
    """sqrt(area) of the zone in pixels -- the yardstick the flicker diagnostic
    normalises by (protocol section 7.3)."""
    import cv2
    return float(np.sqrt(max(cv2.contourArea(_poly_px(poly)), 1.0)))


def caviar_series(seq, zone, score, appearance="all", alarm_mode="any_box"):
    """(frames, hazard, alarm, edge_dist) for one (sequence, zone) channel.

    alarm_mode (protocol Amendment 2'):
      any_box     -- as originally frozen: any detected person box whose foot
                     point lies in the zone raises the alarm.
      gt_matched  -- the same, but the detection must also match an annotated
                     person at IoU >= 0.3.  A static false positive standing in
                     a zone would otherwise 'detect' every event there and
                     inflate the per-invocation detection probability.
    """
    poly = ZONES_SITE[seq["site"]][zone]
    frames = np.array(sorted(seq["labels"].keys()), dtype=int)
    if not len(frames):
        z = np.zeros(0, bool)
        return frames, z, z, np.zeros(0)
    hazard = np.zeros(len(frames), bool)
    edge = np.full(len(frames), np.inf)
    for i, f in enumerate(frames):
        best = np.inf
        for fx, fy, app, _bx in seq["labels"][f]:
            if appearance == "exclude_occluded" and app == "occluded":
                continue
            if point_in_poly(fx, fy, poly):
                hazard[i] = True
                best = min(best, edge_distance_px(fx, fy, poly))
        edge[i] = best
    fire = set()
    ds = seq["det_score"]
    if len(ds):
        keep = ds >= score
        b = seq["det_box"][keep]
        fr = seq["det_frame"][keep]
        fx = ((b[:, 0] + b[:, 2]) / 2.0) / W
        fy = b[:, 3] / H
        for f_, X, Y, box in zip(fr, fx, fy, b):
            if not point_in_poly(float(X), float(Y), poly):
                continue
            if alarm_mode == "gt_matched":
                gts = seq["labels"].get(int(f_), [])
                if not any(iou(box, g[3]) >= GT_MATCH_IOU for g in gts):
                    continue
            fire.add(int(f_))
    alarm = np.array([f in fire for f in frames], dtype=bool)
    return frames, hazard, alarm, edge


# The static-false-positive audit of Amendment 2' divides the image into this
# many cells, which is exactly 10 x 10 px at CAVIAR's 384 x 288 -- the same
# fraction of the frame at every resolution, so the corpora are comparable.
GRID_X, GRID_Y = 38, 28


def detector_quality_generic(boxes_by_frame, det_frame, det_box, det_score,
                             score, W_, H_, label="", zones=None, n_frames=None):
    """Recall and precision of the detector against a box annotation, and the
    static-false-positive audit the protocol requires.

    boxes_by_frame may be empty, which is the honest answer for a corpus
    annotated with per-frame classes and no boxes: recall and precision then
    come back as NaN and only the concentration statistics are defined.

    The concentration statistics are two, because they answer different
    questions.  `top_cell_share` is the share of all detections that land in the
    most frequent cell; `top_cell_frame_share` is the share of evaluated FRAMES
    in which something lands there, which is the protocol's test for a
    stationary false positive (a cell that repeats in more than half the
    frames).  `top_cell_zone` then says whether that cell sits inside a danger
    zone -- the thing that decides whether such a detection can raise alarms.
    """
    import collections
    m = np.asarray(det_score) >= score
    fr = np.asarray(det_frame)[m]
    bx = np.asarray(det_box)[m]
    ngt = matched = ndet = dmatched = 0
    cells = collections.Counter()
    cell_frames = collections.defaultdict(set)
    byf = collections.defaultdict(list)
    for f, b in zip(fr, bx):
        byf[int(f)].append(b)
    for f, gts in boxes_by_frame.items():
        ds = byf.get(int(f), [])
        for g in gts:
            ngt += 1
            if any(iou(g, d) >= GT_MATCH_IOU for d in ds):
                matched += 1
    cw, ch = W_ / GRID_X, H_ / GRID_Y
    for f, ds in byf.items():
        gts = boxes_by_frame.get(int(f), []) if boxes_by_frame else None
        for d in ds:
            ndet += 1
            if gts is not None and any(iou(g, d) >= GT_MATCH_IOU for g in gts):
                dmatched += 1
            key = (int((d[0] + d[2]) / 2.0 / cw), int(d[3] / ch))
            cells[key] += 1
            cell_frames[key].add(int(f))
    top_cell, top_n = (cells.most_common(1) or [((None, None), 0)])[0]
    nan = float("nan")
    n_eval = n_frames or len(set(byf) | set(boxes_by_frame)) or 0
    # The 3 x 3 neighbourhood of the modal cell.  A stationary false positive
    # does not sit in exactly one cell: the box jitters by a few pixels, so the
    # single-cell share understates it.  The cluster share is the statistic the
    # audit's "> 90 % of detections are one static object" rests on, and it is
    # the one to read; the single-cell share is kept beside it as the stricter
    # figure.
    nb = [k for k in cells
          if top_cell[0] is not None
          and abs(k[0] - top_cell[0]) <= 1 and abs(k[1] - top_cell[1]) <= 1]
    nbs = set(nb)
    cluster_n = sum(cells[k] for k in nb)
    cluster_frames = set().union(*[cell_frames[k] for k in nb]) if nb else set()
    # Persistence alone does not say whether the cluster is a false positive or
    # a person who simply stands still: MOT17Det contains both.  The IoU match
    # is what separates them, so it is measured rather than assumed.
    cl_match = cl_tot = 0
    if boxes_by_frame and nbs:
        for f, ds in byf.items():
            gts = boxes_by_frame.get(int(f), [])
            for d in ds:
                if (int((d[0] + d[2]) / 2.0 / cw), int(d[3] / ch)) not in nbs:
                    continue
                cl_tot += 1
                if any(iou(g, d) >= GT_MATCH_IOU for g in gts):
                    cl_match += 1
    zone_hit = ""
    if top_cell[0] is not None and zones:
        # the cell's representative foot point, in normalised coordinates
        x = (top_cell[0] + 0.5) * cw / W_
        y = (top_cell[1] + 0.5) * ch / H_
        hits = [z for z, poly in zones.items() if point_in_poly(x, y, poly)]
        zone_hit = "+".join(sorted(hits)) if hits else "none"
    frame_share = (len(cell_frames.get(top_cell, ())) / n_eval) if n_eval else nan
    cl_frame_share = (len(cluster_frames) / n_eval) if n_eval else nan
    cl_match_rate = (cl_match / cl_tot) if cl_tot else nan
    persistent = bool(np.isfinite(cl_frame_share) and cl_frame_share > 0.5)
    # A stationary FALSE positive: persistent, and mostly not a person the
    # annotation knows about.  Undefined without a box annotation.
    static_fp = bool(persistent and np.isfinite(cl_match_rate)
                     and cl_match_rate < 0.5)
    return dict(video=label, n_gt=ngt, n_det=ndet, n_frames=n_eval,
                recall=(matched / ngt if ngt else nan),
                precision=(dmatched / ndet if (ndet and boxes_by_frame) else nan),
                top_cell_x=top_cell[0], top_cell_y=top_cell[1], top_cell_n=top_n,
                top_cell_share=(top_n / ndet if ndet else nan),
                top_cell_frame_share=frame_share,
                top_cluster_share=(cluster_n / ndet if ndet else nan),
                top_cluster_frame_share=cl_frame_share,
                cluster_match_rate=cl_match_rate,
                persistent_cluster=persistent,
                static_fp=(static_fp if boxes_by_frame else None),
                top_cell_zone=zone_hit)


def detector_quality(seq, score=0.5):
    """The audit for a CAVIAR sequence.  Reported for every corpus, not only
    the one under suspicion (protocol section 11, Amendment 2')."""
    boxes = {int(f): [g[3] for g in people]
             for f, people in seq["labels"].items()}
    r = detector_quality_generic(boxes, seq["det_frame"], seq["det_box"],
                                 seq["det_score"], score, W, H, seq["video"],
                                 zones=ZONES_SITE[seq["site"]],
                                 n_frames=len(seq["labels"]))
    r["site"] = seq["site"]
    return r
