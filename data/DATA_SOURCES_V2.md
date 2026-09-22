# DATA_SOURCES_V2 — provenance, licence and terms

Topic 35 / B2 · recorded 2026-09-21, **updated for V2.1 the same day** ·
protocol: `../EVAL_PROTOCOL_V2_1.md` §2 · screening: `CORPUS_SCREEN_V2_1.md`

> **What changed in V2.1.** The primary corpus is now **CAVIAR** (§0 below).
> MOT17Det's four moving-camera sequences left the analysis entirely and its three
> static ones survive only as a secondary stratum, so the unresolved MOT17
> licence question (A-D1) no longer sits under the paper's headline. §1 is kept
> as the record of what was used in V2.0.

---

## 0. CAVIAR — the V2.1 primary corpus

| | |
|---|---|
| Retrieved | 2026-09-21 |
| URLs | `https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/` (INRIA Labs entrance lobby, Grenoble) · `https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA2/` (shopping-centre hallway, Lisbon) |
| Used | INRIA: 28 sequences with JPEG archives, 27 with ground truth. Lisbon: the along-corridor (`…cor`) view only |
| Resolution / frame rate | 384 × 288, **25 fps**, both published on the data pages |
| Ground truth | hand-labelled CVML XML per sequence, centre-based boxes, 0-based frame numbers |
| Per-file sizes and hashes | `../results/dataset_manifest_v2_1.json` |

**Licence, verbatim from the data page (2026-09-21):**

> "All data is publicly available and on this page they can be downloaded in MPEG2 format or
> split into JPEGs. If you publish results using the data, please acknowledge the data as
> coming from the EC Funded CAVIAR project/IST 2001 37540, found at URL:
> http://homepages.inf.ed.ac.uk/rbf/CAVIAR/ . **Usability is Creative Commons BY-SA**"

CC BY-SA permits derivative works and their publication, with attribution and share-alike,
and places no restriction on purpose. **This is the criterion MOT17Det fails**, and it is why
CAVIAR is the primary corpus rather than a supplement to it. The required acknowledgement
appears in the manuscript's data-availability statement. Only aggregate derived tables are
released; no frame, no ground-truth file and no per-frame verdict is redistributed.

**Static camera** — confirmed by the dataset's documentation *and* measured independently;
evidence and the measurement in `CORPUS_SCREEN_V2_1.md` §0–§1, per-sequence values in
`../results/camera_motion_v2_1.json`.

**Appearance states.** Across the sequences with ground truth the CVML `<appearance>` field
takes four values, and one of them is vanishingly rare: `visible` 29 282, `appear` 97,
`disappear` 95, **`occluded` 17** — 0.06 % of annotated person-frames. The
`exclude_occluded` sensitivity axis of the protocol is therefore run but is close to a
no-op on this corpus, and is reported as such rather than presented as evidence of
robustness.

Nothing in this directory is redistributed. The release repository (VIỆC 7) contains
**only aggregate derived tables** — event durations, counts, rates, fitted quantities — and
**no frame, no ground-truth file, and no per-frame verdict table**. The per-frame detection
cache (`../results/det_cache/*.npz`) stays local and is excluded from the release allow-list.

---

## 1. MOT17Det (MOTChallenge) -- V2.0 primary, now a secondary stratum at most

**Status in V2.1.** The four moving-camera sequences (MOT17-05, -10, -11, -13) are excluded
from the analysis; the three static ones (MOT17-02, -04, -09) are a secondary stratum that is
reported but never pooled into the primary, and only while action A-D1 below is unanswered
rather than answered "no". The rest of this section is the record as written for V2.0.

| | |
|---|---|
| Retrieved | 2026-09-21 |
| URL | `https://motchallenge.net/data/MOT17Det.zip` |
| Archive size | 1 952 547 113 bytes |
| Archive SHA-256 | see `_zips/MOT17Det.zip.sha256` |
| Used | `train/` only: 7 sequences, 5 316 frames, `gt/gt.txt` + `seqinfo.ini` |
| Benchmark papers | Milan, Leal-Taixé, Reid, Roth & Schindler, *MOT16: A Benchmark for Multi-Object Tracking*, arXiv:1603.00831; Dendorfer et al., *MOTChallenge: A Benchmark for Single-Camera Multiple Target Tracking*, IJCV 2021 |

**Published frame rates** (from each sequence's `seqinfo.ini`, which is what the protocol
uses):

| Sequence | frameRate | seqLength | resolution |
|---|---|---|---|
| MOT17-02 | 30 | 600 | 1920×1080 |
| MOT17-04 | 30 | 1050 | 1920×1080 |
| MOT17-05 | 14 | 837 | 640×480 |
| MOT17-09 | 30 | 525 | 1920×1080 |
| MOT17-10 | 30 | 654 | 1920×1080 |
| MOT17-11 | 30 | 900 | 1920×1080 |
| MOT17-13 | **25** | 750 | 1920×1080 |

The benchmark's own HTML table for MOT17Det agrees (MOT17-13 at 25 fps, MOT17-05 at 14 fps).
A machine summary of the sibling MOT17 page reported MOT17-13 as 30 fps; `seqinfo.ini` and
the MOT17Det table are the two sources that agree, and `seqinfo.ini` is what the code reads.

### ⚠ Licence — AUTHOR ACTION A-D1

**No licence or terms-of-use statement is published on the MOTChallenge download pages.**
Checked on 2026-09-21: `motchallenge.net/`, `motchallenge.net/data/MOT17/` and
`motchallenge.net/data/MOT17Det/` were fetched and searched for "licence / license /
Creative Commons / CC BY / non-commercial / terms of use / copyright" — **no match**. The
`MOT17Det.zip` archive contains no `LICENSE` or `README` file. The MOT16 arXiv posting
carries only arXiv's own non-exclusive distribution licence, which governs the *paper*, not
the *data*. The widely repeated attribution "CC BY-NC-SA 3.0" could not be traced to a
primary statement and **is therefore not asserted anywhere in the manuscript**.

*Anh Đạt*: open `https://motchallenge.net/data/MOT17Det/` in a browser (the page may render
terms through JavaScript that a plain fetch does not execute) or write to
`motchallenge-eol@vision.in.tum.de`, and record the answer here.

**What was done in the absence of a statement.** Academic, non-commercial research use;
no redistribution of imagery or annotation; only aggregate statistics published; the
benchmark papers cited. If A-D1 comes back with a licence that forbids derived publication,
the MOT17Det arm is removed and the paper stands on URFD plus the V1 corpora — this is a
**stop-and-report** condition under the prompt's rule 8 and the run would be paused, not
worked around.

---

## 2. UR Fall Detection Dataset (URFD)

| | |
|---|---|
| Retrieved | 2026-09-21 |
| URL | `http://fenix.ur.edu.pl/~mkepski/ds/uf.html` and `.../ds/data/*` |
| Used | camera 0 RGB PNG sequences: 30 fall + 40 ADL; `urfall-cam0-falls.csv`, `urfall-cam0-adls.csv`, `<seq>-data.csv` |
| Per-archive SHA-256 | `URFall/urfall_zip_sha256.txt` |
| Required citation | Bogdan Kwolek, Michal Kepski, *Human fall detection on embedded platform using depth maps and wireless accelerometer*, Computer Methods and Programs in Biomedicine 117(3), December 2014, pp. 489–501, ISSN 0169-2607 |

**Licence, verbatim from the dataset page (2026-09-21):**

> "This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0
> International License and is intended for non-commercial academic use. If you are
> interested in using the dataset for commercial purposes please contact us."

CC BY-NC-SA 4.0 permits derivative works (Section 2(a)(1)(B)) for non-commercial purposes
with attribution and share-alike. Publishing derived measurements is therefore permitted;
redistributing the imagery would require share-alike and is not done.

**Labels, verbatim from the dataset page:** each row of `urfall-cam0-*.csv` carries the
sequence name, the frame number and a posture label; the dataset uses `-1` for "person is
not lying", `0` for "person is temporarily not lying" and `1` for "person is lying".

**Frame rate.** The page does not state a single nominal rate for the RGB stream. Each
sequence ships `<seq>-data.csv` with "frame number, time in milliseconds since sequence
start"; the protocol therefore fits the rate per sequence by least squares of frame index
against time (`EVAL_PROTOCOL_V2.md` §3.3) rather than assuming 30 fps. Spot check on
`fall-01-data.csv`: frames 1, 2, 3 at 0, 33, 66 ms → 30.3 fps.

---

## 3. CDnet2014 and LASIESTA (retained from V1)

Unchanged from the first version of this evaluation; see the V1 data-sources note and
`EVAL_PROTOCOL_V1_COPY.md`. Used in V2 only for the *shape* of `F_D` and the convention
sensitivity, in frames, and never merged with the V2 corpora.

---

## 4. Excluded on purpose

- **VIRAT** — used by another manuscript in this portfolio; excluded by prompt rule 2.1.
- **PPE-Unified** — any data, corpus or manuscript from it; excluded by prompt rule 2 (the
  paper stands alone; EAAI review in progress).
- Any number, corpus or estimate from Deep3, AwP, #4, #5, AAP, T30, #34 — excluded by CP-B0.

## 5. Detector weights

`torchvision` `fasterrcnn_mobilenet_v3_large_320_fpn`, weights `COCO_V1`, downloaded from
`https://download.pytorch.org/models/fasterrcnn_mobilenet_v3_large_320_fpn-907ea3f9.pth`.
File hash, torch and torchvision versions: `../results/detector_manifest.json`. BSD-3-Clause
(torchvision); the weights are the published COCO checkpoint and are not fine-tuned.
