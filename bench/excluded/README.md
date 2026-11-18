# Excluded modules

## inflection (MIT)
Dropped after pilot 2. 169 of its 175 surviving mutants (human tests: 222 killed / 175 survived)
are in `_irregular`, a helper that runs only at import time to build the plural/singular tables.
mutmut cannot kill mutants of import-time-only code, so no test suite can score well here;
excluding that function the human tests would score about 97%. Kept for the record, not scored.
