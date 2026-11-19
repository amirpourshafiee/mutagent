# Benchmark modules

Each module: `src/<name>.py` (single file), `SPEC.md`, `human_tests/`, `meta.yaml`.

- `group: fresh` modules are written for this benchmark (no chance the model has seen them).
- `group: open_source` modules are vendored unchanged from permissively licensed projects
  (license file included in each directory). Their `SPEC.md` is the project's public README, and
  `human_tests/` are the project's own tests, with these edits only to make them run standalone
  (listed per module in meta.yaml). The model has very likely seen these projects in training,
  so results on this group are reported separately from the fresh group.
