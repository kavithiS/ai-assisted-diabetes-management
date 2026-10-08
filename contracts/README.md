# Contracts

Payloads exchanged between components (and between the gateway and the client) are documented
here. A component never depends on another component's internal code or database schema, only on
its contract.

## Versioning rules

1. Each contract lives in its own folder: `contracts/<contract_name>/`.
2. Each contract has a version `MAJOR.MINOR`, recorded in the contract file and in its changelog.
   - **MINOR**: backwards-compatible changes, such as a new optional field.
   - **MAJOR**: breaking changes, such as removing or renaming a field or changing a type or unit.
     A breaking change gets a new API path version (for example `/v2/...`). The old version stays
     available until every consumer has moved.
3. Every field states its type, unit (for example g, kcal, mmol/L) and whether it is required.
4. Changing a contract requires a PR that touches `contracts/` and is reviewed by **every
   affected member** (producer and all consumers).
5. Contracts describe data shapes only. They make no clinical claims. Outputs are "estimated"
   or "predicted", never "diagnosed".

## Planned contracts

Fields are not defined yet. Each owner proposes theirs in a PR.

| Contract | From | To | Status |
|---|---|---|---|
| `meal_nutrition` | C1 | C2, C3 | Planned |
| `glucose_forecast` | C2 | C3, client | Planned |
| `risk_history` | C3 | C3 (internal; stores past meals and glucose for trend analysis) | Planned |
| `risk_assessment` | C3 | client | Planned |
| `foot_analysis` | C4 service | client | Planned |
| `patient_risk_profile` | client | C3 | Planned |
