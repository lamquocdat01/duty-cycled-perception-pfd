# What each script is, and which ones the V2 manuscript depends on

Topic 35 / B2 · 2026-09-21 · **updated for V2.1 (đợt 2b)**

> **V2.1 changed the corpus, not the method.** The primary corpus is now the two static
> CAVIAR sites; the moving-camera sequences that dominated V2.0 are out. New on the path:
> `camera_motion_check.py` (the static gate), `caviar_v2_1.py` (loading and zones),
> `run_case_study_v2_1.py` (driver), `make_zone_overlays.py`, `make_v20_v21_table.py`.
> `run_case_study.py` is kept unchanged as the record of the V2.0 run. The model, the
> Monte-Carlo check, the detector, its weights and every threshold are untouched, so a
> V2.0 → V2.1 difference cannot be a model or detector difference.

## The V2.1 pipeline, in order

| # | Script | Note |
|---|---|---|
| 0 | `camera_motion_check.py` | measures global frame-to-frame motion per sequence → `results/camera_motion_v2_1.json`. Run this **before** the detector: it is what decides which sequences are admissible |
| 1 | `model_v2.py` | unchanged |
| 3 | `run_detector.py --only=caviar` | reads JPEGs straight out of each `frames.tar.gz`; checks the V2.1 protocol hash |
| 5 | `run_case_study_v2_1.py` | primary / contrast / stratum kept apart; flicker diagnostics; cluster counts. **Amendment 2' additions:** the detector-quality audit for every corpus -> `results/detector_quality_v2_1.csv`, both alarm rules -> `alarm_mode_v2_1.csv`, and the site aspect ratios as description only -> `site_aspect_v2_1.csv`. There is no viewpoint gate: `viewpoint_gate()` and `viewpoint_gate_v2_1.csv` are gone |
| 5b | `heterogeneity_v2_2.py` | **đợt 2c.** Reads the events the V2.1 driver produced and adds one model layer: the event-to-event law of `p`. Writes `het_validation_v2_2.csv` (measured against five predictors, per site), `lovo_v2_2.csv` (per-video leave-one-video-out), `pe_distribution_v2_2.csv`, `pe_by_gap_v2_2.csv` (is the dispersion an artefact of the event convention?) and `numbers_v2_2.json`. Checks the frozen protocol hash and asserts that every measured miss rate equals the V2.1 run's, cell by cell |
| 9a | `make_zone_overlays.py` | the frozen zones drawn over frame 0 of each site |
| 9b | `make_v20_v21_table.py` | the withdrawn run, per sequence, and the eight headline quantities side by side |

---

## The original V2 listing follows

## The V2 pipeline, in the order it runs

| # | Script | Reads | Writes |
|---|---|---|---|
| 1 | `model_v2.py` | nothing | `results/model_mc_validation.{csv,json}` — the closed forms of the model and the Monte-Carlo check that has to pass before anything downstream uses them |
| 2 | `novelty_sweep_v2.py` | Crossref / OpenAlex / Semantic Scholar | `../../03_Dossier/sweep/*.json` — read-only; no number from it enters the manuscript |
| 3 | `run_detector.py` | `data/MOT17Det/`, `data/URFall/` | `results/det_cache/*.npz`, `results/detector_manifest.json`. Aborts unless `EVAL_PROTOCOL_V2.md` still hashes to the frozen value |
| 4 | `case_study_v2.py` | *(library)* | — estimator definitions, transcribed from the frozen protocol |
| 5 | `run_case_study.py` | the caches | `results/events_v2.csv`, `miss_validation_v2.csv`, `p_beta_v2.csv`, `beta_lag_curve_v2.csv`, `bridge_v2.csv`, `far_latency_v2.csv`, `latency_v2.csv`, `sensitivity_v2.csv`, `cross_corpus_v2.csv`, `urfd_by_kind_v2.csv`, `numbers_v2.json` |
| 6 | `comparison_v2.py` | `events_v2.csv` | `cmp_amlas_v2.csv`, `cmp_sis_v2.csv`, `cmp_zerofailure_v2.csv`, `comparison_numbers_v2.json` |
| 7 | `build_bib_v2.py` | Crossref, live | `../../02_Manuscript/refs.bib`, `refs_trel.bib`. Exits non-zero if any DOI fails to resolve |
| 8 | `make_numbers_tex.py` | the JSONs above | `../../02_Manuscript/numbers.tex` — **every** number in the manuscript |
| 9 | `make_tables_v2.py` | the CSVs above | `../../02_Manuscript/body/tab_*.tex`, `05b_case_numbers.tex`, `abstract_numbers.tex` — every table, and the two paragraphs whose *directional words* are generated |
| 10 | `make_figures_v2.py` | the CSVs above | `../../02_Manuscript/figs/*.png` |
| 11 | `../../02_Manuscript/render_check.py` | both wrappers | builds and checks the rendered PDFs |

Re-running the whole chain from step 3 reproduces every number in the paper. Steps 1, 2, 3
and 7 touch the network or take minutes; 5, 6, 8, 9, 10 are seconds.

## Retained V1 scripts

These are the frozen V1 tools, kept because the change-detection corpora keep their V1 role
(the *shape* of `F_D` and the size of the convention sensitivity, in frames — protocol §9).

| Script | Status in V2 |
|---|---|
| `duration_law_public.py` | retained, unchanged — CDnet2014 / LASIESTA event extraction |
| `bridge_tables.py` | retained, unchanged — the V1 bridge tables. **Not on the V2 path.** In V1 it also wrote `numbers.tex`; in V2 that file is written by `make_numbers_tex.py`, so none of the literature values hard-coded in `bridge_tables.py` can reach the V2 manuscript |
| `check_simulation.py` | retained — the V1 simulation check, superseded for the model by `model_v2.verify_model_mc()` |
| `build_bib.py` | retained **only for its helper functions** (`fetch`, `to_bibtex`, `esc`), which `build_bib_v2.py` imports. Its own `DOI_REFS` list is V1's and is not used |
| `make_supplementary.py`, `make_graphical_abstract.py` | retained for VIỆC 7; not run yet |

**Independence check (CP-B0).** No script on the V2 path reads anything from Deep3, AwP, #4,
#5, AAP, T30, #34 or PPE-Unified, and no such number is in `numbers.tex`. The only inputs are
two public video corpora, the public COCO detector weights, and published work with a DOI.

## Determinism

Seed `20260921` everywhere. The detector runs in `eval()` mode with no stochastic layer, so
the per-frame verdicts are deterministic; the bootstrap and the Monte-Carlo are seeded. The
one thing that is *not* byte-reproducible is the PDF, because pdfTeX embeds a timestamp — so
any check that compares PDF bytes must re-hash after a rebuild.
