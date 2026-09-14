# MLB collection-status correction — independent review

Date: September 14, 2026. **Accepted for the bounded integration and reporting-display deployment gate. No blocking findings remain.** This accepts the collection-status correction and factual release-candidate documentation only; it is not whole-v1.2 release acceptance, a fresh health certification or study closure.

## Exact candidate and authority

Independent reviewer: delegated collection-review agent, separate from the implementation author. Reviewed the uncommitted candidate in `/private/tmp/pops-edge-collection-status` at HEAD `0d8e18248d190a0bf4bf30185ece4427dd371a9f` (PR #51). The coordinating agent freshly fetched main during this review and confirmed origin/main and HEAD equal that revision. All 14 inventory hashes were independently verified before inspection and again before this receipt. The exact reviewed bytes are listed below; this review file is an additional artifact, not part of that inventory.

Applied root AGENTS, methodology/product/architecture authority hierarchy, reporting contract section 6 and acceptance boundaries, existing `operations/PROSPECTIVE_PROJECTION.md` health rules, and the bounded collection-status handoff. Existing accepted reporting/scientific evidence is reused rather than reopening its scope.

The Owner subsequently requested independent review and explicitly authorized commit, PR, merge and deployment if acceptable. That conditional authorization now has an accepted candidate; it supersedes earlier pending-authorization wording in dated candidate artifacts. It does not authorize collector repinning/restarts, provider acquisition, source or scheduler changes, NFL changes, tags, whole-release publication or study closure. A separate integration handoff records the execution boundary.

## Findings and acceptance reasoning

No P0/P1 blockers or required implementation corrections were found.

- The new adapter reads existing sanitized, digest-checked invocation records and invokes only the extracted pure observation rules. It does not run health-report, acquisition, archive reconciliation, checkpoint refresh or an operational write. The extraction retains the original cadence thresholds, skipped-hour grace, failure and supersession logic; the full operational health function retains its existing additional audits.
- Frozen observations have an independent read time and latest completion time. Current invocation blockers, valid completions, skipped cycles and the dated recorded health-check outcome are visible. The wording explicitly declines a fresh overall audit or capture-completeness inference, so invocation success does not confer scientific or operational authority.
- Missing, malformed, inaccessible, future-dated and contradictory observations yield status unavailability, leaving valid scientific display usable. Multiple elapsed hourly skip slots with one detection time remain valid. Historical failures do not permanently poison current invocation status after later valid work under the existing rules.
- Activation continues to reconstruct retained immutable report renderers before publication and retains selected references, last scientific attempt, anchors, packages and verification receipts. The optional status component is restricted to the separate display; the default v3 bytes and v1/v2 dispatch are preserved. Opening executes no refresh. Existing failed/running report notices and historical/live navigation remain intact.
- Offline recovery guidance and supporting guide copies are accessible from both report views. The guidance preserves failures and prospective gaps, and directs bounded manual intervention without granting new collector authority.
- README, CHANGELOG, release plan and operator guide distinguish completed PR #51 activation from this then-local correction and whole-release publication. Their candidate-era gate wording is historical once the separately linked integration record applies. VERSION and NFL are unchanged.

The approved core local workflow is operable. No change to scientific membership, Coverage, provenance, chronology or arithmetic was found. Remaining limits are the accepted frozen/manual operation and existing health semantics, not reasons to expand the PR.

## Independent validation

Used the existing `/Users/tom/pops-edge/venv/bin/python` environment; no dependency installation or provider calls.

- 101 actual tests passed across `tests.test_forecast_reporting_collection`, `tests.test_forecast_reporting_delivery` and `tests.test_forecast_standalone_activation` in the initial run (24.586 seconds). That invocation also mistakenly named a nonexistent `tests.test_forecast_operational_lifecycle` module, producing one loader error rather than a product test failure.
- Corrected the lifecycle module name to `tests.test_pr30_lifecycle`: all 19 tests passed in 1.276 seconds. Thus all 120 actual focused tests passed, including existing lifecycle/health behavior and new frozen-status preservation cases.
- Independently parsed four isolated preview HTML pages and checked all 42 local links; all resolved, with no raw `<pre>` dumps.
- `git diff --check` passed. Exact candidate hashes remained unchanged after review.

The implementation preview receipt's retained acquired-package checks, baseline-v3 byte comparison and original-file preservation checks are supporting evidence, not newly rerun scientific verification. Prior independent 123-test/33-test reporting reviews and 906-test compatibility evidence remain applicable. This review does not claim a fresh complete suite, hosted CI, browser visual inspection or a present production-health assessment. The existing browser restriction was honored.

## Accepted limitations and state changed

Status is a dated local snapshot. Matching the operational directory is an explicit operator responsibility because existing heartbeat records have no namespace field. Concurrent append after the read boundary may visibly degrade status; a later manual refresh is adequate. No new full archive, checkpoint, disk or secondary audit is inferred. Original immutable pages retain historical status wording, and scientific update is followed by a separate display refresh when wanted. Automatic recovery and generalized infrastructure remain deferred.

Review wrote this Markdown receipt and disposable test outputs only; it did not modify implementation, production reports, source archives, operational records, configuration, schedules or external GitHub state. No commit, push, PR, merge or deployment was performed by the reviewer.

## Next authorized gate

Proceed with the separately recorded bounded integration handoff: commit exactly the accepted candidate plus review/integration artifacts, create and merge the PR after its checks, then activate only the reporting display from a clean merged revision. Verify retained scientific state and immutable bytes, recovery/evidence links, status observation date/digest, and the unchanged collector deployment. Record actual merged revision and deployment outcome in a separate completion receipt. Preserve rollback material. Do not represent this acceptance as whole-v1.2 release authorization.

## Reviewed file hashes

| File | SHA-256 |
|---|---|
| `ARCHITECTURE.md` | `d40ff3e556f50291030d4c59c1bf90ec8b1f10a722399096b6741cb6066d979d` |
| `CHANGELOG.md` | `209625fa9dcdec2f81d945bee1d72ee9ca8012640cd551294e3b2418e76a737f` |
| `README.md` | `98e21df8fee7b0f36ba47e87710e7425b7ef7560aef6b9c2bcd5ac4e1b11d8c9` |
| `docs/MLB_COLLECTION_STATUS_HANDOFF_v1.2.0.md` | `c76788f31c4797a68a72a625bb06b25b273e45b50ea40ec8fc5cd8c2d9bbf62a` |
| `docs/MLB_COLLECTION_STATUS_REVIEW_v1.2.0.md` | `1355b670e593fdb51917119f698a46954bea7389ad71b94f84f856fed91310e7` |
| `docs/MLB_REPORTING_DELIVERY_API_v1.2.0.md` | `6b1feeec81e851adf85eb809baa33c47472e114daa2c9250043a02c26374c12d` |
| `docs/RELEASE_PLAN_v1.2.0.md` | `601952a8491a9d40279168cc02f56b745cf7c7ced7bf4eae028bd5d12c5b6950` |
| `forecast_reporting_activation.py` | `3f5e9f2be284192ba22c9ed9335742334ff5b82d08f4755b88ac9330e20d8a03` |
| `forecast_reporting_collection.py` | `43c371ac462541053e6edee5ff578864db13b4239a2817b129510d45f32b4c35` |
| `forecast_reporting_presentation.py` | `bf3a9b9dfec4311fe8b24e3c5841a3194af6d7706e76ee9f2e7d782ce7fcf20d` |
| `forecast_standalone_activation.py` | `2682922737bfc6821645b5921c3844a837e668e4cd0c90517b262ab91df4fcd2` |
| `operate_forecast_reporting.py` | `236ff10f69277402a14dd10c72a56835e1a44ed515425d804ab1bbaeeee89621` |
| `tests/test_forecast_reporting_collection.py` | `eedce352a52646a544ecda374a354de8933ac0b7aefcfd2830e1613bd08709b6` |
| `tests/test_forecast_reporting_delivery.py` | `2dee8ee8bf566f96a0e23f3c27e1380ea74765b082e13225732916ec282a5677` |
