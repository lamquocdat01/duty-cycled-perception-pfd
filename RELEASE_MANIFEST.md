# RELEASE_MANIFEST — the allow-list, and the SHA-256 of every file in it

Generated 2026-09-22T06:49:46+00:00 · 64 files · repository `duty-cycled-perception-pfd`, tag `v2.0.0-submission`

Every file published is listed below. Anything not on this list is not in the repository;
`verify_package_trel.py` checks that in both directions.

The identifiers the article's data-availability statement quotes:

- **protocol** `EVAL_PROTOCOL_V2_1.md` — `7432cffcfc7124488e2cd991fbfbf1b10e92674c7e5088dab48da73d96f77efb`
- **event table** `results/events_v2.csv` — `a93c3ef764cc35cf75e8f5e710dd8b6e6ac530a48a6d062329920ce4e55628bf`
- **numbers** `results/numbers_v2.json` — `3dd512320222d3f2b467b01af3c7a93d006563fd35343e1a343eaca8199db6fe`

`results_v1/numbers.json` carries the frozen figures of an earlier change-detection
analysis that the article retains in one subsection; it is included so that every macro
the manuscript uses can be regenerated from this repository alone.

## Deliberately absent

- `results/det_cache/*.npz` — per-frame detector verdicts on third-party video. Rebuilt by
  `code/run_detector.py`; not ours to redistribute.
- the video corpora, their ground truth and any frame imagery. `data/` carries only the two
  screening documents; `.gitignore` blocks the rest of it.
- `render_check.py` and `make_highlights_v2.py`: they belong to the manuscript build, need
  manuscript sources that are not published here, and carry venue-specific strings. Named
  so the omission is visible.
- the manuscript sources and the submission package: this is the code and data release,
  not the paper.

## Files

| File | Bytes | SHA-256 |
|---|---:|---|
| `.gitattributes` | 97 | `06269e4709b2653deeb6abba4177b684ab3a4bb544d37af063710224e7867246` |
| `.gitignore` | 216 | `b0180cc891187a16329fddb3a06861c5e2ba5b780da245a5f5d075346fff6a18` |
| `CITATION.cff` | 910 | `10531fbeeceaf9a210dce0d061d29094bbbe60192e6d565ae5c0202a562e3241` |
| `code/build_bib_v2.py` | 13,569 | `4d0dccf904c1af197dddd5dd3cd7069ebe78317a53f5effac920709dad0c8d46` |
| `code/camera_motion_check.py` | 6,135 | `a2d4cf985790b30390c71feb91d99551112edb393f72567da5c924980a51f77d` |
| `code/case_study_v2.py` | 26,276 | `caa877b8a556a437a4f37d43d29fd053898c58e37e894880413e6f2957fdbdfc` |
| `code/caviar_v2_1.py` | 14,610 | `33802e3ef76f427e9abf349940b8cb1999a9b6d4bb03cae17317844347681f2d` |
| `code/comparison_v2.py` | 13,144 | `dde4751d098cfbc3bd271d11bac31db82f402ab055e3a9a73d3a288052d5741c` |
| `code/heterogeneity_v2_2.py` | 17,592 | `ef3f1c76c59fca345e68ebcd9e15272e75c37988c1171b2df373a203c52e9686` |
| `code/make_figures_v2.py` | 10,408 | `76d73e1e55a9a018a8781c3a8c68229e8e3a783263d6b9f1439d1c0f64b4f7e0` |
| `code/make_numbers_tex.py` | 23,986 | `1839265c06a10e2eb878cd2594a5c8ef1a9ffa92a9ad49779362acfbc8d2dfd8` |
| `code/make_tables_v2.py` | 32,989 | `4833c7c7aeb0bbfc7ba745b40389b09400f6347501447e3c67c56d724ff0219c` |
| `code/make_v20_v21_table.py` | 8,056 | `f97b156eb4a4c2c617c0ad4fd96befb544a95d03319276439abf2734d9bdbce6` |
| `code/make_zone_overlays.py` | 3,093 | `c6a45193b8437f824c11dd9bd8e8779832a935b0a5f3ea9fdb88c2b9e9a69f6c` |
| `code/model_v2.py` | 14,696 | `311c05774c565c9c86ee111696e5d9a1db8e1e83ae019cbcebadbfd7971c5675` |
| `code/README_CODE_V2.md` | 6,043 | `36784dc8815f39bb4360318811b220527f6d8313e05c641cfff51652c72afb1b` |
| `code/run_case_study_v2_1.py` | 25,990 | `6ba85a395caa9dc23e9230782a121c97b74249894f2dc6514b048dc332a0e821` |
| `code/run_detector.py` | 9,903 | `c724342db48cebdabf68ff6f74f0df7ceba895d4bb953f4356bb125d2a0526fe` |
| `data/CORPUS_SCREEN_V2_1.md` | 10,025 | `129dd461ca3672fd23e1c6867840f6c34a6e68f5d52b91a3acbb3b7c7e21f46b` |
| `data/DATA_SOURCES_V2.md` | 9,225 | `02b0f8645eda04eba2293f3ce97ea1e48e3044d4f5287f8368bbd6e86c0499f6` |
| `DEFEATERS.md` | 3,243 | `08ca2d3695d90d9ead6d8b1e648abe7b45de205e910c1595181400a57ed7b1d3` |
| `EVAL_PROTOCOL_V2.md` | 15,025 | `874e7cb4b09c3654ab78b33b493500476eae47662516b8c081cc6064ab570a00` |
| `EVAL_PROTOCOL_V2_1.md` | 20,182 | `7432cffcfc7124488e2cd991fbfbf1b10e92674c7e5088dab48da73d96f77efb` |
| `LICENSE` | 1,350 | `b6329f54b1df128dcdd488c829e176c25efd9ce71173a069d1009af4abd3b3d5` |
| `README.md` | 4,867 | `56d10a40c5b8550702487a287354fc798ddd09c731e6c4963a3d18dc1995e3aa` |
| `requirements.txt` | 99 | `a13b0268fec6be26a8e99bc72038281352449edf5765f8a6530c291d276b74a4` |
| `results/alarm_mode_v2_1.csv` | 1,309 | `6cabd911461cc0b66327aacca0b6408ad853c5886d345127b9bb7a81ea75248b` |
| `results/beta_lag_curve_v2.csv` | 7,192 | `6f05a78ab85a823c1a79efefb59c431d3a11e8c449190a54cc176a60c2d35d51` |
| `results/bridge_v2.csv` | 3,571 | `99172f38701daa1711e2eedc159e0464a450a1b38f0bb3ce75b2590f71c69dfe` |
| `results/camera_motion_v2_1.json` | 17,549 | `5498f0ec2b0284ef68840aa3c75a440ac36e1e1c267a05d62fe838107a240240` |
| `results/clusters_v2_1.csv` | 99 | `5e5b928d720e0c849eb3aef3da0240f84ddc63ce6221cb7b38c43a54cfcb6bdb` |
| `results/cmp_amlas_v2.csv` | 22,795 | `da42387bdb9ea2ca274f2bd1e6e845e9e2b07997013f866340af294ce46b8c45` |
| `results/cmp_dispersion_v2_2.csv` | 6,906 | `e4baaa5433e815910e3c9a3cc9888f3175188bbae55d171d3ca6de7d03f0c436` |
| `results/cmp_sis_v2.csv` | 13,684 | `45fdbfc3a6371c5a0b2e343bd0055445a85191bef0bcb85e16e53e2eb6f23e6f` |
| `results/cmp_zerofailure_v2.csv` | 5,285 | `8245bdd25d2a563e9f849a7dd8fc0a4c5a32d8b8acc8a2c90adcf4a03f7c6bc4` |
| `results/comparison_numbers_v2.json` | 1,660 | `82ba5dab256510ffd2d23d5d1ba610c6fd13b442f6ba568a114509ce65f7b4be` |
| `results/cross_corpus_v2.csv` | 2,329 | `41067f4ba5ec58851ea634812c2d477e7ff618446b5e547b9aa1ddca890e68c1` |
| `results/detector_manifest.json` | 605 | `309554f134b846c90db01b37168131c93211fa68ba69c10c2dc5889c02b4c7d9` |
| `results/detector_quality_v2_1.csv` | 19,941 | `28b4dbcf4c7f25a8a80e6808419d5685faf273e50a80c4ee2857e60d4c5c5dbe` |
| `results/events_v2.csv` | 29,254 | `a93c3ef764cc35cf75e8f5e710dd8b6e6ac530a48a6d062329920ce4e55628bf` |
| `results/far_latency_v2.csv` | 1,296 | `1583d71cd18eeef4e35df1b5014400a8f7e1039a05d3e42b77cd6a3aae42de55` |
| `results/fd_summary_v2.csv` | 756 | `671beb2796cab8c419b4ffc38adf494a7ae1a42701307e6ffabf75581cd52ca6` |
| `results/flicker_v2_1.csv` | 29,391 | `df135981d47ecd17858a4b8738ce96600d1d71c7a4630365111c1b1623db8e71` |
| `results/het_validation_v2_2.csv` | 6,867 | `4cceed8979060731b588e933e629cb0d5f1de09e61d8e5998b7e5bbba3e95900` |
| `results/latency_v2.csv` | 2,339 | `fec89f388818e6938b137b34847337fcd2b3f671dff659d2fa698a9adb891769` |
| `results/lovo_v2_2.csv` | 16,729 | `0f44aa6e5011f1e2ce39730f16a69bdbd0c7f259a4fa513d375b93de984f0f83` |
| `results/miss_validation_v2.csv` | 4,145 | `025776e7ce54a9e8111c39b75086611d23fed268e8b9d50960cbc26db878b16d` |
| `results/model_mc_validation.csv` | 32,003 | `05f8ec5cdf85b075dc7d3e206541b627231832941847ccdbcef484ea4743d09d` |
| `results/model_mc_validation.json` | 362 | `b1e76005dfa3e7c3d677bbfdd7c2f5e5146c8a24755eeb8659102b64024a6f0a` |
| `results/mot17_static_v2_1.csv` | 585 | `e2ee064aa683e20ef4792fe31eaa26427d7b8e11790f1d79ec099b0ef4b62840` |
| `results/numbers_v2.json` | 11,085 | `3dd512320222d3f2b467b01af3c7a93d006563fd35343e1a343eaca8199db6fe` |
| `results/numbers_v2_2.json` | 3,795 | `542275ae733eda513fbd1d5c946c43882b4cb41a9684e48611d9b031fb22541a` |
| `results/p_beta_v2.csv` | 436 | `5c231403cb0987256dd241992a8a97e3c115cec3751c64da39a785499efc8111` |
| `results/pe_by_gap_v2_2.csv` | 858 | `769ed8d0e53aa539c823a6ec901279fc84a5ed1c6fbec7f6addcefbc96e9ea04` |
| `results/pe_distribution_v2_2.csv` | 681 | `eadf3edd1eeb2055547d5e2a21533d7d9b6c24f237f89fb45e96f557ffb63bca` |
| `results/protocol_v2_1_freeze.json` | 2,115 | `6e47cd5af2ffdd4d4323dd755c74c1030938c7e30140e9fb9c709268f7f71047` |
| `results/protocol_v2_freeze.json` | 496 | `785c4f0c502d03b65c03f7ee36104137df20ab3f4ee882ca966e0353f4cf1b9d` |
| `results/sensitivity_v2.csv` | 2,977 | `9c29910937b24d9ef29921abccfb09583768a73b035ac704e63a2cae8ae5186b` |
| `results/site_aspect_v2_1.csv` | 205 | `b4804c2a0bc58f17d339403e3e5cff6dad8d7f87432aed14d73c6c9694078fd3` |
| `results/static_gate_v2_1.csv` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `results/urfd_contrast_v2_1.csv` | 2,035 | `daf09194521dffe24e93ef07bb4ab7905f69c871075f4434b62815835bdb191e` |
| `results/WITHDRAWN_overhead_stratum_v2_1.csv` | 639 | `35c4bc39c88d7633691e89001fbf8b67c2c71646be079fbf839d81005085bfa1` |
| `results/WITHDRAWN_viewpoint_gate_v2_1.csv` | 164 | `f598f79a61b7251cefe8c07fecdf73c1d2e887d74f27df67a39d01708769cd94` |
| `results_v1/numbers.json` | 3,409 | `8ea0144f5ce8b56abdc9d1d5f50a5dc25aeaa2bc114af98243a483059205eda5` |
