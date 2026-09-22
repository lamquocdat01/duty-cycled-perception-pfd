# EVAL_PROTOCOL_V2.1 — static-camera corpora (đợt 2b)

**Status: FROZEN 2026-09-21, before the detector was run on any new corpus and before any
result of this protocol was looked at.** The freeze is recorded by the SHA-256 of this file
in `results/protocol_v2_1_freeze.json`; `run_detector.py` and the analysis abort if the hash
of this file no longer matches.

This protocol supersedes `EVAL_PROTOCOL_V2.md` for the case study. V2's §1 (purpose and
out-of-scope), §5 (detector), §6 (estimands) and §9 (retained V1 analysis) carry over
**unchanged** and are not restated; what changes is the corpus, the zones, the event
convention and the reporting of the excluded material.

---

## 1. Why there is a V2.1

`EVAL_PROTOCOL_V2.md` made MOT17Det the primary corpus. 109 of the 135 uncensored events it
produced came from sequences filmed with a **moving** camera. A danger zone fixed in image
coordinates is not a danger zone when the image is panning, and the model of Section 3
assumes a monitor watching a fixed scene. The V2.0 numbers are therefore not usable as they
stand.

**This is a corpus-selection error, not a coding error, and not a result-driven decision.**
The sequences leave the primary analysis because of the camera attribute published by the
benchmark (MOT16, arXiv:1603.00831, Table 2) and confirmed by an independent measurement
(§3), both of which are properties of the *recording*, available before any hazard, duration
or miss rate is computed. Evidence and the full screening of replacements:
`data/CORPUS_SCREEN_V2_1.md`.

Nothing is deleted. The complete V2.0 result set is kept in `results_v2_0/` and is reported
in the supplementary under its own name, with per-sequence event counts.

## 2. Corpora

| Corpus | Role | Source | Clips | Frame rate | Licence |
|---|---|---|---|---|---|
| **CAVIAR-INRIA** (entrance lobby, Grenoble) | **primary** | `homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/` | 28 with JPEG archives, 27 with ground truth | **25 fps**, published | CC BY-SA, verbatim on the data page, attribution to EC project IST 2001 37540 |
| **CAVIAR-LISBON** (shopping-centre hallway), *along-corridor view only* | **primary** | `homepages.inf.ed.ac.uk/rbf/CAVIARDATA2/` | the `…cor` folders | **25 fps**, published | as above |
| **URFD** | contrast case (§8) | as V2 | 30 fall + 40 ADL | fitted per sequence | CC BY-NC-SA 4.0 |
| MOT17Det static subset (02, 04, 09) | **secondary stratum only, never pooled into primary** | as V2 | 3 | 30 fps | ⚠ unresolved, author action A-D1 |
| MOT17Det moving subset (05, 10, 11, 13) | **excluded**; reported in the supplementary as "run V2.0 — removed from primary because the camera moves" | as V2 | 4 | — | — |
| CDnet2014 + LASIESTA | retained shape analysis, as V2 §9 | as V1 | 53 + 48 | n/a | as V1 |

**The Lisbon `…front` view is excluded on purpose.** It is a time-synchronised second camera
on the *same* physical event, so including both views would put two copies of each event into
a bootstrap that assumes videos are independent.

## 3. The static-camera gate

A sequence enters the primary analysis only if its camera is static, and "static" is a
measurement made by `code/camera_motion_check.py`: the median magnitude of the global
frame-to-frame translation, estimated by phase correlation over 60 frame pairs at a stride of
5 frames, expressed as a percentage of the image diagonal.

**Threshold: median shift < 0.1 % of the image diagonal per 5-frame interval.**

The threshold is fixed here, before any new corpus is processed. It was chosen from the gap
in the already-measured MOT17Det values — static sequences measure 0.004–0.023 %, moving ones
0.622–1.500 %, a factor of 27 with nothing between — and it sits in the middle of that gap on
a log scale. Every sequence of every corpus is measured and checked against it; any sequence
that fails is excluded from the primary analysis and listed by name in the results.

**Same-camera check.** All sequences of a site are asserted to share one camera. This is
verified rather than assumed: the first frame of each sequence is compared with the site's
median first frame, and the mean absolute difference is recorded per sequence. Outliers are
reported; the check exists so that a re-shot or re-aimed sequence cannot enter the pool
unnoticed.

## 4. Hazard, zones and the ground-truth predicate

Hazard: **a person is inside a predefined danger zone.**

### 4.1 Ground truth

CAVIAR ships hand-labelled CVML XML per sequence:
`<frame number="n"><objectlist><object id="k"><box xc yc w h/><appearance>…`.
Frame numbers are 0-based; boxes are **centre-based**.

- A ground-truth person in frame `n` is any `<object>` carrying a `<box>`.
- **Foot point** `= (xc, yc + h/2)`, normalised by the image size `(384, 288)`.
- **Primary: every appearance state counts.** Sensitivity: exclude objects whose
  `<appearance>` is `occluded`. (This is the CAVIAR analogue of the MOT17 visibility axis of
  V2 §8.)
- The evaluation window of a sequence is every frame present in the XML.

### 4.2 Zones — fixed from scene geometry, per camera

Three polygons per camera, in normalised image coordinates, **defined by looking at frame 0
of the site and nothing else**: no ground truth, no detector output, and no event count was
consulted. They are the same for every sequence of that camera, because it is the same
camera looking at the same room. Overlay renderings go to the supplementary.

**CAVIAR-INRIA** (entrance lobby):

| Zone | Reading | Polygon, normalised `(x, y)`, `y` downwards |
|---|---|---|
| `Z1` | entrance apron, the floor just inside the doors | `(0.00,0.70) (0.40,0.68) (0.48,1.00) (0.00,1.00)` |
| `Z2` | central walkway, the open floor people cross | `(0.30,0.30) (0.75,0.30) (0.80,0.70) (0.32,0.70)` |
| `Z3` | floor beside the column, lower right | `(0.55,0.72) (0.95,0.62) (1.00,1.00) (0.58,1.00)` |

**CAVIAR-LISBON** (corridor, along-corridor view). The polygons follow the corridor's
perspective, narrowing with depth:

| Zone | Reading | Polygon, normalised `(x, y)` |
|---|---|---|
| `Z1` | shop-front strip, walkway against the shop windows | `(0.15,1.00) (0.38,1.00) (0.30,0.42) (0.19,0.42)` |
| `Z2` | corridor centre | `(0.38,1.00) (0.70,1.00) (0.45,0.40) (0.32,0.40)` |
| `Z3` | balustrade side, the strip along the railing over the void | `(0.70,1.00) (0.95,0.92) (0.62,0.42) (0.47,0.42)` |

A **monitoring channel** is a `(sequence, zone)` pair. `hazard(t) = 1` iff at least one
ground-truth person's foot point lies inside the zone. The primary analysis pools all
channels of both sites; **per-zone and per-site results are reported alongside**, never
pooled away.

## 5. Detector — unchanged from V2

`torchvision` `fasterrcnn_mobilenet_v3_large_320_fpn`, weights
`FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.COCO_V1`, **not fine-tuned**, CPU, score
threshold **0.50**, COCO label 1. `alarm(t) = 1` iff some predicted person box with score
≥ 0.50 has its foot point inside the zone. Score-threshold sensitivity `{0.30, 0.50, 0.70}`.
Every frame is scored once and the verdicts are re-sampled offline to simulate every
invocation period and every phase. **Nothing about the detector changes in V2.1**, so a
difference between V2.0 and V2.1 cannot be a detector difference.

## 6. Events

As V2 §4, with one change and two additions.

1. `hazard(t)` over the evaluation window of a channel.
2. **Gap merge, primary `g = 0.5` s.** The rationale is physical rather than statistical: a
   single incursion that flickers out for less than the time available to react is still one
   demand, so the merge tolerance should be the required reaction time `T_react`.
   ⚠ **`T_react` could not be sourced from a readable standard** — ISO 13855 is paywalled
   (author action A-W1) — so **0.5 s is declared here as a convention, not as a derived
   value**, and it is frozen before the run. If A-W1 supplies the standard's constant, `g`
   is re-derived and the analysis re-run; the sensitivity axis below already brackets the
   plausible range.
   Sensitivity: `g ∈ {0, 0.1, 0.5, 1.0}` s.
3. An **event** is a maximal run after merging; duration `D = n_frames / f`, in seconds.
4. **Censoring**: primary excludes events touching either end of the window; the count is
   reported. Sensitivity: include.
5. No minimum-duration filter. **But two flicker diagnostics are mandatory** (§7.3).
6. Channels yielding zero uncensored events are recorded, not silently dropped.

## 7. Reporting rules added in V2.1

### 7.1 Clusters beside every interval
Bootstrap resampling is **by video**, as in V2. The **number of clusters is printed next to
every confidence interval**. A corpus contributing fewer than 10 clusters has its intervals
labelled **"indicative only"** wherever they appear.

### 7.2 Per-site and per-zone
Every headline quantity is reported pooled, per site, and per zone.

### 7.3 Flicker diagnostics
Two numbers, reported with the duration law:

- the count and share of events shorter than **0.2 s**;
- the share of events that are **zone-edge flicker**: the foot point stays within **5 % of
  `sqrt(zone area in pixels)`** of the zone boundary for the *whole* event, measured with a
  signed point-to-polygon distance. Such an event is a person walking along the boundary,
  not a genuine incursion, and it is the mechanism the audit identified behind the 20 of 140
  sub-0.2 s events in V2.0.

Both are reported; neither is used to filter the primary analysis, because a filter chosen
after seeing durations would be exactly the kind of tuning §10 forbids.

## 8. URFD, read correctly (VIỆC 2b.3)

The V2.0 report treated URFD as untestable because every fall event is right-censored. That
was too strict, and the audit is right that it was.

**The model check is valid under right-censoring.** `miss(D, K, p)` is compared against a
measurement that uses the **same observed `D`** on both sides: the measured miss rate
enumerates schedule phases over the *observed* frames of the event, and the prediction is
evaluated at the *observed* `n_frames`. Truncating an event shortens both sides identically,
so the comparison tests the model exactly as it would on an uncensored event. Censoring
affects the estimate of **`F_D`**, not the model check — and there it is conservative: the
observed `D` is a lower bound on the true `D`, so `M(K) = E[(1 − D/K)₊]` computed from
observed durations is an **upper** bound on the true structural miss.

Therefore: the URFD measured-vs-modelled table is reported on the **include-censored** axis
(n ≈ 35 events), split `fall` / `ADL`, and `F_D`-derived quantities from URFD are labelled as
upper bounds. **No detector is re-run**; the V2 `det_cache` is reused unchanged.

## 9. Sensitivity axes (all reported)

| Axis | Primary | Variants |
|---|---|---|
| Detector score threshold | 0.50 | 0.30, 0.70 |
| CAVIAR appearance | all states | exclude `occluded` |
| Danger zone | pooled over Z1–Z3 | Z1, Z2, Z3 separately |
| Site | pooled | INRIA only, Lisbon only |
| Gap merge `g` | **0.5 s** | 0, 0.1, 1.0 s |
| Censored events | excluded | included |
| Aspect-ratio rule (URFD) | 1.00 | 0.80, 1.20 |
| Hazard label (URFD) | `{1}` | `{0, 1}` |

## 10. Integrity

- Seeds `20260921`; bootstrap replicate counts recorded.
- Every number in the manuscript is emitted to `results/numbers_v2.json` and rendered into
  `02_Manuscript/numbers.tex`. No number is typed by hand.
- `results/events_v2.csv` is hashed and the hash appears in the data-availability statement.
- A **V2.0 → V2.1 comparison table** for the eight headline quantities is mandatory, so the
  effect of the corpus change is visible rather than inferred.
- Results are reported as they fall. If the static corpora give a smaller floor, a weaker
  headline, or a model that fits worse, the paper says so. No threshold in §3, §4 or §6 is
  revisited after a result is seen.

## 11. Amendment 2′ --- the viewpoint gate is WITHDRAWN, and what replaced it

**An earlier Amendment 2 added a "viewpoint gate" that excluded the CAVIAR-INRIA lobby from
the primary analysis on the ground that its median annotation aspect ratio (h/w = 0.71) was
below 1. That amendment was wrong and is withdrawn in full.** No site is excluded by it.

**Why it was wrong.** The gate's justification was that on an overhead view the hand
annotation and a COCO detector describe different shapes, so comparing the bottom edges of
their boxes measures nothing. The evidence offered was that annotation boxes at that site
have median aspect 0.71 while detector boxes have 1.51 and 5.5 times the area. An
independent audit showed that this comparison is not between two descriptions of the same
person. Measured against the annotation at IoU >= 0.3, the detector's **recall at the lobby
is 0.000--0.097 (median 0.008) and its precision 0.000--0.107 (median 0.016)**: it
essentially never finds the annotated people. Between 25 % and 83 % of its detections there
fall in a single 10 x 10 pixel cell -- median 37 %, in every one of its 27 sequences -- one
static false positive. The "detector boxes" in the aspect comparison were therefore
overwhelmingly that object, not people.

The honest reading is simpler and less flattering: **the lobby's detection probability --
0.026 on the ten-sequence check that first raised the alarm, 0.018 over all 27 -- is the
detector's real performance there.** Excluding the site on a geometric pretext would have
removed a corpus because the detector fails on it, which is selection on an outcome. That is
exactly what the protocol forbids.

**What replaces it.**

1. **No site is excluded.** The lobby returns to the analysis. `F_D` and `M(K)` depend only
   on the ground truth, so the structural quantities are computed on **both** sites, pooled
   **and reported per site** -- the duration-law quantiles per site in
   `results/fd_summary_v2.csv`, `M(K)` per site in `results/bridge_v2.csv`.
2. **The model check is reported per site with the local p_hat.** The model takes `p` as an
   input; a site where `p` is small is a *detector-bound* regime, like the UR Fall corpus of
   section 8, not an inadmissible one. Both regimes are informative and both are reported.
3. **The lobby is an operational-design-domain finding**, stated as such: annotated people
   there occupy a median of about 725 px^2 in a 384 x 288 wide-angle overhead view, and an
   off-the-shelf COCO detector recalls essentially none of them. That is a fact about the
   detector's ODD, evidenced by recall at IoU, and it belongs in the paper.
4. **A new alarm axis applies to every corpus**, not only the suspect one:
   - `any_box` (the originally frozen rule): any detected person box whose foot point lies
     in the zone raises the alarm;
   - `gt_matched`: the same, and the detection must additionally match an annotated person
     at IoU >= 0.3.
   `p_hat`, the miss rate and the false-alarm rate are reported under **both**, at the two
   invocation periods the sensitivity tables use (0.5 s and 1 s). The reason
   is general: under `any_box` a static false positive standing inside a zone would "detect"
   every event there, inflating `p_hat` and deflating the miss rate, and no amount of care
   elsewhere would reveal it. The rule needs a box annotation, so it is undefined for the UR
   Fall corpus, which carries a per-frame posture label and no boxes; that is reported as
   undefined rather than silently omitted.
5. **A static-false-positive audit is mandatory for every corpus.** Per sequence:
   - the detector's **recall and precision** against the annotation at IoU >= 0.3
     (undefined, and reported as such, where there is no box annotation);
   - the **share of detections** falling in the single most frequent cell of a 38 x 28 grid
     over the image -- 10 x 10 px at CAVIAR's 384 x 288, and the same fraction of the frame
     at any other resolution, so the corpora are comparable;
   - the same two shares over the **3 x 3 neighbourhood** of that cell. A stationary false
     positive does not sit in exactly one cell -- the box jitters by a few pixels -- so the
     single-cell figure understates it and the neighbourhood figure is the one to read;
   - a sequence is declared to contain a **persistent detection cluster** when that
     neighbourhood receives a detection in **more than half of the evaluated frames**;
   - the **share of that cluster's detections that match an annotated person** at
     IoU >= 0.3. Persistence alone does not say what the cluster is: a person who stands
     still for the whole clip produces one too. A persistent cluster whose match rate is
     below 0.5 is a **stationary false positive**; above it, the detector is right and the
     person is simply stationary. This distinction is measured, not assumed, and is
     undefined where there is no box annotation;
   - **whether that cell lies inside a danger zone**, named. This is what decides whether a
     stationary false positive can raise alarms at all: one outside every zone inflates
     nothing, one inside a zone would "detect" every event in it.
   Reported in `results/detector_quality_v2_1.csv`, for every corpus.

**Disclosure about timing, which matters here.** The withdrawn gate was written after seeing
an anomalous detection rate on the lobby. This replacement was written after the results for
**both** sites existed. It is therefore not protected by any freeze, and the only honest
defence of it is its direction: it **removes** an exclusion the protocol had made and
**adds** reporting axes. It restores data rather than discarding it, and every quantity it
introduces is reported for every corpus rather than for the one under suspicion. The
aspect-ratio numbers are kept as descriptive statistics of the two sites and no longer gate
anything.

## 12. Amendment log

| Date | Change | Reason |
|---|---|---|
| 2026-09-21 14:09:56Z | Protocol V2.1 frozen (initial version) | Replaces the primary corpus after the independent audit found that 109 of 135 V2.0 events came from moving cameras. Carried over from V2 unchanged: the detector, its weights and thresholds, the estimator definitions, and the model. |
| 2026-09-21, Amendment 2 (**withdrawn same day**) | Added a viewpoint gate on the median ground-truth box aspect ratio. | Believed at the time that an overhead view made the foot-point predicate meaningless. |
| 2026-09-21, Amendment 2′ | §11 rewritten: the viewpoint gate is **withdrawn**, no site is excluded, the lobby is reported as an ODD finding, and a `gt_matched` alarm mode plus a static-false-positive audit are added **for every corpus**. | An independent audit showed the gate's evidence compared annotated people against a static false positive: detector recall at the lobby is 0.000–0.097 (median 0.008) and 25–83 % of its detections sit in one 10×10 px cell, 92 % in its 3×3 neighbourhood. The low detection rate there is real detector performance, so excluding the site was selection on an outcome. See §11, including the disclosure that this amendment was written after both sites' results existed. |
| 2026-09-22, Amendment 2′ (clarified) | §11 item 5: the persistence test is renamed a **persistent detection cluster** and a **cluster match rate** is added; a stationary *false positive* now requires persistence **and** a match rate below 0.5. No estimator, threshold, detector setting, zone or event changes; the same detections are counted either way. | Running the test as first written showed the naming was wrong: on MOT17Det all three static sequences carry a persistent cluster inside a danger zone, but in one of them (MOT17-04) 97 % of that cluster matches an annotated person -- it is a person standing still, not a false positive -- while in the other two 0 % matches. Calling all three false positives would have been a claim the data does not support. |
