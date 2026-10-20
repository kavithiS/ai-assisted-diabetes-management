# Risk register (C3, PP1)

| Risk | Level | Mitigation | Owner | Status |
|---|---|---|---|---|
| Ethics not approved (submitted 21/09/2026): no real patient data, no user study | High | Demo data + public South Asian data only; study planned for PP2 | Me + supervisor | Open, waiting |
| Hospital/university data not available (KDU could not share that much data) | High | Own questionnaire after ethics approval; National Hospital permission letters | Me | Open |
| Label is "diagnosed diabetes", users already have diabetes | High | Honest wording ("estimated risk profile"); supervisor email | Me + supervisors | Open |
| Live demo fails (slow laptop, emulator) | High | One-command scripts, phone-window fallback, backup video | Me | Mitigated |
| DHS weights / recommendation wording not clinically reviewed | Medium | Marked "provisional" everywhere; clinician review requested | Me + clinician | Open |
| Lifestyle factors have no real training data | Medium | DHS/recommendations only; synthetic only as pipeline check | Me | Open |
| Latency above 2 s target (median 2.22 s) | Medium | Warm-up; 127.0.0.1 not localhost; load test planned for PP2 | Me | Open |
| C1/C2 contracts not ready | Medium | C3 works standalone; contract proposal written | Team | Open |
| Gateway lacks CORS / auth / HTTPS | Medium | PR notes to the gateway owner; local demo only | Gateway owner | Open |
| Laptop disk nearly full broke builds | Medium | Freed space; never build with the emulator running | Me | Mitigated |
| AI-assisted code I cannot explain | Medium | AI-use log; walk through each file before Q&A | Me | Ongoing |
