"""camera_motion_check.py -- Topic 35 / V2.1, VIEC 2b.1.

Measures how much the *camera* moves in each sequence, independently of what the
benchmark's documentation claims, so that "static" is a number in this package
and not a citation.

Method: sample frame pairs at a fixed stride, convert to greyscale, and estimate
the global translation between them with phase correlation (cv2.phaseCorrelate),
which is a whole-image frequency-domain estimator and is therefore driven by the
background rather than by the people walking across it.  Report the median and
the 90th percentile of the per-pair shift magnitude, in pixels, normalised by the
image diagonal so sequences of different resolution compare.

This is evidence for a protocol decision, not a result: it is run on the
candidate corpora *and* on the sequences already processed, and the numbers go
into CORPUS_SCREEN_V2_1.md.
"""
from __future__ import annotations

import argparse
import configparser
import json
import pathlib
import tarfile

import cv2
import numpy as np

EVAL = pathlib.Path(__file__).resolve().parents[1]
DATA = EVAL / "data"
RESULTS = EVAL / "results"
STRIDE = 5          # frames between the two members of a pair
MAX_PAIRS = 60      # per sequence; enough for a stable median, cheap to run


def _shift(a, b):
    ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float32)
    win = cv2.createHanningWindow(ga.shape[::-1], cv2.CV_32F)
    (dx, dy), _resp = cv2.phaseCorrelate(ga * win, gb * win)
    return float(np.hypot(dx, dy))


def _summarise(name, shifts, diag, extra=None):
    s = np.asarray(shifts, dtype=float)
    out = dict(sequence=name, n_pairs=int(s.size), stride=STRIDE,
               diag_px=round(diag, 1),
               median_px=float(np.median(s)) if s.size else float("nan"),
               p90_px=float(np.percentile(s, 90)) if s.size else float("nan"))
    out["median_pct_diag"] = 100.0 * out["median_px"] / diag
    out["p90_pct_diag"] = 100.0 * out["p90_px"] / diag
    if extra:
        out.update(extra)
    return out


def scan_mot17():
    root = DATA / "MOT17Det" / "train"
    if not root.exists():
        return []
    rows = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        cp = configparser.ConfigParser()
        cp.read(d / "seqinfo.ini")
        imgs = sorted((d / "img1").glob("*.jpg"))
        if len(imgs) <= STRIDE:
            continue
        idx = np.linspace(0, len(imgs) - 1 - STRIDE,
                          min(MAX_PAIRS, len(imgs) - STRIDE)).astype(int)
        shifts = []
        for i in idx:
            a = cv2.imread(str(imgs[i]))
            b = cv2.imread(str(imgs[i + STRIDE]))
            if a is None or b is None:
                continue
            shifts.append(_shift(a, b))
        diag = float(np.hypot(int(cp["Sequence"]["imWidth"]),
                              int(cp["Sequence"]["imHeight"])))
        rows.append(_summarise(f"MOT17Det/{d.name}", shifts, diag,
                               dict(corpus="MOT17Det")))
        print("  ", rows[-1]["sequence"], f"{rows[-1]['median_pct_diag']:.3f} %",
              flush=True)
    return rows


def _frames_from_tar(tgz, limit_pairs=MAX_PAIRS, stride=STRIDE):
    """Yield (a, b) frame pairs from a CAVIAR *_jpg.tar.gz without unpacking."""
    with tarfile.open(tgz, "r:gz") as tf:
        names = sorted(m.name for m in tf.getmembers()
                       if m.isfile() and m.name.lower().endswith((".jpg", ".jpeg")))
        if len(names) <= stride:
            return
        idx = np.linspace(0, len(names) - 1 - stride,
                          min(limit_pairs, len(names) - stride)).astype(int)
        want = sorted(set(idx.tolist()) | set((idx + stride).tolist()))
        cache = {}
        for i in want:
            f = tf.extractfile(names[i])
            if f is None:
                continue
            buf = np.frombuffer(f.read(), dtype=np.uint8)
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if img is not None:
                cache[i] = img
        for i in idx:
            if i in cache and i + stride in cache:
                yield cache[i], cache[i + stride]


def scan_caviar():
    rows = []
    for site in ("INRIA", "LISBON"):
        root = DATA / "CAVIAR" / site
        if not root.exists():
            continue
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            tgz = d / "frames.tar.gz"
            if not tgz.exists() or tgz.stat().st_size < 1000:
                continue
            shifts, diag = [], None
            try:
                for a, b in _frames_from_tar(tgz):
                    if diag is None:
                        diag = float(np.hypot(a.shape[1], a.shape[0]))
                    shifts.append(_shift(a, b))
            except Exception as exc:                      # noqa: BLE001
                print("   !", d.name, exc, flush=True)
                continue
            if not shifts:
                continue
            rows.append(_summarise(f"CAVIAR-{site}/{d.name}", shifts, diag,
                                   dict(corpus=f"CAVIAR-{site}")))
            print("  ", rows[-1]["sequence"], f"{rows[-1]['median_pct_diag']:.3f} %",
                  flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["mot17", "caviar"])
    a = ap.parse_args()
    rows = []
    if a.only in (None, "mot17"):
        print("MOT17Det:")
        rows += scan_mot17()
    if a.only in (None, "caviar"):
        print("CAVIAR:")
        rows += scan_caviar()
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "camera_motion_v2_1.json"
    old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    byname = {r["sequence"]: r for r in old}
    byname.update({r["sequence"]: r for r in rows})
    out.write_text(json.dumps(sorted(byname.values(), key=lambda r: r["sequence"]),
                              indent=1), encoding="utf-8")
    print("wrote", out, f"({len(byname)} sequences)")


if __name__ == "__main__":
    main()
