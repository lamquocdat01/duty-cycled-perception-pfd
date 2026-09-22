"""run_detector.py -- Topic 35 / V2, VIEC 2.3.

Runs the frozen pretrained detector once over every frame of every sequence of
MOT17Det (train) and URFD (camera 0 RGB) and caches the raw person detections.
Nothing here decides anything: thresholds, zones and posture rules are applied
later, in analyse_case_study.py, so that every sensitivity axis of
EVAL_PROTOCOL_V2.md section 8 can be evaluated without re-running inference.

Cache format, one .npz per sequence:
    frame  (int32)   1-based frame index
    box    (float32) N x 4, (x1, y1, x2, y2) in pixels
    score  (float32) N

Only COCO label 1 (person) is kept, and only detections with score >= 0.25,
which is below every score threshold in the protocol.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import time

import numpy as np
import torch
import torchvision
from PIL import Image

EVAL = pathlib.Path(__file__).resolve().parents[1]
DATA = EVAL / "data"
RESULTS = EVAL / "results"
CACHE = RESULTS / "det_cache"
SEED = 20260921
SCORE_FLOOR = 0.25
PROTOCOL = EVAL / "EVAL_PROTOCOL_V2_1.md"
FREEZE = "protocol_v2_1_freeze.json"


def check_protocol_freeze(amend=False):
    rec = json.load(open(RESULTS / FREEZE, encoding="utf-8"))
    h = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    if h != rec["sha256"]:
        msg = (f"EVAL_PROTOCOL_V2.md has changed since it was frozen\n"
               f"  frozen {rec['sha256']}\n  now    {h}")
        if not amend:
            raise SystemExit(msg + "\nRe-run with --amend and record the change in section 11.")
        print("WARNING:", msg)
    return rec


def load_model():
    from torchvision.models.detection import (
        fasterrcnn_mobilenet_v3_large_320_fpn,
        FasterRCNN_MobileNet_V3_Large_320_FPN_Weights as W)
    weights = W.COCO_V1
    model = fasterrcnn_mobilenet_v3_large_320_fpn(weights=weights)
    model.eval()
    torch.manual_seed(SEED)
    # locate the cached weights file so its hash can be recorded
    url = weights.url
    fn = pathlib.Path(torch.hub.get_dir()) / "checkpoints" / url.rsplit("/", 1)[1]
    sha = hashlib.sha256(fn.read_bytes()).hexdigest() if fn.exists() else None
    manifest = dict(
        architecture="fasterrcnn_mobilenet_v3_large_320_fpn",
        weights_enum="FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.COCO_V1",
        weights_url=url, weights_file=str(fn), weights_sha256=sha,
        torch=torch.__version__, torchvision=torchvision.__version__,
        score_floor_cached=SCORE_FLOOR, seed=SEED, device="cpu",
        coco_person_label=1)
    return model, weights.transforms(), manifest


@torch.inference_mode()
def run_sequence(model, tf, frames, out_path, log_every=200):
    """frames: list of (frame_index, path). Writes one .npz."""
    idx_all, box_all, score_all = [], [], []
    t0 = time.time()
    for i, (fi, path) in enumerate(frames):
        # `path` is either a file on disk or a zero-argument loader, which is how
        # CAVIAR frames are read straight out of their .tar.gz without unpacking
        # half a gigabyte of JPEGs onto the disk.
        img = (path() if callable(path) else Image.open(path)).convert("RGB")
        x = tf(torchvision.transforms.functional.pil_to_tensor(img))
        out = model([x])[0]
        keep = (out["labels"] == 1) & (out["scores"] >= SCORE_FLOOR)
        b = out["boxes"][keep].numpy().astype(np.float32)
        s = out["scores"][keep].numpy().astype(np.float32)
        idx_all.append(np.full(len(s), fi, dtype=np.int32))
        box_all.append(b)
        score_all.append(s)
        if log_every and (i + 1) % log_every == 0:
            print(f"    {i+1}/{len(frames)} frames  {(time.time()-t0)/(i+1):.3f} s/frame",
                  flush=True)
    np.savez_compressed(
        out_path,
        frame=np.concatenate(idx_all) if idx_all else np.zeros(0, np.int32),
        box=np.concatenate(box_all) if box_all else np.zeros((0, 4), np.float32),
        score=np.concatenate(score_all) if score_all else np.zeros(0, np.float32),
        n_frames=np.int32(len(frames)))
    return time.time() - t0


def mot17_sequences():
    root = DATA / "MOT17Det" / "train"
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        imgs = sorted((d / "img1").glob("*.jpg"))
        frames = [(int(p.stem), p) for p in imgs]
        yield f"MOT17Det__{d.name}", frames


def urfd_sequences():
    root = DATA / "URFall" / "seq"
    if not root.exists():
        return
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        imgs = sorted(d.rglob("*.png"))
        if not imgs:
            continue
        # file names are <seq>-cam0-rgb-<nnn>.png
        def fidx(p):
            stem = p.stem
            tail = stem.rsplit("-", 1)[-1]
            return int(tail) if tail.isdigit() else 0
        frames = sorted(((fidx(p), p) for p in imgs), key=lambda t: t[0])
        yield f"URFD__{d.name}", frames


def caviar_sequences():
    """CAVIAR frames live inside one .tar.gz per sequence.  They are read
    through a persistent handle rather than unpacked, and the frame index is
    taken from the trailing digits of the JPEG name, which is what the CVML
    ground truth's `<frame number>` refers to."""
    import io
    import tarfile
    root = DATA / "CAVIAR"
    if not root.exists():
        return
    for site in ("INRIA", "LISBON"):
        sroot = root / site
        if not sroot.exists():
            continue
        for d in sorted(p for p in sroot.iterdir() if p.is_dir()):
            tgz = d / "frames.tar.gz"
            if not tgz.exists() or tgz.stat().st_size < 1000 or not (d / "gt.xml").exists():
                continue
            # Listing a .tar.gz decompresses the whole stream, so check the cache
            # *before* opening it: otherwise a re-run spends minutes unpacking
            # archives it is about to skip.
            if (CACHE / f"CAVIAR-{site}__{d.name}.npz").exists():
                print(f"skip CAVIAR-{site}__{d.name} (cached)", flush=True)
                continue
            # getmembers() decompresses the whole stream, so a truncated
            # download raises here rather than half-way through inference.
            # Such a sequence is skipped and picked up on a later pass.
            try:
                tf = tarfile.open(tgz, "r:gz")
                names = sorted(m.name for m in tf.getmembers()
                               if m.isfile()
                               and m.name.lower().endswith((".jpg", ".jpeg")))
            except Exception as exc:                       # noqa: BLE001
                print(f"skip {d.name}: archive not readable yet ({exc})", flush=True)
                continue

            def loader(n, _tf=tf):
                return Image.open(io.BytesIO(_tf.extractfile(n).read()))

            # CAVIAR names a frame <sequence><NNNN>.jpg, and several sequence
            # names themselves end in a digit ("Browse1", "OneLeaveShop1cor"),
            # so neither "all digits" nor "trailing digit run" gives the frame
            # number.  Take the fixed-width counter, then *verify* that the
            # parsed indices are exactly 0..N-1; fall back to file order if the
            # convention does not hold for a sequence.
            # The counter width is not constant across CAVIAR: Browse1 uses four
            # digits, Browse2 and Meet_Crowd use three.  Try each width and keep
            # the one whose indices are exactly 0..N-1.
            def counter(n, width):
                tail = pathlib.Path(n).stem[-width:]
                return int(tail) if tail.isdigit() and len(tail) == width else None

            want = list(range(len(names)))
            idx = None
            for width in (3, 4, 5, 6):
                cand = [counter(n, width) for n in names]
                if None not in cand and sorted(cand) == want:
                    idx = cand
                    break
            if idx is None:
                print(f"  note: {d.name} frame names give no consistent counter; "
                      f"using zero-padded file order", flush=True)
                idx = want
            frames = [(i, (lambda nn=n: loader(nn))) for i, n in zip(idx, names)]
            frames.sort(key=lambda t: t[0])
            yield f"CAVIAR-{site}__{d.name}", frames


def main(argv):
    amend = "--amend" in argv
    only = None
    for a in argv:
        if a.startswith("--only="):
            only = a.split("=", 1)[1]
    check_protocol_freeze(amend)
    CACHE.mkdir(parents=True, exist_ok=True)
    model, tf, manifest = load_model()
    json.dump(manifest, open(RESULTS / "detector_manifest.json", "w"), indent=1)
    print("detector:", manifest["architecture"], "| weights sha256:",
          str(manifest["weights_sha256"])[:16], flush=True)

    gens = []
    if only in (None, "mot17"):
        gens.append(mot17_sequences())
    if only in (None, "urfd"):
        gens.append(urfd_sequences())
    if only in (None, "caviar"):
        gens.append(caviar_sequences())

    timings = {}
    for gen in gens:
        for name, frames in gen:
            out = CACHE / f"{name}.npz"
            if out.exists():
                print(f"skip {name} (cached)", flush=True)
                continue
            print(f"run  {name}: {len(frames)} frames", flush=True)
            dt = run_sequence(model, tf, frames, out)
            timings[name] = dict(n_frames=len(frames), seconds=round(dt, 1),
                                 s_per_frame=round(dt / max(len(frames), 1), 4))
            print(f"done {name} in {dt:.1f}s", flush=True)
    if timings:
        old = {}
        tp = RESULTS / "detector_timings.json"
        if tp.exists():
            old = json.load(open(tp, encoding="utf-8"))
        old.update(timings)
        json.dump(old, open(tp, "w"), indent=1)
    print("DETECTOR_RUN_DONE")


if __name__ == "__main__":
    main(sys.argv[1:])
