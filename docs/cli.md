# CLI reference

Run `pbb COMMAND --help` for current options. Human output uses Rich; `--json` prints one machine-readable value and exits nonzero on failure.

Targets may be snapshot references (`@2` or `s_abc:@2`), unique CSS/XPath selectors, or exact semantic names. Ambiguity is an error. `pbb tabs`, `pbb tab INDEX`, and `pbb tab close INDEX` manage persistent tabs. `pbb snapshot --selector '#main' --max-elements 50 --max-chars 5000` creates a bounded focused Snapshot v2. Navigation waits for `domcontentloaded`, not unbounded `networkidle`.

`pbb close` closes the browser and daemon in v0.1. A subsequent command requires `pbb start`.

