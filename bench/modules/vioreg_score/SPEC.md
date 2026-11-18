# vioreg.score spec

Module docstring of the vioreg project.

---

Score VIO runs: results/<seq>/run*.tum + EuRoC ground truth -> results/<seq>.json.

    python -m vioreg.score --seqs MH_01_easy --out results

JSON contract (frozen; exact key sets are enforced by tests/test_score.py):
  sequence, backend, vio_commit, image_digest, harness_commit, config_hash, runs,
  align, skip_s, ate{ok,rmse,median,max,coverage,n}, rpe{ok,rmse,delta_s},
  per_run_ate_rmse, wall_s

Aggregation across runs (VIO is not bit-deterministic, so a sequence may have N runs):
  * per_run_ate_rmse lists every run's ATE RMSE in numeric run order (run1, run2, ...,
    run10); a run that could not be scored contributes null.
  * The top-level ate AND rpe blocks are copied from ONE representative run: the median
    run by ATE RMSE. For an even N the upper median (the worse of the two middle runs)
    is used, so ties break toward failing. Taking both blocks from the same run keeps
    them mutually consistent (they describe a run that actually happened, not a blend
    of medians of different runs). err.npy holds that run's per-pose ATE error.
  * Fail closed: if ANY run is missing, empty, unreadable or has ok=false, or there are
    zero runs, or ground truth is unreadable, or any of the four provenance fields is
    missing, then ate.ok = rpe.ok = false, the other ate/rpe fields are null (the key
    set never changes), the reason goes to stderr, and the exit code is 1. A median
    must never hide a crashed run.
  * wall_s is the median per-run VIO wall-clock time, read from run<k>.wall_s sidecars
    written by the runner. It is null unless every run has one; it is a performance
    figure, not a correctness one, so its absence does not fail the result.

Provenance:
  vio_commit     label vioreg.ov_ref of the Docker image (== /ws/OV_COMMIT, built in)
  image_digest   the REGISTRY digest of the pinned image (vioreg/image_ref.py): --image must be
                 <repo>@sha256:<64 hex> (default $IMAGE, else docker/IMAGE_REF), and
                 `docker image inspect` RepoDigests must list it. Never the local image ID,
                 which changes per rebuild and per Docker storage mode. Unconfirmed -> None
                 -> the result fails closed. Every run<k>.image_digest sidecar written by
                 the runner must equal it, like config_hash.
  harness_commit `git rev-parse HEAD`, with "-dirty" appended if src/, configs/ or
                 scripts/ have any uncommitted change, untracked files included
  config_hash    sha1 over estimator_config.yaml + the kalibr IMU and IMU-camera yamls it
                 references, contents concatenated in sorted file-name order (see
                 vioreg/config_hash.py). Read from the config baked into the image, or from
                 --config-dir when the runs mounted an override. Every run<k>.config_hash
                 sidecar written by scripts/run_sequence.sh must equal it, or the result
                 fails closed: a run made with another config is never scored under this hash.