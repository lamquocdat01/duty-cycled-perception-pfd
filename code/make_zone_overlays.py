"""make_zone_overlays.py -- Topic 35 / V2.1.

Renders the frozen danger zones of EVAL_PROTOCOL_V2_1.md section 4.2 over frame 0
of each site, so a reader can see what was actually fixed and judge it, rather
than reading four polygons in a table.  Goes to the supplementary.

The zones were defined by looking at these frames and nothing else -- no ground
truth, no detector output, no event count -- and this script only draws them.
"""
from __future__ import annotations

import pathlib
import tarfile

import cv2
import numpy as np

import caviar_v2_1 as CV

EVAL = pathlib.Path(__file__).resolve().parents[1]
DATA = EVAL / "data"
FIGS = EVAL.parent / "02_Manuscript" / "figs"

# Okabe-Ito, the same fixed order the figures use, in BGR for OpenCV.
COL = {"Z1": (178, 114, 0), "Z2": (0, 94, 213), "Z3": (115, 158, 0)}
READING = {
    "CAVIAR-INRIA": {"Z1": "entrance apron", "Z2": "central walkway",
                     "Z3": "floor beside the column"},
    "CAVIAR-LISBON": {"Z1": "shop-front strip", "Z2": "corridor centre",
                      "Z3": "balustrade side"},
}


def first_frame(tgz):
    with tarfile.open(tgz, "r:gz") as tf:
        names = sorted(m.name for m in tf.getmembers()
                       if m.isfile() and m.name.lower().endswith((".jpg", ".jpeg")))
        if not names:
            return None
        buf = np.frombuffer(tf.extractfile(names[0]).read(), np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def draw(site, img, out):
    H, W = img.shape[:2]
    zones = CV.ZONES_SITE[site]
    ov = img.copy()
    for k, poly in zones.items():
        pts = np.array([[int(x * W), int(y * H)] for x, y in poly], np.int32)
        cv2.fillPoly(ov, [pts], COL[k])
    blend = cv2.addWeighted(ov, 0.35, img, 0.65, 0)
    for k, poly in zones.items():
        pts = np.array([[int(x * W), int(y * H)] for x, y in poly], np.int32)
        cv2.polylines(blend, [pts], True, (255, 255, 255), 1)
        cx, cy = pts.mean(axis=0).astype(int)
        cv2.putText(blend, k, (cx - 9, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(blend, k, (cx - 9, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (255, 255, 255), 1, cv2.LINE_AA)
    big = cv2.resize(blend, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(out), big)
    print("  wrote", out.name, "|",
          ", ".join(f"{k}: {v}" for k, v in READING[site].items()))


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    for site in ("INRIA", "LISBON"):
        root = DATA / "CAVIAR" / site
        if not root.exists():
            continue
        cand = sorted(p for p in root.iterdir()
                      if (p / "frames.tar.gz").exists()
                      and (p / "frames.tar.gz").stat().st_size > 1000)
        if not cand:
            continue
        img = first_frame(cand[0] / "frames.tar.gz")
        if img is None:
            continue
        draw(f"CAVIAR-{site}", img, FIGS / f"fig_zones_{site.lower()}.png")
    print("ZONE_OVERLAYS_DONE")


if __name__ == "__main__":
    main()
