# Expected results

Verified 2026-10-24 in a clean virtual environment built only from
`requirements.txt` (Python 3, pinned: `cryptography==46.0.5`,
`jwcrypto==1.5.6`, `pydantic==2.12.5`, `sd-jwt==0.10.4`, `rfc8785==0.1.4`,
`jsonschema==4.26.0`, `pytest==9.1.1`).

```
24 passed, 0 skipped        (test_matrix.py 15, test_latest_jwt.py 7,
                             test_reissuance.py 2)
```

## Matrix (run_matrix.py)

| Case | Approach A (id/totals/line_items) | Approach B (full signed state) |
|---|---|---|
| T0 no change | accept → dest_1 | accept → dest_1 |
| T1 destination dest_1→dest_2, same totals | **accept → order to dest_2** | reject (`fulfillment`) |
| T2 option standard→express, same price | **accept** | reject |
| T2b option change + total change | reject | reject |
| T3a consent change in complete *request* | accept | accept |
| T3b consent change in *session state* | accept | reject (`buyer`) |
| T4 volatile metadata only | accept | accept |
| T5 no mandate (AP2 negotiated) | reject | reject |
| T6 revised checkout B + fresh mandate for B | accept → dest_2 | accept → dest_2 |
| NC1 tampered embedded checkout | reject (signature) | reject (signature) |
| NC2 expired mandate | reject | reject |
| NC3 mandate for a different checkout | reject | reject |

## Latest-JWT branches (run_latest_jwt.py)

For both T1 and T2 — signature valid and mandate valid in all rows:

| Case | Latest-JWT match | UCP-only (A) | With AP2 latest rule |
|---|---|---|---|
| (i) state changes, no replacement signed checkout issued | yes (vacuous) | accept | accept |
| (ii) new signed checkout issued, old mandate presented | **no** | accept | **reject** |
| (iii) new signed checkout + fresh mandate | yes | accept | accept |

Case (i) is a verifier-robustness exercise only: the audit did not
establish that a no-response change to platform-selected fulfillment
state is a protocol-permitted transition (see README, finding 2).

## Same-state reissuance (run_reissuance.py)

```
sig1 verifies: True    sig2 verifies: True
jws equal: False       checkout_jwt equal: False    checkout_hash equal: False
semantic state equivalent (A and B): True
latest-JWT match: False  ->  UCP-only decision: accept;
                             with AP2 latest rule: reject
```

## Schema observations

- Fixture checkout: 0 validation errors against the official composed
  schemas (AP2 mandate, fulfillment, buyer consent) at the pinned UCP
  commit.
- `merchant_authorization` matches the official schema regex.
- A real SD-JWT+KB `checkout_mandate` presentation does **not** match the
  official schema regex, while verifying cryptographically — a pattern
  mismatch, not invalid cryptography (upstream issue #599).
