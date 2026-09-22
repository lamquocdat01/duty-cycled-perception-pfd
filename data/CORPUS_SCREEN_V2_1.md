# CORPUS_SCREEN_V2_1 — screening static-camera corpora

Topic 35 / B2, đợt 2b · screened 2026-09-21 · required by VIỆC 2b.1 ·
spec: `00_Plan/AUDIT_COWORK_CP-U5_20260921.md` blocker B1

**Why this exists.** The V2.0 primary corpus was MOT17Det. 109 of its 135 uncensored events
come from sequences filmed with a **moving** camera, and a danger zone fixed in image
coordinates is not a danger zone at all when the image is panning. The model's premise
(Section 3 of the manuscript: a monitor watching a fixed scene) requires a static camera, so
the corpus has to be replaced before any number from it is used.

The six criteria below are the audit's, taken as mandatory. A candidate that fails any one
of them is out; none was waived.

---

## 0. The static-camera test, made a measurement

"Static" is not taken on trust from anybody's prose. `code/camera_motion_check.py` estimates
the **global** frame-to-frame translation with phase correlation — a whole-image
frequency-domain estimator, so it follows the background rather than the people crossing it
— on 60 frame pairs per sequence at a stride of 5 frames, and reports the median shift as a
percentage of the image diagonal.

Run on the V2.0 corpus, against the camera attribute published in the MOT16 benchmark paper
(arXiv:1603.00831, Table 2), which MOT17 reuses:

| Sequence | Benchmark says | Measured median shift (% of diagonal) |
|---|---|---|
| MOT17-02 | static | **0.023** |
| MOT17-04 | static | **0.004** |
| MOT17-09 | static | **0.005** |
| MOT17-05 | moving (hand-held) | **1.500** |
| MOT17-10 | moving | **0.622** |
| MOT17-11 | moving | **0.790** |
| MOT17-13 | moving | **0.890** |

The measurement and the documentation agree on all seven, and they separate with a gap of
more than an order of magnitude: the largest "static" value is 0.023 % and the smallest
"moving" value is 0.622 %, a factor of 27 with nothing in between.

**Frozen threshold: a sequence is static if the median global shift is below 0.1 % of the
image diagonal per 5-frame interval.** The threshold sits in the middle of that empty gap on
a log scale. It is fixed here, before any event, duration or miss rate is computed on any new
corpus, and it is applied to every corpus including the candidates.

## 1. CAVIAR — **ACCEPTED**, both sites

EC-funded project IST 2001 37540; data pages
`https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/` (INRIA Labs entrance lobby, Grenoble) and
`https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA2/` (shopping centre hallway, Lisbon).

| # | Criterion | Evidence |
|---|---|---|
| 1 | **static camera, confirmed by the dataset's own documentation** | The page states the clips were "filmed … with a wide angle camera lens **in the entrance lobby** of the INRIA Labs at Grenoble", and for the second site "a wide angle lens along and across the hallway in a shopping centre in Lisbon", with "for each sequence … **two time synchronised videos**, one with the view across and the other along the hallway" — two fixed viewpoints. Two further tells, both only meaningful for a fixed camera: the dataset ships a **per-sequence background image** (`CAVIARDATA2/BACKGROUNDS/bg_<sequence>.ppm`), and the page explains that "there are several people in the video sequence that are not boxed because **they do not move** over the course of the sequence". The project's stated application is "City centre surveillance: … these cities have video cameras already installed" — the installed-camera setting this paper models. Measured values for every downloaded sequence are in `../results/camera_motion_v2_1.json` and every one is checked against the 0.1 % threshold by the analysis. |
| 2 | **per-frame ground truth** | Hand-labelled CVML XML per sequence: `<frame number="…"><objectlist><object id="…"><box xc yc w h/>`, plus `orientation`, `appearance` and a role/movement/context/situation hypothesis list. Centre-based boxes, 0-based frame numbers. |
| 3 | **published frame rate** | "half-resolution PAL standard (384 x 288 pixels, **25 frames per second**)", stated for both sites. |
| 4 | **readable terms permitting research use and publication of derived figures** | Verbatim from the data page: *"All data is publicly available and on this page they can be downloaded in MPEG2 format or split into JPEGs. If you publish results using the data, please acknowledge the data as coming from the EC Funded CAVIAR project/IST 2001 37540, found at URL: http://homepages.inf.ed.ac.uk/rbf/CAVIAR/ . **Usability is Creative Commons BY-SA**"*. CC BY-SA permits derivative works and their publication, with attribution and share-alike, and — unlike the NC licences — does not restrict the purpose. This is the criterion MOT17Det fails. |
| 5 | **≥ 10 independent clips** | INRIA lobby: **28** sequences with JPEG archives, 27 of them with ground truth. Lisbon: **59** sequence folders; the analysis uses the *along-corridor* (`…cor`) view only, because the `…front` view is a time-synchronised second camera on the **same** physical event and including both would break the independence the video-level bootstrap assumes. |
| 6 | **machine-downloadable** | Plain HTTPS, no challenge page, no login: `Walk1_jpg.tar.gz` returns HTTP 200, 12 965 850 bytes; `wk1gt.xml` returns HTTP 200, 1 490 491 bytes. Downloaded by `scratchpad/dl_caviar.sh`; per-file sizes in `../results/dataset_manifest_v2_1.json`. |

**Both sites are in the primary analysis.** They are different buildings, different cameras,
different scene geometry and different traffic, and the results are reported per site as well
as pooled.

## 0b. Viewpoint: a description, not a gate

Measured from the hand annotation alone:

| Site | Boxes | Median `h/w` | Per-sequence median range | Median annotated person area |
|---|---|---|---|---|
| CAVIAR-INRIA (lobby) | 38 552 | **0.71** | 0.52 - 0.93 | 725 px² in a 384×288 frame |
| CAVIAR-LISBON (corridor) | 132 673 | **2.68** | 2.12 - 3.21 | larger, oblique |

Seen obliquely a standing person is taller than wide; seen from above they are not. The lobby
camera is a wide-angle lens looking down, the corridor camera looks along the floor.

**An earlier version of this screen used that number as a gate and excluded the lobby. The
gate is withdrawn.** Protocol §11 (Amendment 2′) records why in full; in short, the evidence
for it compared annotated *people* against what turned out to be a **static false positive**:
at the lobby the detector's recall against the annotation at IoU >= 0.3 is 0.000-0.097
(median 0.008), its precision 0.000-0.107, and 25-83 % of all its detections fall in a single
10×10 px cell, in every one of its 27 sequences. The low detection rate there is the detector's real performance on that
viewpoint and scale, so removing the site would have been selection on an outcome.

What the site actually shows is an **operational-design-domain** finding, and it is reported
as one: an off-the-shelf COCO detector, unmodified, recalls almost none of the people a human
annotator marks in a wide-angle overhead view at this scale. That is worth more to an
assurance argument than a clean second corpus would have been.

**Cost and benefit.** The primary analysis now rests on two sites and 53 sequences rather
than one site and 26 --- comfortably past the ten-cluster bar the audit's blocker B2 raised
against MOT17Det's seven --- with URFD on the include-censored axis as the contrast corpus.
The price is that pooled numbers mix a detector-bound regime with a schedule-bound one, which
is why every table reports the sites separately.

## 2. PETS2009 — **REJECTED on criterion 6**

Not machine-downloadable on 2026-09-21. Every address that the literature points at either
fails to resolve or returns 404:

| URL | Result |
|---|---|
| `http://www.cvg.reading.ac.uk/PETS2009/a.html` | connection failed (000) |
| `http://ftp.cs.rdg.ac.uk/PETS2009/` | connection failed (000) |
| `https://cs.binghamton.edu/~mrldata/pets2009` | 404 |
| `https://motchallenge.net/data/PETS2009/` | 404 |

⚠ **AUTHOR ACTION A-C1** — if a working PETS2009 mirror is known, it is a genuinely separate
corpus (different site, different annotators) and would strengthen condition (i) of the venue
rule. It is not needed for the run to proceed: CAVIAR's two sites already give two
independent static scenes.

## 3. MOT20 — **REJECTED on criterion 4**

MOT20 is static and crowded, and would have been a reasonable technical fit. It is hosted by
MOTChallenge, and **MOTChallenge publishes no licence or terms of use anywhere a client can
read them** — the same gap recorded as author action A-D1 for MOT17Det (`DATA_SOURCES_V2.md`
§1). Adding a second corpus with the same unresolved question would double the exposure
rather than reduce it. Excluded until A-D1 is answered.

## 4. What happens to MOT17Det

- **The four moving sequences (05, 10, 11, 13) leave the primary analysis.** The decision
  rests on the camera attribute published by the benchmark, corroborated by the measurement
  of §0 — **not** on any result computed from them. The V2.0 run that included them is kept
  in full, under its own name, and is reported in the supplementary together with the
  per-sequence event counts, so the change is visible rather than silent.
- **The three static sequences (02, 04, 09) are kept only as a secondary stratum**, never
  pooled into the primary, and only while A-D1 is unanswered rather than answered "no". They
  contribute 26 uncensored events across 3 videos — too few clusters to carry a claim, which
  is exactly why they are a stratum and not a corpus.
- Nothing is deleted. `results_v2_0/` holds the complete V2.0 result set.

## 5. Unchanged exclusions

VIRAT (used by another manuscript in this portfolio) and anything from PPE-Unified, Deep3,
AwP, #4, #5, AAP, T30 or #34 — excluded by prompt rule 2.1 and CP-B0, as before.
