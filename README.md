# Duty-cycled machine-learning perception monitors as periodically inspected protection channels

Code, frozen evaluation protocol and derived data for the article

> *Duty-cycled machine-learning perception monitors as periodically inspected protection
> channels: choosing the invocation period and the redundancy architecture.*

A camera-based safety monitor that evaluates one frame in every `K` is a protection system
that inspects its demand periodically. This repository holds everything needed to
reproduce the paper's numbers from the event tables, and everything needed to re-derive
those event tables from the public video corpora.

**Nothing here is a third-party dataset.** No frame, no ground-truth file and no per-frame
detector verdict is redistributed. What is released is the code, the protocol, and tables
derived from the corpora at the event level.

---

## What is in here

| Path | What it is |
|---|---|
| `EVAL_PROTOCOL_V2_1.md` | the **operative** evaluation protocol, frozen before the detector was run, with its amendment log. Its SHA-256 is checked by the analysis on every start. |
| `EVAL_PROTOCOL_V2.md` | the superseded V2 protocol, kept because the amendment log refers to it |
| `code/` | the analysis, in the order it runs (see `code/README_CODE_V2.md`) |
| `data/CORPUS_SCREEN_V2_1.md` | why each corpus was admitted or rejected, with the licence text quoted |
| `data/DATA_SOURCES_V2.md` | where each corpus comes from and under what terms |
| `results/*.csv`, `results/*.json` | every derived table the paper reports, plus the two tables of the run that was **withdrawn** after audit (`WITHDRAWN_*`), kept so the record is complete |
| `DEFEATERS.md` | the assurance argument's defeaters and their treatment, in full |
| `RELEASE_MANIFEST.md` | every released file with its SHA-256, as released at tag `v2.0.0-submission`; since that tag only the title lines of this README and of `CITATION.cff` have changed |

## Reproducing the paper

The pipeline has two halves. The second half is reproducible from this repository alone;
the first needs the video corpora, which you must obtain yourself under their own licences.

**From the event tables (no video needed).** `results/events_v2.csv` is the event-level
table: one row per hazard event, with its duration in frames and seconds, its frame rate,
whether it is boundary-censored, and how many of its frames the detector fired on. From it:

```bash
python code/comparison_v2.py        # design-side tables
python code/make_numbers_tex.py     # every number the manuscript prints
```

**From the corpora (video needed).** Obtain CAVIAR, UR Fall Detection and — if you want the
secondary stratum — MOT17Det, following `data/DATA_SOURCES_V2.md`, and place them under
`data/`. Then:

```bash
python code/camera_motion_check.py      # the static-camera measurement, before anything else
python code/run_detector.py             # caches per-frame verdicts into results/det_cache/
python code/run_case_study_v2_1.py      # events, estimators, the V2.1 tables
python code/heterogeneity_v2_2.py       # the event-to-event law of p, and its tests
```

`results/det_cache/` is deliberately **not** in this repository: it is a per-frame record of
a third-party corpus. `run_detector.py` rebuilds it, which takes a couple of hours on a CPU.

Determinism: seed `20260921` throughout; the detector runs in `eval()` mode with no
stochastic layer. The one thing that is not byte-reproducible is a PDF, because pdfTeX
embeds a timestamp.

## The protocol is enforced, not just published

`code/case_study_v2.py` hashes `EVAL_PROTOCOL_V2_1.md` at every start and refuses to run if
it no longer matches `results/protocol_v2_1_freeze.json`. The protocol was frozen before the
detector was run on the corpus, and both amendments made after that are logged in it with
the reason, the time, and a statement of what had already been computed. One of those
amendments **withdraws** the other; the manuscript says so, and the tables from the
withdrawn version are in `results/WITHDRAWN_*`.

## Licence and attribution

The **code and the derived tables in this repository are MIT-licensed** (`LICENSE`). The
corpora are not ours to license, and the licence each one carries is quoted verbatim in
`data/CORPUS_SCREEN_V2_1.md`.

The primary corpus requires an acknowledgement, which is given here as its terms ask:

> The data come from the **EC Funded CAVIAR project/IST 2001 37540**, found at URL
> <http://homepages.inf.ed.ac.uk/rbf/CAVIAR/>. Usability is Creative Commons BY-SA.

The contrast corpus is the UR Fall Detection dataset (Kwolek & Kepski,
[10.1016/j.cmpb.2014.09.005](https://doi.org/10.1016/j.cmpb.2014.09.005)), used under
CC BY-NC-SA 4.0 for non-commercial academic research. For MOT17Det, used only as a
secondary stratum, **no licence statement could be located** on the benchmark's pages; no
part of it is redistributed here and only aggregate counts derived from it are reported.

## Citing

See `CITATION.cff`.
