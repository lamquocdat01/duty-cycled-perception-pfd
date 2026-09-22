# EVAL_PROTOCOL_V2 — real safety hazards, real detector (Topic 35 / B2, V2)

**Status: FROZEN 2026-09-21, before the detector was run and before any result of this
protocol was looked at.** The freeze is recorded by the SHA-256 of this file in
`results/protocol_v2_freeze.json`, written by `run_case_study.py` at the start of every run;
the run aborts if the hash of this file does not match the one recorded at freeze time,
unless `--amend` is passed, which also appends to §11.

Any change after the timestamp above must be recorded in §11 (amendment log) with date and
reason, and every affected result must be regenerated.

This protocol supersedes `EVAL_PROTOCOL_V1_COPY.md` for the case study. The V1 protocol
remains in force, unmodified, for the CDnet2014 + LASIESTA *shape* analysis (§9).

---

## 1. What this evaluation is for

V1 measured the event-duration law `F_D` from ground-truth annotation and swept the
per-invocation detection probability `p`. It never ran a detector and never named a hazard,
and the editor's reading of that is recorded in `VENUE_REJECT_PLAN_20260921.md` §2.

V2 answers a different, falsifiable question:

> On a real, publicly annotated video corpus with a **named safety hazard** and a real
> pretrained detector, does the sampling-miss model of `model_v2.py` predict the
> **end-to-end miss rate** of a duty-cycled monitor, as a function of the invocation
> period `K`, within the uncertainty of the measurement?

The model is stated in `code/model_v2.py` and was validated against an independent
Monte-Carlo simulation of the schedule *before* this protocol was written
(`results/model_mc_validation.json`). What is being tested here is not the algebra but
the modelling assumptions: uniform schedule phase, a single per-invocation detection
probability `p`, and within-event dependence captured by one beta-factor.

**Out of scope, and not to be claimed from these numbers:**

- No claim that either corpus is representative of any particular industrial installation.
- No claim about detector quality. The detector is an off-the-shelf COCO model used
  without fine-tuning; a low `p` is a measurement, not a defect of the model under test.
- No compliance claim. Every SIL band is labelled "PFD-like" throughout.
- No claim beyond the two hazards defined in §3.

## 2. Corpora

| Corpus | Source | Content used | Frame rate | Licence |
|---|---|---|---|---|
| **MOT17Det** (train split) | `https://motchallenge.net/data/MOT17Det.zip` | 7 sequences, 5 316 frames, per-frame ground-truth pedestrian boxes (`gt/gt.txt`) | published per sequence in `seqinfo.ini` (14 or 30 fps) | CC BY-NC-SA 3.0 (MOTChallenge terms) |
| **UR Fall Detection (URFD)** | `http://fenix.ur.edu.pl/~mkepski/ds/uf.html` | camera 0 RGB, 30 fall + 40 ADL sequences, per-frame posture labels (`urfall-cam0-falls.csv`, `urfall-cam0-adls.csv`) | derived per sequence from the timestamps in `<seq>-data.csv` (see §3.3) | CC BY-NC-SA 4.0, non-commercial academic use |
| CDnet2014 + LASIESTA | as V1 | 53 videos + 48 sequences, shape of `F_D` only | not uniformly published | as V1 |

Both new corpora permit research use and the publication of derived measurements; neither
permits redistribution of the imagery. **No frame, no ground-truth file and no per-frame
verdict table derived pixel-wise from either corpus is re-hosted.** The release contains
only aggregate tables (durations, counts, rates). Verbatim licence text and the retrieval
URLs go in `data/DATA_SOURCES_V2.md`; file counts and SHA-256 of the downloaded archives go
in `results/dataset_manifest_v2.json`.

## 3. Hazards, and the ground-truth hazard predicate

Two hazards are named, one per corpus. In both cases the ground truth defines a binary
per-frame predicate `hazard(t)`, and the monitor's job is to raise an alarm while it holds.

### 3.1 MOT17Det — "a person is inside a predefined danger zone"

- **Ground-truth people.** Rows of `gt/gt.txt` with class `1` (pedestrian), confidence flag
  `1`, and visibility `>= 0.25` (primary; sensitivity over `{0.00, 0.25, 0.50}`).
- **Foot point** of a box `(x, y, w, h)` is `(x + w/2, y + h)`, in pixels, converted to
  image-normalised coordinates by dividing by `imWidth`, `imHeight`.
- **Danger zones.** Three fixed polygons in normalised image coordinates, *identical for
  every sequence*, chosen from image geometry alone and frozen here before any detector
  output or any ground-truth statistic was inspected:

  | Zone | Reading | Polygon (normalised `(x, y)`, `y` downwards) |
  |---|---|---|
  | `Z1` | approach corridor, bottom centre | `(0.30,1.00) (0.70,1.00) (0.60,0.60) (0.40,0.60)` |
  | `Z2` | left-hand margin | `(0.00,0.55) (0.20,0.55) (0.20,1.00) (0.00,1.00)` |
  | `Z3` | right-hand margin | `(0.80,0.55) (1.00,0.55) (1.00,1.00) (0.80,1.00)` |

- A **monitoring channel** is a `(sequence, zone)` pair: 7 x 3 = 21 channels.
  `hazard(t) = 1` iff at least one ground-truth person's foot point lies inside the zone.
- The **primary analysis pools all 21 channels**; per-zone results are reported alongside
  it (VIEC 2.1 requires the zone sensitivity to be reported, not hidden).

### 3.2 URFD — "a person is lying on the floor"

- `urfall-cam0-*.csv` column 3 is the posture label: `-1` not lying, `0` transition,
  `1` lying.
- `hazard(t) = 1` iff the label is `1` (primary). Sensitivity: labels `{0, 1}` together.
- The **evaluation window** of a sequence is the set of frames that carry a label row;
  frames without one are dropped (they carry no annotation), mirroring CDnet's
  `temporalROI` rule in V1.
- **Amended 2026-09-21, see §11.** The 40 ADL sequences *do* carry `1` labels: 1 470
  labelled frames in 16 runs, against 903 frames in 30 runs across the fall sequences.
  (In an ADL sequence the subject lies down deliberately — on a sofa or the floor — rather
  than falling.) The hazard predicate is a statement about *posture*, and it is applied
  unchanged: a run of `1` labels is an event wherever it occurs. ADL sequences therefore
  contribute events as well as hazard-free time. Results are reported split by sequence
  kind (`fall` / `adl`) so that the difference is visible rather than pooled away, and the
  interpretation of an ADL "lying" event — hazard-like by the predicate, not a fall — is
  stated in the limitations.
- Three frame indices in `urfall-cam0-adls.csv` are non-consecutive (the label file skips a
  frame). Durations are counted in labelled frames, so such a skip shortens the event it
  falls in by one frame; the count is recorded in the manifest.

### 3.3 Time base

Durations are reported in **seconds**, which is what V1 could not do.

- MOT17Det: `f` = the `frameRate` field of `seqinfo.ini` (published by the dataset).
- URFD: `f` is estimated per sequence by ordinary least squares of frame index on the
  timestamp column of `<seq>-data.csv` (milliseconds since sequence start). The fitted
  rate and its residual are recorded per sequence; a sequence whose fitted rate differs
  from 30 fps by more than 10 % is reported separately rather than silently pooled.

## 4. Events

Unchanged in form from V1 §4, with the gap-merge parameter now expressed in seconds:

1. Form `hazard(t)` over the evaluation window of a channel.
2. **Gap merge `g`**: two runs separated by `<= g` seconds of inactivity are merged.
   **Primary `g = 0`.** Sensitivity: `g in {0, 0.1, 0.5}` s.
3. An **event** is a maximal run after merging; its duration `D` is
   `(number of frames) / f`, in seconds.
4. **Boundary censoring**: an event touching either end of the evaluation window is
   flagged censored; **the primary analysis excludes censored events** and reports how
   many were excluded. Sensitivity: include them.
5. No minimum-duration filter.
6. Channels yielding zero uncensored events are recorded in the manifest, not dropped
   silently.

Recorded per event: `corpus, channel, sequence, zone, event_id, start_frame, end_frame,
n_frames, fps, D_seconds, censored`.

## 5. Detector

**Pretrained, off the shelf, not fine-tuned, run once over every frame.**

- `torchvision.models.detection.fasterrcnn_mobilenet_v3_large_320_fpn`,
  weights `FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.COCO_V1`.
  The torch / torchvision versions and the SHA-256 of the downloaded weights file are
  recorded in `results/detector_manifest.json`.
- Inference on CPU, one frame at a time, no test-time augmentation, no tracking, no
  temporal smoothing. Deterministic: `torch.use_deterministic_algorithms` is not required
  because the network is evaluated in `eval()` mode with no stochastic layers; the seed
  `20260921` is fixed anyway.
- **Score threshold `s = 0.50`** (primary), COCO label `1` = person.
  Sensitivity: `s in {0.30, 0.50, 0.70}`.
- **Per-frame verdict.**
  - MOT17Det, channel `(sequence, zone)`: `alarm(t) = 1` iff some predicted person box
    with score `>= s` has its foot point inside the zone.
  - URFD: `alarm(t) = 1` iff some predicted person box with score `>= s` has aspect ratio
    `w / h >= 1.0`, i.e. is wider than it is tall. This is the standard bounding-box
    posture rule for fall detection; the threshold `1.0` is frozen here, before any
    verdict was computed. Sensitivity: `w/h in {0.8, 1.0, 1.2}`.
- Every frame is scored **once**; the per-frame verdict series is then re-sampled offline
  to simulate every `(K, phase)` pair. No frame is ever re-run.

## 6. Estimands

Let `q = 1 - p`. All confidence intervals are 95 %.

1. **Per-invocation detection probability `p`**: the fraction of hazard-active frames on
   which `alarm(t) = 1`. Reported with a Wilson interval (frames treated as independent,
   which they are not — stated as such) *and* with a **cluster bootstrap over videos**
   (`B = 2 000`, seed `20260921`), which is the interval quoted in the paper.
   Bootstrap resampling is **by video, never by event or by frame** (VIEC 2.2).
2. **Within-event dependence `beta`.** For a lag `l`, let `P2(l)` be the probability that
   two hazard-active frames of the same event, `l` frames apart, both carry
   `alarm = 0`. Under the beta-factor model of `model_v2.py` §1.2,
   `P2 = beta q + (1 - beta) q^2`, giving the moment estimator
   `beta_hat(l) = (P2(l) - q^2) / (q - q^2)`.
   Reported for `l = 1 .. 30`, with the lag-`l` autocorrelation of the verdict series
   alongside. The **headline `beta_hat` is the value at the lag equal to the `K` being
   modelled**; the whole curve is reported.
3. **End-to-end miss rate, measured.** For an invocation period `K` (frames) and every
   phase offset `phi in {0, ..., K-1}`, an event is *missed* iff no sampled frame inside
   it carries `alarm = 1`. `miss_hat(K)` is the mean over events and over all `K` phases —
   an exact enumeration of the phase distribution, not a sample of it.
4. **Model prediction.** `miss_model(K) = mean over events of p_miss_exact(D_i_frames, K,
   p_hat, beta_hat)`, with `p_hat`, `beta_hat` from 1 and 2 and `D_i` the *measured*
   duration of event `i`. Prediction and measurement are compared per `K`; the comparison
   is the headline validation figure. **`p_hat` and `beta_hat` are the only quantities
   fitted; the miss rate is not fitted to anything.**
5. **False alarms.** Over frames with `hazard(t) = 0`, the fraction with `alarm(t) = 1`,
   converted to alarms per hour at invocation period `K` as
   `FAR(K) = fa_rate * 3600 / K`. Reported for MOT17Det (non-hazard frames of each
   channel) and for URFD (**all hazard-free frames of all 70 sequences**, not only the ADL
   ones — see the amendment in §3.2).
6. **Latency.** For each detected event, the time from the event's first frame to the
   first invocation that fires, in seconds; reported as a distribution against the
   worst-case schedule bound `(K - 1) / f`.
7. **Bridge quantities**, from the measured `F_D` in seconds: `M(K)`, `PFD_like`, the
   PFD-like band, the event-level `n_req`, and the 1oo2 staggered improvement
   `M(K/2) / M(K)` and `E[((1-D/K)_+)^2] / M(K)`.

## 7. The end-to-end worksheet (VIEC 2.4)

For one named hazard per corpus, in this order, with every number traceable:
hazard -> required reaction time `T_react` (from a standard or a DOI-bearing source, **not
invented**; if no citable value is found the cell is left as an author action and the
worksheet is run over a range) -> constraint on `K` -> `M(K)` -> `p_hat`, `beta_hat` ->
`PFD_like` -> band -> event-level `n_req` -> improvement from a staggered 1oo2.

## 8. Sensitivity analysis (all reported)

| Axis | Primary | Variants |
|---|---|---|
| GT visibility (MOT17Det) | 0.25 | 0.00, 0.50 |
| Detector score threshold | 0.50 | 0.30, 0.70 |
| Aspect-ratio rule (URFD) | 1.00 | 0.80, 1.20 |
| Danger zone | pooled over Z1–Z3 | Z1, Z2, Z3 separately |
| Gap merge `g` | 0 s | 0.1 s, 0.5 s |
| Censored events | excluded | included |
| Hazard label (URFD) | `{1}` | `{0, 1}` |
| Corpus | pooled | MOT17Det only, URFD only |

## 9. Retained V1 analysis

CDnet2014 + LASIESTA keep their V1 role — the *shape* of `F_D` and the convention
sensitivity — and are reported in condensed form, with the bulk moved to the
supplementary. Their numbers are not recomputed and not merged with the V2 corpora: the
V1 durations are in frames and the two hazards above are not change-detection.

## 10. Reproducibility and integrity

- Every number in the manuscript is emitted to `results/numbers_v2.json` and rendered into
  `02_Manuscript/numbers.tex`; no number is typed by hand (checklist C6).
- Seeds fixed at `20260921`; bootstrap replicate counts recorded.
- `results/events_v2.csv` and `results/verdict_summary_v2.csv` are hashed (SHA-256) and the
  hashes appear in the data-availability statement.
- Results are reported as they fall. If the model does not predict the measurement, that is
  the finding, and it is not repaired by re-tuning any threshold of §3 or §5.

## 11. Amendment log

| Date | Change | Reason |
|---|---|---|
| 2026-09-21 | Protocol frozen (initial version) | — |
| 2026-09-21, before the analysis was run and before any result of it was seen | §3.2 and §6.5: corrected the factual claim that the URFD ADL sequences carry no `1` labels. They carry 1 470 such frames in 16 runs. The **hazard predicate is unchanged**; what changes is that ADL sequences also contribute events, results are reported split by sequence kind, and the false-alarm denominator is all hazard-free frames rather than all ADL frames. Also recorded: three non-consecutive frame indices in the ADL label file. | The original sentence was a wrong statement about the data, made before the label files were inspected. It is corrected rather than worked around. The analysis code already applied the predicate uniformly, so no estimator definition changed and nothing was re-tuned; only the prose describing the data, and the false-alarm denominator, were wrong. The detector had already been run at this point, but the detector is independent of the hazard labels and no miss rate, floor or fitted quantity had been computed. |
