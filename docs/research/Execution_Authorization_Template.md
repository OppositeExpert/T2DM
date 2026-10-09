# Final Scientific Execution Authorization Record

**Template only — copying or completing this file does not itself authorize a run**

## Study identity

- Protocol/SAP version:
- Frozen repository commit and tag:
- Source archive SHA-256:
- Final experiment-profile SHA-256:
- Executable analysis-configuration SHA-256:
- Requirements lock SHA-256:
- Dataset-configuration SHA-256:
- Raw-data SHA-256 for each authorized dataset:
- Concealed split-manifest path:
- Concealed split-manifest SHA-256:
- Final holdout seed:
- Authorized models and panels:
- Authorized primary/secondary metrics and comparison families:
- Completed authorization-record path and SHA-256 (record after signatures):

## Preflight confirmations

- [ ] Novelty review independently approved.
- [ ] Endpoint and claim hierarchy approved.
- [ ] Development ablation decision report approved.
- [ ] Selective-prediction and subgroup decisions approved.
- [ ] Threshold policy, practical margins, and suppression rules approved.
- [ ] TRIPOD+AI and PROBAST+AI reviews completed or assigned with an approved
      post-run completion plan.
- [ ] The concealed manifest contains no persisted outcome information.
- [ ] The manifest hash was independently verified.
- [ ] No final outcomes, counts, prevalence, or performance have been inspected.
- [ ] Backup, log capture, and immutable-archive locations are prepared.

## Authorization scope

- Authorized datasets:
- Authorized commands/profile names:
- Maximum permitted executions:
- Authorized execution window:
- Operator:
- Independent artifact reviewer:
- Conditions that invalidate the run:

## Approvals

- Principal investigator/supervisor: __________________ Date/time: __________
- Statistical/methodological reviewer: _______________ Date/time: __________
- Execution operator acknowledgment: _________________ Date/time: __________

## Post-execution record

- Actual start/end time:
- Exit status:
- Output study identifiers:
- Output manifest/archive SHA-256:
- Deviations or infrastructure failures:
- Rerun authorized: No / Yes, with separate signed justification

The configured `final_authorization_record` must point to a completed, reviewed,
versioned copy—not this blank template—and the protocol must contain its exact
SHA-256. Final execution remains denied until the raw-data, concealed-manifest,
authorized-seed, executable-analysis, and authorization-record hashes agree with
the locked profile and all human approvals.
