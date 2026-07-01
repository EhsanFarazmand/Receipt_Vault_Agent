# Per-Merchant Return & Price-Protection Policies

> Bulky resource — loaded **only** when the `return-policy` skill reaches the lookup
> step (progressive disclosure keeps this out of context until needed). Figures are
> illustrative defaults for the demo; a production build cites each merchant's
> published policy and versions this file. Mirrored in code at
> `app/domain/merchant_policies.py`.

| Merchant | Return window (days) | Price-protection (days) | Notes |
| :--- | ---: | ---: | :--- |
| Target | 90 | 14 | Most items 90d; some electronics 30d. |
| Costco | 365 | 30 | Very generous; most items no deadline, electronics 90d. |
| Apple | 14 | 14 | Standard 14-day return and price match. |
| Amazon | 30 | 7 | 30-day returns; limited price-protection. |
| Best Buy | 15 | 15 | 15-day standard; longer for members. |
| Walmart | 90 | 0 | 90-day returns; no formal price-protection. |
| Home Depot | 90 | 0 | 90-day returns on most items. |
| **(unknown)** | 30 | 0 | Conservative default when the merchant is not listed. |
