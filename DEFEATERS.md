# Defeaters, and how each is treated

This is Table 15 of the article, in full. The two-column build of the paper points
here because the journal's page limit does not allow the table to be embedded; the
single-column build carries it inline. Nothing is added or removed.

"Open" means the assurance pattern **records** the weakness rather than resolving it.

| Defeater | Attacks | Treatment |
|---|---|---|
| Detector failures correlated within an event, and events that differ from each other | G3.2 | **Measured; largely treated.** Within-event dependence is modelled as an IEC 61508-6 `beta`-factor and estimated per lag; the residual it leaves is accounted for by a second layer, an event-to-event law of `p` (model section, heterogeneous p), whose direction is fixed by convexity rather than fitted. The argument must carry that law, not a mean, because the mean is the optimistic end (model section, heterogeneous p). |
| Event process synchronises with the invocation clock | G2, G3 | Not removable by assertion. the fixed-phase subsection gives the price: with a locked phase the structural miss of a short event ranges over `[0,1]`. The pattern therefore requires phase randomisation or period dithering as a **design obligation**, with evidence. |
| Duration law drifts after certification | G3.1 | `M(K)` is re-estimated from the field event log; a performance indicator fires when the empirical sub-`K` mass leaves its certified interval. |
| `n_req` unreachable in the available time | G3 | Stated, not hidden: either accept a larger epsilon, shorten `K` until the floor fits, or add a staggered second channel (the redundancy subsection). |
| Event definition is a convention | C2, G3.1 | Sensitivity across conventions is reported (the sensitivity subsection) and the chosen convention is frozen in the context node. The merge tolerance additionally needs a **physical** justification --- the reaction time --- and where that cannot be sourced, the argument must say so rather than let a default stand in silently. |
| The camera moves, or is re-aimed after commissioning | C1, G3.1 | **A design and surveillance obligation, not an assumption.** A zone is a region of the scene, so if the camera moves the predicate stops measuring the hazard. The pattern requires evidence that the camera is fixed --- here a measured bound on global frame-to-frame motion (the case-study setup) --- and a field indicator that fires if it changes. The cost of getting this wrong is not subtle: an earlier version of this analysis drew most of its events from moving-camera footage and produced a duration law that described the camera rather than the hazard. |
| Demonstration corpus profile != operational profile | G3 | **Open.** This is the profile-mismatch problem [bishop2017profile]; counting in events narrows it to the duration law but does not remove it. |
| Alarm burden makes the monitor be switched off | G4 | A disabled monitor has miss rate 1. The false-alarm budget is therefore a safety claim, and is measured here rather than assumed [alarmfatigue2026]. |

---

Generated from `02_Manuscript/body/07_assurance.tex` at release time; the paper and
this file cannot disagree because they have one source.
