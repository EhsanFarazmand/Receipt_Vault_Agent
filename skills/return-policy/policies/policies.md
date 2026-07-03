# Per-merchant policy reference (resource tier)

Loaded only when the `return-policy` or `price-protection` branch is reached —
the "resources" level of progressive disclosure. Keep this table honest and
sourced from public store policies; it mirrors `app/data_sources.py`.

| Merchant  | Return window | Price-protection window | Support domain |
| :-------- | :------------ | :---------------------- | :------------- |
| Target    | 90 days       | 14 days                 | target.com     |
| Costco    | 365 days      | 30 days                 | costco.com     |
| Apple     | 14 days       | 14 days                 | apple.com      |
| Amazon    | 30 days       | 7 days                  | amazon.com     |
| Best Buy  | 15 days       | 15 days                 | bestbuy.com    |
| Walmart   | 90 days       | (none)                  | walmart.com    |
| _default_ | 30 days       | (none)                  | —              |

Notes:
- Electronics often carry a shorter window than the store default (e.g. Target
  electronics 30 days). Prefer the item-category window when known.
- Holiday/extended windows are ignored here for determinism in the demo.
