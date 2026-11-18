Done: S1-S4 (scaffold, grader, Docker sandbox, agent loop); S5a review (spec scoring, flaky check); S5b benchmark: 4 open-source modules vendored, runner (mutagent.bench) with baselines B0/B2/B3/B4, B0 results for 5 modules in bench/results/b0_all.json.
Next: 4 more fresh modules + the 4 vioreg modules (12 total); then run B2/B3/B4 x3 repeats (est. $15-30, set --max-usd):
  python -m mutagent.bench --out bench/results/run1.json --baselines B2 B3 B4 --repeats 3 --max-usd 20
Caveats to report: open-source group is likely in the model's training data; mutation score on 1 module/run is noise.
