# ReturnDesk Benchmark v1.0 - Data Card

Synthetic damaged-delivery claims with known correct outcomes, for testing
claim-handling agents against a written refund policy.

## Summary

- Claims: 1000 (dev 200, test 800, golden 42 from dev)
- Seed: 4060336691 (namespace `returndesk-bench/stephenoke14/mrhills/v1`)
- Labels computed by: `returndesk-rules/1.0 (stephenoke14, mrhills)`
- Policy file SHA-256: `d1dce1168f27f41583b9611ce18cd0622551d6c2a75ac1a78ba1296f3bddf67a`

## How labels are made

Each claim's expected outcome is the result of applying `policy/refund_policy.yaml`
to the claim's true facts with the ReturnDesk rules engine. Systems under test
see only the `input` block; the `truth` block is hidden.

## Categories

| Value | Count | Share |
| --- | --- | --- |
| standard | 500 | 50% |
| boundary | 120 | 12% |
| injection | 120 | 12% |
| manipulation | 100 | 10% |
| conflict | 100 | 10% |
| urgent_invalid | 60 | 6% |

- **standard**: realistic mix of claims.
- **boundary**: one value exactly at or just past a policy limit.
- **conflict**: the message describes different damage from the photo.
- **injection**: a prompt-injection attempt inside the message; must be escalated.
- **manipulation**: a false claim in plain language; the true facts decide.
- **urgent_invalid**: an angry customer with an invalid claim; must be escalated, not rejected.

## Expected outcomes

| Value | Count | Share |
| --- | --- | --- |
| escalate | 486 | 49% |
| refund | 328 | 33% |
| reject | 186 | 19% |

## Limitations

- All data is synthetic. Messages are template-based and less varied than real customers.
- Perception (damage class, confidence) is given as input, so the benchmark tests
  decision-making, not the vision model.
- Labels follow one specific policy; a different policy needs a rebuilt benchmark.

## Rules for use

- Tune prompts and code on **dev** only. Report results on **test**.
- **golden** is a small dev subset for CI checks.
- Do not edit files by hand. Run `--verify` before every experiment.

Built for ReturnDesk by stephenoke14 (mrhills). Licence: CC BY 4.0.
