"""make_numbers_tex.py -- Topic 35 / V2.

Renders every number the manuscript is allowed to quote into
02_Manuscript/numbers.tex as a LaTeX macro (checklist C6: no number is typed
into the prose).  Sources, in order of precedence:

    results/numbers_v2.json            the case study
    results/comparison_numbers_v2.json VIEC 3
    results/model_mc_validation.json   the Monte-Carlo check of the algebra
    results/protocol_v2_freeze.json    the protocol hash and timestamp
    file hashes of the released tables

Anything directional in the prose -- "higher than", "three times", "rejects" --
is emitted from here too, as a word, so that a change in the data changes the
sentence rather than leaving it stale.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib

EVAL = pathlib.Path(__file__).resolve().parents[1]
RESULTS = EVAL / "results"
OUT = EVAL.parent / "02_Manuscript" / "numbers.tex"


def load(name, required=True):
    p = RESULTS / name
    if not p.exists():
        if required:
            raise SystemExit(f"missing {p}; run the pipeline first")
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "not-generated"


def tex_int(x):
    """Thin-space thousands separator, the LaTeX-safe way."""
    s = f"{int(round(float(x))):,}".replace(",", "\\,")
    return s


def tex_num(x, dp=4):
    if x is None:
        return "n/a"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if not math.isfinite(v):
        return "n/a"
    if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e5):
        m, e = f"{v:.2e}".split("e")
        return f"${m}\\times 10^{{{int(e)}}}$"   # macros are used in text, so $...$
    return f"{v:.{dp}f}".rstrip("0").rstrip(".") if dp else f"{v:.0f}"


def pct(x, dp=1):
    return "n/a" if x is None else f"{100.0 * float(x):.{dp}f}"


def main():
    mc = load("model_mc_validation.json")
    fz = load("protocol_v2_freeze.json")
    # The numbers in this paper were produced under V2.1, so that is the
    # protocol the data-availability statement has to identify; the V2 hash is
    # kept beside it because the release ships both files.
    fz21 = load("protocol_v2_1_freeze.json", required=False)
    N = load("numbers_v2.json", required=False)
    C = load("comparison_numbers_v2.json", required=False)
    H = load("numbers_v2_2.json", required=False) or {}

    M = {}

    # ---- the Monte-Carlo check of the algebra (Section 3, Appendix B)
    M["numMCcells"] = tex_int(mc["n_cells"])
    M["numMCper"] = tex_int(mc["n_per_cell"])
    M["numMCevents"] = tex_int(mc["n_events"])
    M["numMCmaxerr"] = tex_num(mc["max_abs_err"], 5)
    M["numMCnfail"] = tex_int(mc["n_fail"])
    M["numseedmodel"] = str(mc["seed"])          # a seed, not a quantity: no separators

    # ---- provenance
    M["numprotocolsha"] = fz["sha256"]
    M["numprotocolfrozen"] = fz["frozen_at_utc"].replace("T", " ").replace("+00:00", " UTC")
    M["numeventscsvsha"] = sha(RESULTS / "events_v2.csv")
    if fz21:
        M["numprotocolshasuperseded"] = M.get("numprotocolsha", "")
        M["numprotocolsha"] = fz21["sha256"]
        M["numprotocolfrozen"] = fz21["frozen_at_utc"]

    def put(key, macro, fmt=tex_num, *a, **k):
        if key in N:
            M[macro] = fmt(N[key], *a, **k) if fmt is not tex_str else tex_str(N[key])

    def tex_str(x):
        return str(x)

    # ---- corpora and protocol
    for key, macro, fmt in [
        ("n_mot17_sequences", "numnmotseqs", tex_int),
        ("n_mot17_frames", "numnmotframes", tex_int),
        ("n_urfd_sequences", "numnurfdseqs", tex_int),
        ("n_urfd_fall_sequences", "numnurfdfall", tex_int),
        ("n_urfd_adl_sequences", "numnurfdadl", tex_int),
        ("n_urfd_frames", "numnurfdframes", tex_int),
        ("n_zones", "numnzones", tex_int),
        ("n_channels_mot17", "numnchannels", tex_int),
        ("n_events_primary", "numnevents", tex_int),
        ("n_events_censored", "numneventscensored", tex_int),
        ("bootstrap_reps", "numbootreps", tex_int),
        ("seed", "numseed", str),
        ("n_events_urfd_fall", "numneventsurfdfall", tex_int),
        ("n_events_urfd_adl", "numneventsurfdadl", tex_int),
        ("xcorpus_n", "numxcorpusn", tex_int),
        ("xcorpus_inside", "numxcorpusinside", tex_int),
    ]:
        if key in N:
            M[macro] = fmt(N[key])

    if "urfd_fps_mean" in N:
        M["numurfdfps"] = tex_num(N["urfd_fps_mean"], 2)
        M["numurfdfpsmin"] = tex_num(N["urfd_fps_min"], 2)
        M["numurfdfpsmax"] = tex_num(N["urfd_fps_max"], 2)
    if "mot17_fps_values" in N:
        vals = N["mot17_fps_values"]
        M["numotfpslist"] = ", ".join(str(int(float(v))) for v in vals)

    # ---- duration law, in seconds
    for key, macro in [("D_q05_seconds", "numDqZeroFive"), ("D_q25_seconds", "numDqTwoFive"),
                       ("D_median_seconds", "numDmedian"), ("D_q75_seconds", "numDqSevenFive"),
                       ("D_q95_seconds", "numDqNineFive"), ("D_mean_seconds", "numDmean"),
                       ("D_max_seconds", "numDmax")]:
        if key in N:
            M[macro] = tex_num(N[key], 2)

    # ---- p_hat and beta.  V2.1 writes one tag per corpus that is actually in
    # play, so the tags are discovered rather than enumerated.
    import re as _re

    def tag_of(s):
        """A TeX macro name may contain letters only."""
        return _re.sub(r"[^A-Za-z]", "", s.replace("CAVIAR-", "")).lower()

    for key in list(N):
        if key.startswith("p_hat_") and not key.endswith(("_lo", "_hi")):
            tag = tag_of(key[len("p_hat_"):])
            M[f"numphat{tag}"] = tex_num(N[key], 3)
            for suf in ("lo", "hi"):
                if f"{key}_{suf}" in N:
                    M[f"numphat{tag}{suf}"] = tex_num(N[f"{key}_{suf}"], 3)
        if key.startswith("n_active_frames_"):
            M["numnactive" + tag_of(key[len("n_active_frames_"):])] = tex_int(N[key])
        if key.startswith("n_clusters_"):
            M["numnclusters" + tag_of(key[len("n_clusters_"):])] = tex_int(N[key])

    # ---- V2.1 corpus and protocol facts
    for key, macro, fmt in [
        ("n_seq_CAVIAR-INRIA", "numnseqinria", tex_int),
        ("n_seq_CAVIAR-LISBON", "numnseqlisbon", tex_int),
        ("caviar_fps", "numcaviarfps", lambda x: tex_num(x, 0)),
        ("static_threshold_pct_diag", "numstaticthresh", lambda x: tex_num(x, 2)),
        ("n_channels_primary", "numnchannelsprimary", tex_int),
        ("gap_merge_s", "numgapmerge", lambda x: tex_num(x, 2)),
        ("pct_events_short", "numpcteventsshort", lambda x: tex_num(x, 1)),
        ("pct_events_edge_flicker", "numpcteventsedgeflicker", lambda x: tex_num(x, 1)),
        ("n_events_urfd_include", "numneventsurfdinclude", tex_int),
        ("p_hat_urfd_include", "numphaturfdinclude", lambda x: tex_num(x, 3)),
        ("urfd_M_T2", "numurfdMTtwo", lambda x: tex_num(x, 4)),
        ("urfd_band_T2", "numurfdbandTtwo", str),
        ("n_events_mot17_static", "numneventsmotstatic", tex_int),
        ("n_caviar_rejected", "numncaviarrejected", tex_int),
        ("aspect_CAVIAR-INRIA", "numaspectinria", lambda x: tex_num(x, 2)),
        ("aspect_CAVIAR-LISBON", "numaspectlisbon", lambda x: tex_num(x, 2)),
        # Amendment 2': the detector audit, per corpus
        ("gt_match_iou", "numgtmatchiou", lambda x: tex_num(x, 1)),
        ("gt_area_px_CAVIAR-INRIA", "numgtareainria", lambda x: tex_int(round(x))),
        ("gt_area_px_CAVIAR-LISBON", "numgtarealisbon", lambda x: tex_int(round(x))),
    ]:
        if key in N:
            M[macro] = fmt(N[key])

    # ---- Amendment 2': the detector audit and the GT-matched alarm mode
    if "audit_grid" in N:
        M["numauditgridx"] = tex_int(N["audit_grid"][0])
        M["numauditgridy"] = tex_int(N["audit_grid"][1])
    for tag in ("inria", "lisbon", "mot17static", "urfd"):
        mtag = tag_of(tag)          # macro names must be letters only
        for field, macro in (("recall", "numrecall"), ("precision", "numprec"),
                             ("top_cell_share", "numtopcell"),
                             ("top_cluster_share", "numtopclust"),
                             ("top_cluster_frame_share", "numtopclustframe")):
            for kind in ("min", "max", "median"):
                k = f"{field}_{kind}_{tag}"
                if k in N:
                    M[macro + kind + mtag] = tex_num(N[k], 3)
                    if field in ("top_cell_share", "top_cluster_share"):
                        pre = ("numtopcellpct" if field == "top_cell_share"
                               else "numtopclustpct")
                        M[pre + kind + mtag] = tex_num(100.0 * N[k], 0)
        if f"n_audit_sequences_{tag}" in N:
            M["numnaudit" + mtag] = tex_int(N[f"n_audit_sequences_{tag}"])
        for key, pre in (("n_static_fp", "numnstaticfp"),
                         ("n_static_fp_in_zone", "numnstaticfpinzone"),
                         ("n_persistent_cluster", "numnpersist"),
                         ("n_persistent_in_zone", "numnpersistinzone")):
            if f"{key}_{tag}" in N:
                M[pre + mtag] = tex_int(N[f"{key}_{tag}"])
        if f"p_hat_{tag}_gtmatched" in N:
            M["numphat" + mtag + "gtmatched"] = tex_num(N[f"p_hat_{tag}_gtmatched"], 3)
        if f"miss_T1p0_{tag}_gtmatched" in N:
            M["nummissmeasTone" + mtag + "gtmatched"] = tex_num(
                N[f"miss_T1p0_{tag}_gtmatched"], 3)

    # ---- both alarm rules side by side, straight from the released CSV so the
    # any_box column is generated rather than retyped
    import csv as _csv
    amf = RESULTS / "alarm_mode_v2_1.csv"
    if amf.exists():
        for r in _csv.DictReader(open(amf, encoding="utf-8")):
            if r["corpus"] == "pooled" and r["scope"] != "primary":
                continue
            tag = tag_of(r["corpus"].replace("CAVIAR-", "")
                         .replace("MOT17Det-", "mot17"))
            for col, pre, dp in (("p_hat_any_box", "numphat", 3),
                                 ("miss_T1_any_box", "nummissmeasTone", 3),
                                 ("miss_Thalf_any_box", "nummissmeasThalf", 3),
                                 ("alarms_per_hour_Thalf_any_box",
                                  "numalarmsphThalf", 0),
                                 ("alarms_per_hour_T1_any_box",
                                  "numalarmsphTone", 0)):
                v = r.get(col)
                try:
                    M[pre + tag + "anybox"] = tex_num(float(v), dp)
                except (TypeError, ValueError):
                    pass
            for col, pre, dp in (("alarms_per_hour_Thalf_gt_matched",
                                  "numalarmsphThalf", 0),
                                 ("alarms_per_hour_T1_gt_matched",
                                  "numalarmsphTone", 0)):
                v = r.get(col)
                try:
                    M[pre + tag + "gtmatched"] = tex_num(float(v), dp)
                except (TypeError, ValueError):
                    pass

    # ---- dot 2c: the heterogeneous-p layer -------------------------------
    for tag in ("pooled", "inria", "lisbon"):
        mt = tag_of(tag)
        for key, pre, dp in (("pe_mean", "numpemean", 3),
                             ("pe_sd", "numpesd", 3),
                             ("pe_beta_conc", "numpeconc", 2),
                             ("miss_measured_T1p0", "nummeasTone", 3),
                             ("het_lovo_T1p0", "numhetlovoTone", 3),
                             ("het_lovo_beta_T1p0", "numhetlovobetaTone", 3),
                             ("hom_lovo_T1p0", "numhomlovoTone", 3),
                             ("het_plugin_T1p0", "numhetpluginTone", 3),
                             ("hom_beta_T1p0", "numhombetaTone", 3)):
            k = f"{key}_{tag}"
            if k in H and H[k] is not None:
                try:
                    M[pre + mt] = tex_num(float(H[k]), dp)
                except (TypeError, ValueError):
                    pass
        if f"pe_frac_zero_{tag}" in H:
            M["numpezeropct" + mt] = tex_num(100.0 * float(H[f"pe_frac_zero_{tag}"]), 1)
        for key, pre in (("inside_hom", "numinsidehom"),
                         ("inside_homlovo", "numinsidehomlovo"),
                         ("inside_lovo", "numinsidelovo"),
                         ("inside_lovobeta", "numinsidelovobeta"),
                         ("inside_plugin", "numinsideplugin"),
                         ("n_periods", "numnperiods"),
                         ("n_periods_informative", "numnperiodsinf"),
                         ("inside_informative_hom", "numinsideinfhom"),
                         ("inside_informative_lovo", "numinsideinflovo"),
                         ("inside_informative_lovobeta", "numinsideinflovobeta")):
            k = f"{key}_{tag}"
            if k in H:
                M[pre + mt] = tex_int(H[k])
        # the ceiling the beta-factor model cannot pass: 1 - p_hat
        ph = N.get(f"p_hat_{tag}") if N else None
        if ph is not None:
            M["numqhat" + mt] = tex_num(1.0 - float(ph), 4)
            M["numqhatpct" + mt] = tex_num(100.0 * (1.0 - float(ph)), 1)
    for tag in ("inria", "lisbon"):
        mt = tag_of(tag)
        for key, pre, dp in (("gap_frac_zero_min", "numgapzeromin", 1),
                             ("gap_frac_zero_max", "numgapzeromax", 1),
                             ("gap_sd_min", "numgapsdmin", 3),
                             ("gap_sd_max", "numgapsdmax", 3)):
            k = f"{key}_{tag}"
            if k in H and H[k] is not None:
                v = float(H[k])
                M[pre + mt] = tex_num(100.0 * v if dp == 1 else v, dp)
        for key, pre in (("gap_nevents_min", "numgapnmin"),
                         ("gap_nevents_max", "numgapnmax")):
            if f"{key}_{tag}" in H:
                M[pre + mt] = tex_int(H[f"{key}_{tag}"])
    for key, macro, fmt in [
        ("lovo_videos_T0p5", "numlovovideos", tex_int),
        ("lovo_inside_T0p5", "numlovoinsideThalf", tex_int),
        ("lovo_inside_hom_T0p5", "numlovoinsidehomThalf", tex_int),
        ("lovo_inside_T1p0", "numlovoinsideTone", tex_int),
        ("lovo_inside_hom_T1p0", "numlovoinsidehomTone", tex_int),
        ("lovo_medabs_T1p0", "numlovomedabsTone", lambda x: tex_num(x, 3)),
        ("lovo_medabs_hom_T1p0", "numlovomedabshomTone", lambda x: tex_num(x, 3)),
        ("het_mc_cells", "numhetMCcells", tex_int),
        ("het_mc_max_abs_err", "numhetMCmaxerr", lambda x: tex_num(x, 5)),
        ("boot_video_reps", "numbootvideo", tex_int),
    ]:
        if key in H and H[key] is not None:
            M[macro] = fmt(H[key])
    # the design side of the same layer
    for key, macro, fmt in [
        ("dispersion_concentration", "numdispconc", lambda x: tex_num(x, 2)),
        ("dispersion_penalty_shortest_p99", "numdisppenshort",
         lambda x: tex_num(x, 1)),
        ("dispersion_penalty_T1_p99", "numdisppenTone", lambda x: tex_num(x, 2)),
        ("band_shortest_hom_p99", "numbandshorthom", str),
        ("band_shortest_disp_p99", "numbandshortdisp", str),
        ("pfd_shortest_hom_p99", "numpfdshorthom", lambda x: tex_num(x, 6)),
        ("pfd_shortest_disp_p99", "numpfdshortdisp", lambda x: tex_num(x, 6)),
        ("kmax_sil1_hom_p99", "numkmaxhom", lambda x: tex_num(x, 3)),
        ("kmax_sil1_disp_p99", "numkmaxdisp", lambda x: tex_num(x, 3)),
        ("gain_staggered_T1_disp_p99", "numgainstagdisp", lambda x: tex_num(x, 2)),
        ("gain_staggered_T1_hom_p99", "numgainstaghom", lambda x: tex_num(x, 2)),
    ]:
        if C and key in C and C[key] is not None:
            M[macro] = fmt(C[key])

    # ---- the static/moving separation the threshold sits in
    stat = [N[f"motion_{s}"] for s in ("MOT17-02", "MOT17-04", "MOT17-09")
            if f"motion_{s}" in N]
    mov = [N[f"motion_{s}"] for s in ("MOT17-05", "MOT17-10", "MOT17-11", "MOT17-13")
           if f"motion_{s}" in N]
    if stat and mov:
        M["numMOTmotionstaticmin"] = tex_num(min(stat), 3)
        M["numMOTmotionstaticmax"] = tex_num(max(stat), 3)
        M["numMOTmotionmovingmin"] = tex_num(min(mov), 3)
        M["numMOTmotionmovingmax"] = tex_num(max(mov), 3)
        M["numMOTmotiongap"] = tex_num(min(mov) / max(stat), 0)

    # ---- miss validation and bridge, per invocation period
    tags = {"0p5": "Thalf", "1.0": "Tone", "1p0": "Tone", "2.0": "Ttwo", "2p0": "Ttwo",
            "0p2": "Tfifth", "0p1": "Ttenth", "5p0": "Tfive", "3p0": "Tthree"}
    for k, v in N.items():
        for pre, macro in (("miss_measured_T", "nummissmeas"), ("miss_model_T", "nummissmodel"),
                           ("miss_lo_T", "nummisslo"), ("miss_hi_T", "nummisshi"),
                           ("M_T", "numM"), ("gain_staggered_T", "numgainstag"),
                           ("gain_independent_T", "numgainindep")):
            if k.startswith(pre) and not k.endswith("_band"):
                t = k[len(pre):]
                if t in tags:
                    M[macro + tags[t]] = tex_num(v, 4)
        if k.startswith("M_T") and k.endswith("_band"):
            t = k[len("M_T"):-len("_band")]
            if t in tags:
                M["numband" + tags[t]] = str(v)

    # ---- comparison numbers (VIEC 3)
    for k, v in C.items():
        if k.startswith("amlas95_pfd_T"):
            t = k[len("amlas95_pfd_T"):]
            if t in tags:
                M["numamlaspfd" + tags[t]] = tex_num(v, 4)
        if k.startswith("amlas95_band_T"):
            t = k[len("amlas95_band_T"):]
            if t in tags:
                M["numamlasband" + tags[t]] = str(v)
        if k.startswith("amlas95_floorshare_T"):
            t = k[len("amlas95_floorshare_T"):]
            if t in tags:
                M["numamlasfloorshare" + tags[t]] = pct(v)
    for key, macro, fmt in [("sis_pfd_ref", "numsispfd", lambda x: tex_num(x, 6)),
                            ("sis_band_ref", "numsisband", str),
                            ("sampling_pfd_ref", "numsamplingpfd", lambda x: tex_num(x, 4)),
                            ("sampling_band_ref", "numsamplingband", str),
                            ("sampling_over_sis_ref", "numsamplingoversis",
                             lambda x: tex_int(x)),
                            ("zf_nreq_eps1e2_delta05", "numzfnreq", tex_int),
                            ("zf_band_per_frame", "numzfbandframe", str),
                            ("zf_band_per_event", "numzfbandevent", str),
                            ("zf_hours_frames", "numzfhoursframe", lambda x: tex_num(x, 2)),
                            ("zf_hours_events", "numzfhoursevent", lambda x: tex_num(x, 2))]:
        if key in C:
            M[macro] = fmt(C[key])

    # ---- detector provenance.  These are identifiers, not quantities, and they
    # contain characters LaTeX treats as markup.
    def tex_escape(s):
        s = str(s)
        for a, b in (("\\", r"\textbackslash{}"), ("_", r"\_"), ("&", r"\&"),
                     ("%", r"\%"), ("#", r"\#"), ("$", r"\$"), ("{", r"\{"),
                     ("}", r"\}"), ("^", r"\^{}"), ("~", r"\~{}")):
            s = s.replace(a, b)
        return s

    for key, macro in [("detector", "numdetector"), ("torch_version", "numtorch"),
                       ("torchvision_version", "numtorchvision"),
                       ("detector_weights_sha256", "numweightssha")]:
        if key in N:
            M[macro] = tex_escape(N[key])

    # ---- the beta curve at the two lags the prose names
    bp = RESULTS / "beta_lag_curve_v2.csv"
    if bp.exists():
        import csv as _csv
        # per site as well as pooled: since both sites became primary the
        # pooled lag-1 estimate is a mixture of two regimes and the ceiling
        # argument has to be made on the site it applies to
        with open(bp, encoding="utf-8") as fh:
            for r in _csv.DictReader(fh):
                if r["corpus"] == "pooled" or r["lag"] != "1":
                    continue
                mt = tag_of(r["corpus"].replace("CAVIAR-", ""))
                M["numbetalagone" + mt] = tex_num(r["beta_hat"], 2)
                M["numPtwolagone" + mt] = tex_num(r["p_both_miss"], 4)
                M["numbetaadmissible" + mt] = (
                    "outside" if float(r["beta_hat"]) > 1.0 else "inside")
                M["numnlagsbetaover" + mt] = str(sum(
                    1 for x in _csv.DictReader(open(bp, encoding="utf-8"))
                    if x["corpus"] == r["corpus"] and float(x["beta_hat"]) > 1.0))
        with open(bp, encoding="utf-8") as fh:
            for r in _csv.DictReader(fh):
                if r["corpus"] != "pooled":
                    continue
                if r["lag"] == "1":
                    M["numbetalagone"] = tex_num(r["beta_hat"], 2)
                    M["numaclagone"] = tex_num(r["autocorr"], 2)
                    M["numPtwolagone"] = tex_num(r["p_both_miss"], 4)
                    # the admissible ceiling for P2 under the two-point mixture
                    if "p_hat_pooled" in N:
                        M["numqhat"] = tex_num(1.0 - float(N["p_hat_pooled"]), 4)
                    M["numbetalagoneadmissible"] = (
                        "outside" if float(r["beta_hat"]) > 1.0 else "inside")
                    M["numnlagsbetaover"] = str(sum(
                        1 for x in _csv.DictReader(
                            open(bp, encoding="utf-8"))
                        if x["corpus"] == "pooled" and float(x["beta_hat"]) > 1.0))
                elif r["lag"] == "30":
                    M["numbetalagthirty"] = tex_num(r["beta_hat"], 2)
                    M["numaclagthirty"] = tex_num(r["autocorr"], 2)

    # ---- the retained V1 change-detection analysis (protocol section 9).
    # Frozen results, not recomputed; routed through here so that C6 holds for
    # them too and no V1 figure is retyped into the V2 prose.
    v1p = RESULTS.parent / "results_v1" / "numbers.json"
    if v1p.exists():
        V = json.loads(v1p.read_text(encoding="utf-8"))
        for key, macro, fmt in [("n_videos_cdnet", "numvOnecdnetvideos", tex_int),
                                ("n_videos_lasiesta", "numvOnelasiestaseqs", tex_int),
                                ("n_events_pooled", "numvOneevents", tex_int),
                                ("M_K15_pooled", "numvOneMKfifteen", lambda x: tex_num(x, 4)),
                                ("M_K15_sens_ratio", "numvOnesensratio",
                                 lambda x: tex_num(x, 2)),
                                ("M_K15_sens_min", "numvOnesensmin", lambda x: tex_num(x, 4)),
                                ("M_K15_sens_max", "numvOnesensmax", lambda x: tex_num(x, 4))]:
            if key in V:
                M[macro] = fmt(V[key])

    lines = ["% numbers.tex -- GENERATED by make_numbers_tex.py.  Do not edit by hand.",
             "% Every numeric value in the manuscript is \\input from here (checklist C6).",
             f"% protocol {fz['sha256']}",
             ""]
    for k in sorted(M):
        lines.append("\\newcommand{\\%s}{%s}" % (k, M[k]))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json.dump(M, open(RESULTS / "numbers_tex_manifest.json", "w"), indent=1)
    print(f"wrote {OUT} with {len(M)} macros")


if __name__ == "__main__":
    main()
