#!/usr/bin/env python3
"""build_bib_v2.py -- generate 02_Manuscript/refs.bib for V2 from live Crossref.

Same contract as V1 build_bib.py (checklist C5: every reference carries a DOI or a
resolvable URL on the rendered page; nothing is hand-typed; the script exits
non-zero if any DOI fails to resolve, so a broken reference cannot reach the
manuscript silently).  The list below is the V2 list: the reliability-community
literature the desk reject said was missing, plus the V1 entries that are still
relevant, minus the ones the V2 case study made unnecessary.

Run:  python build_bib_v2.py --out ../../02_Manuscript/refs.bib
"""
from __future__ import annotations

import argparse
import sys
import time

import build_bib as B

# key -> DOI, grouped as they appear in the manuscript.
DOI_REFS = {
    # --- delay-time / periodic inspection: the parent literature -----------------
    "christer1984delay": "10.1057/jors.1984.80",
    "christer1987delay": "10.1057/jors.1987.54",
    "baker1994delay": "10.1016/0377-2217(94)90234-8",
    "wang2012delayreview": "10.1016/j.ress.2012.04.004",
    "flage2014imperfect": "10.1016/j.ress.2013.11.009",
    "scarf2019random": "10.1016/j.ejor.2019.04.042",
    "zhang2021fixedschedule": "10.1016/j.ress.2020.107402",
    "hybrid2024multistage": "10.1016/j.ress.2023.109629",
    "protection2025imperfect": "10.1016/j.ress.2025.110798",
    # --- safety instrumented systems with demands of finite duration -------------
    "innal2010pfd": "10.1243/1748006XJRR278",
    "jin2011sis": "10.1016/j.ress.2010.11.007",
    "liu2011demandmode": "10.1016/j.jlp.2010.08.014",
    "liu2013teststrategy": "10.1016/j.ress.2013.06.035",
    "hokstad2014demandrate": "10.1016/j.ress.2014.03.001",
    "alizadeh2018redundant": "10.1016/j.ress.2017.11.011",
    "eisinger2021alldemand": "10.1016/j.ress.2021.107457",
    "xie2021prolonged": "10.1016/j.ress.2021.107975",
    "oilgas2021maintenance": "10.1016/j.ress.2021.107545",
    "sil2025competing": "10.1016/j.ress.2025.111025",
    "hazard2026allmodes": "10.1016/j.ress.2025.111620",
    # --- conservative / zero-failure demonstration -------------------------------
    "littlewood1997stopping": "10.1109/32.637384",
    "bishop2011formalism": "10.1109/TSE.2010.67",
    "bishop2017profile": "10.1016/j.ress.2016.08.019",
    "bishop2020bound": "10.1016/j.ress.2020.107060",
    # --- dot 2c: heterogeneity, and claims made under a distribution over p -----
    "vaupel1979frailty": "10.2307/2061224",
    "littlewood2013conservative": "10.1109/tse.2013.35",
    "zhao2020operational": "10.1016/j.infsof.2020.106393",
    # --- machine learning at the target venues -----------------------------------
    "paterson2025amlas": "10.1016/j.ress.2025.111311",
    "chelouati2023gsn": "10.1016/j.ress.2022.108933",
    "xu2021mlreview": "10.1016/j.ress.2021.107530",
    "xu2023piml": "10.1016/j.ress.2022.108900",
    "chen2024npp": "10.1016/j.ress.2024.110266",
    "wang2024trust": "10.1016/j.ress.2024.110008",
    "ships2025acceptance": "10.1016/j.ress.2025.110810",
    "alarmfatigue2026": "10.1016/j.ress.2025.111890",
    "trel2023relabel": "10.1109/TR.2023.3298685",
    "trel2025ads": "10.1109/TR.2025.3561455",
    "trel2025brake": "10.1109/TR.2025.3563384",
    "trel2026grade": "10.1109/TR.2026.3704288",
    "risa2024mlreliability": "10.1111/risa.14666",
    "zhao2020safety": "10.1007/978-3-030-54549-9_16",
    "dong2023reliability": "10.1145/3570918",
    "diemert2023ailevels": "10.1007/978-3-031-40953-0_34",
    "tarrisse2021locks": "10.3850/978-981-18-2016-8_661-cd",
    # --- duty cycling as a known phenomenon outside the reliability venues -------
    "zhu2011dutycycle": "10.1007/s11276-011-0397-9",
    # --- corpora and detector -----------------------------------------------------
    "dendorfer2021motchallenge": "10.1007/s11263-020-01375-2",
    "kwolek2014urfd": "10.1016/j.cmpb.2014.09.005",
    "list2004cvml": "10.1109/ICPR.2004.1334335",
    "goyette2014cdnet": "10.1109/CVPRW.2014.126",
    "cuevas2016lasiesta": "10.1016/j.cviu.2016.08.005",
    "ren2017fasterrcnn": "10.1109/TPAMI.2016.2577031",
    "howard2019mobilenetv3": "10.1109/ICCV.2019.00140",
    # --- method -------------------------------------------------------------------
    "clauset2009powerlaw": "10.1137/070710111",
    "vuong1989lr": "10.2307/1912557",
}

OVERRIDES = {
    "zhao2020safety": {"booktitle": "Computer Safety, Reliability, and Security (SAFECOMP 2020), "
                                    "Lecture Notes in Computer Science 12234",
                       "publisher": "Springer"},
    "diemert2023ailevels": {"booktitle": "Computer Safety, Reliability, and Security (SAFECOMP 2023), "
                                         "Lecture Notes in Computer Science 14181",
                            "publisher": "Springer"},
    "tarrisse2021locks": {"booktitle": "Proceedings of the 31st European Safety and Reliability "
                                       "Conference (ESREL 2021)",
                          "publisher": "Research Publishing, Singapore"},
    "goyette2014cdnet": {"booktitle": "IEEE Conference on Computer Vision and Pattern Recognition "
                                      "Workshops (CVPRW)"},
    "howard2019mobilenetv3": {"booktitle": "IEEE/CVF International Conference on Computer Vision "
                                           "(ICCV)"},
    "list2004cvml": {"booktitle": "17th International Conference on Pattern Recognition "
                                  "(ICPR)"},
}

MANUAL = r"""
@misc{iec61508,
  author       = {{International Electrotechnical Commission}},
  title        = {{IEC 61508:2010 --- Functional safety of electrical/electronic/programmable electronic safety-related systems, Parts 1--7}},
  year         = {2010},
  edition      = {2},
  url          = {https://webstore.iec.ch/publication/5517}
}

@misc{iec615086,
  author       = {{International Electrotechnical Commission}},
  title        = {{IEC 61508-6:2010 --- Part 6: Guidelines on the application of IEC 61508-2 and IEC 61508-3}},
  year         = {2010},
  edition      = {2},
  url          = {https://webstore.iec.ch/publication/5520}
}

@misc{iso13849,
  author       = {{International Organization for Standardization}},
  title        = {{ISO 13849-1:2023 --- Safety of machinery: Safety-related parts of control systems, Part 1: General principles for design}},
  year         = {2023},
  url          = {https://www.iso.org/standard/73481.html}
}

@misc{iso13855,
  author       = {{International Organization for Standardization}},
  title        = {{ISO 13855:2024 --- Safety of machinery: Positioning of safeguards with respect to the approach of the human body}},
  year         = {2024},
  url          = {https://www.iso.org/standard/82357.html}
}

@misc{isotr5469,
  author       = {{International Organization for Standardization and International Electrotechnical Commission}},
  title        = {{ISO/IEC TR 5469:2024 --- Artificial intelligence: Functional safety and AI systems}},
  year         = {2024},
  howpublished = {Technical Report},
  url          = {https://www.iso.org/standard/81283.html}
}

@misc{iso8800,
  author       = {{International Organization for Standardization}},
  title        = {{ISO/PAS 8800:2024 --- Road vehicles: Safety and artificial intelligence}},
  year         = {2024},
  howpublished = {Publicly Available Specification},
  url          = {https://www.iso.org/standard/83303.html}
}

@misc{ul4600,
  author       = {{Underwriters Laboratories}},
  title        = {{ANSI/UL 4600 --- Standard for Safety for the Evaluation of Autonomous Products}},
  year         = {2023},
  edition      = {3},
  url          = {https://www.shopulstandards.com/ProductDetail.aspx?UniqueKey=35953}
}

@misc{hawkins2021amlas,
  author       = {Hawkins, Richard and Paterson, Colin and Picardi, Chiara and Jia, Yan and Calinescu, Radu and Habli, Ibrahim},
  title        = {Guidance on the Assurance of Machine Learning in Autonomous Systems ({AMLAS})},
  year         = {2021},
  howpublished = {arXiv preprint arXiv:2102.01564},
  url          = {https://arxiv.org/abs/2102.01564}
}

@misc{braband2020sil,
  author       = {Braband, Jens and Sch{\"a}be, Hendrik},
  title        = {On Safety Assessment of Artificial Intelligence},
  year         = {2020},
  howpublished = {arXiv preprint arXiv:2003.00260},
  url          = {https://arxiv.org/abs/2003.00260}
}

@misc{caviar,
  author       = {{CAVIAR project (EC IST 2001 37540)}},
  title        = {{CAVIAR} Test Case Scenarios: video clips and hand-labelled ground truth},
  year         = {2004},
  howpublished = {EC Funded CAVIAR project/IST 2001 37540, Creative Commons BY-SA},
  url          = {http://homepages.inf.ed.ac.uk/rbf/CAVIAR/}
}

@misc{milan2016mot16,
  author       = {Milan, Anton and Leal-Taix{\'e}, Laura and Reid, Ian and Roth, Stefan and Schindler, Konrad},
  title        = {{MOT16}: A Benchmark for Multi-Object Tracking},
  year         = {2016},
  howpublished = {arXiv preprint arXiv:1603.00831},
  url          = {https://arxiv.org/abs/1603.00831}
}

@misc{torchvision,
  author       = {{TorchVision maintainers and contributors}},
  title        = {{TorchVision}: {PyTorch}'s Computer Vision library},
  year         = {2016},
  howpublished = {Software, BSD-3-Clause},
  url          = {https://github.com/pytorch/vision}
}
"""


COMBINING = {0x0300: "`", 0x0301: "'", 0x0302: "^", 0x0303: "~", 0x0304: "=",
             0x0306: "u", 0x0307: ".", 0x0308: '"', 0x030A: "r", 0x030B: "H",
             0x030C: "v", 0x0327: "c", 0x0328: "k", 0x0323: "d", 0x0331: "b"}
SINGLE = {"ı": r"{\i}", "ł": r"{\l}", "Ł": r"{\L}", "ø": r"{\o}", "Ø": r"{\O}",
          "æ": r"{\ae}", "Æ": r"{\AE}", "œ": r"{\oe}", "Œ": r"{\OE}",
          "å": r"{\aa}", "Å": r"{\AA}", "ß": r"{\ss}", "đ": r"{\dj}",
          "Đ": r"{\DJ}", "–": "--", "—": "---", "’": "'", "‘": "`",
          "“": "``", "”": "''", " ": " ", " ": " ", "×": r"$\times$",
          "°": r"$^\circ$", "µ": r"$\mu$", "−": "-"}


def latexify(s: str) -> str:
    """Turn a Crossref string into plain LaTeX with no character above U+007F.

    IEEEtran is loaded without inputenc and has no slot for a *combining* mark,
    so a name like Bak{\\i}r or Schaebe has to arrive as an accent command.
    """
    import unicodedata
    out = []
    for ch in unicodedata.normalize("NFD", s):
        o = ord(ch)
        if o < 128:
            out.append(ch)
        elif o in COMBINING and out:
            base = out.pop()
            acc = COMBINING[o]
            out.append("\\%s{%s}" % (acc, base) if acc.isalpha()
                       else "\\%s%s" % (acc, ("{%s}" % base) if len(base) == 1 else base))
        elif ch in SINGLE:
            out.append(SINGLE[ch])
        else:
            nfc = unicodedata.normalize("NFC", ch)
            out.append(SINGLE.get(nfc, "?"))
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../../02_Manuscript/refs.bib")
    args = ap.parse_args()

    B.OVERRIDES = OVERRIDES
    entries, failed = [], []
    for key, doi in DOI_REFS.items():
        try:
            m = B.fetch(doi)
            entries.append(latexify(B.to_bibtex(key, m)))
            print(f"  ok   {key:28s} {doi}")
        except Exception as exc:                       # noqa: BLE001
            failed.append((key, doi, repr(exc)))
            print(f"  FAIL {key:28s} {doi}  {exc}", file=sys.stderr)
        time.sleep(0.2)

    if failed:
        print(f"\n{len(failed)} DOI(s) did not resolve -- refs.bib NOT written.",
              file=sys.stderr)
        return 1

    header = ("% GENERATED by build_bib_v2.py from live Crossref metadata.\n"
              "% Do not edit by hand: re-run the script instead.\n"
              "% Every DOI below resolved through api.crossref.org at generation time.\n\n")

    def write(path, entries_txt):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(header)
            fh.write("\n".join(entries_txt))
            fh.write("\n% --- no DOI assigned: standards, software and preprints, "
                     "cited by official URL ---\n")
            fh.write(MANUAL)

    write(args.out, entries)

    # IEEEtran.bst does not print a `doi` field but does print `url`.  Checklist C5
    # asks for an identifier on the *rendered* page, so the two-column wrapper gets a
    # second bib in which every DOI is additionally expressed as a resolvable URL.
    out2 = args.out.replace("refs.bib", "refs_trel.bib")
    entries2 = []
    for e in entries:
        doi = None
        for line in e.splitlines():
            s = line.strip()
            if s.startswith("doi "):
                doi = s.split("=", 1)[1].strip().strip("{},")
        if doi:
            e = e.rstrip()[:-1].rstrip().rstrip(",")
            e += f",\n  {'url':<12} = {{https://doi.org/{doi}}}\n}}\n"
        entries2.append(e)
    write(out2, entries2)

    n = len(entries) + MANUAL.count("@")
    print(f"\nwrote {args.out} and {out2}: {len(entries)} DOI entries + "
          f"{MANUAL.count('@')} URL-only entries = {n} references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
