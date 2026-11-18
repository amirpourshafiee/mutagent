# vioreg.variance spec

Module docstring of the vioreg project.

---

Run-to-run variance analysis (session S3).

    python -m vioreg.variance --root results/variance --seqs ... --baseline-variant A_serial         --out-dir docs/variance

Per run: ATE and RPE are recomputed with the same score._score_run the scorer uses (so the
numbers are identical to score.py's). Determinism is checked POSE BY POSE (pose_equivalent):
since S3b, file sha1s are only informational, because the recorder's shutdown race can drop
the final pose and make identical estimator output differ as bytes. A failed run (empty / unreadable / ok=false)
is kept with null metrics and its reason.

Outputs:
  baseline.json  per sequence: per-run ATE RMSE, per-run RPE RMSE, per-run ok, align,
                 skip_s, and the four provenance fields from results/<variant>/<seq>.json
                 (the baseline variant only; thresholds are NOT derived here)
  variance.json  per variant x sequence: spread statistics, failures, distinct trajectories
  spread.png     per-sequence strip plot of ATE RMSE per run, one column per variant