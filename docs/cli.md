# CLI reference

Run `pbb COMMAND --help` for current options. Human output uses Rich; `--json` prints one machine-readable value and exits nonzero on failure.

Targets may be snapshot references (`@2` or `s_abc:@2`), unique CSS/XPath selectors, or exact semantic names. Ambiguity is an error. Navigation waits for `domcontentloaded`, not unbounded `networkidle`.

`pbb close` closes the browser and daemon in v0.1. A subsequent command requires `pbb start`.

