# Risk register (C3, PP1)

| Risk | Level | Mitigation | Owner | Status |
|---|---|---|---|---|
| Label is "diagnosed diabetes", users already have diabetes | High | Honest wording ("estimated risk profile"); supervisor email sent | Me + supervisors | Open |
| Ethics not approved: no Sri Lankan data, no user study | High | Demo data only; open South Asian data; study planned for PP2 | Me + supervisor | Open |
| Live demo fails (laptop slow, emulator) | High | One-command scripts, phone-window fallback, backup video | Me | Mitigated |
| DHS weights / recommendation wording not clinically reviewed | Medium | Marked "provisional" everywhere; clinician review requested | Me + clinician | Open |
| Lifestyle factors have no real training data | Medium | Used for DHS/recommendations only; synthetic only as pipeline check | Me | Open |
| Latency above 2 s target (median 2.15 s) | Medium | Warm-up; 127.0.0.1 not localhost; load test planned | Me | Open |
| C1/C2 contracts not ready | Medium | C3 works standalone; contract proposal written | Team | Open |
| Gateway lacks CORS / auth / HTTPS | Medium | PR notes to gateway owner; local demo only | Gateway owner | Open |
| Laptop disk nearly full broke builds | Medium | Freed 14 GB; never build with emulator running | Me | Mitigated |
| AI-assisted code I cannot explain | Medium | AI-use log; walk through each file before Q&A | Me | Ongoing |
