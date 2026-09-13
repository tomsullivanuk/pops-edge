# Independent acceptance review — frozen reporting source authority

September 13, 2026. **Accepted for slice 1 only. No blocking findings remain.**
This is an independent PM/Chief Architect review by the delegated source-boundary
reviewer, not the implementation author's self-assessment. It does not accept the
full reporting capability, successor scoring, report delivery or v1.2 release.

## Exact candidate and governing scope

Reviewed working-tree additions on `codex/mlb-reporting-source-boundary`, based on
`6b74140cce63243e59722cd6661d24fb2377c6e5` (PR #48 merge; first parent
`1f1c033f7b0250f390aee597f85246cbdeba564c`). No candidate implementation commit
existed at review time. The following SHA-256 values identify the exact accepted
four-file candidate; this review artifact is an additional documentation file.

| Path | SHA-256 |
| --- | --- |
| `forecast_reporting_source.py` | `43af438f320877f6b6e64d3114b64a7af7c597aabad4810421b74d91efd8fc68` |
| `tests/test_forecast_reporting_source.py` | `1de363e3690c9a411d4ab86f188f7415bd054d8ea6c86711f8ae905e6895ece6` |
| `docs/MLB_REPORTING_SOURCE_API_v1.2.0.md` | `b08131e3e333aaf62b50171a199af842df5491bf579d193cac19a40ddbb1ebe3` |
| `docs/MLB_REPORTING_IMPLEMENTATION_SEQUENCE_v1.2.0.md` | `681aeb7939b45e840174de8dbe0809790945c554b1ab48a8b0bd4bafd4c297e1` |

Applied complete root AGENTS.md, the Methodology and Architecture reporting
amendments, [reporting contract](MLB_REPORTING_CONTRACT_v1.2.0.md), the approved
slice-1 must-hold conditions in the local split handoff, and the
[durable sequencing decision](MLB_REPORTING_IMPLEMENTATION_SEQUENCE_v1.2.0.md).
The reviewer inspected the existing namespace integrity, acquisition/session
completion and correction validators, original source replay and singleton
publication implementation independently of the implementation report.

## Acceptance reasoning

Fresh creation inventories the actual complete namespace and verifies unchanged
inventory around source reconstruction. It accepts no historical cutoff argument.
All manifest material remains represented, including failed or non-contributing
entries. Reconstruction derives roots, dependencies, dispositions and graph digest
under the original validators. The adapter gives completion/correction validators
the frozen inventory, so later manifest-last completion with earlier acquisition
chronology cannot change old admission. Current namespace-wide corruption remains
blocking even outside the selected source roots.

Saved verification authenticates against an independently retained boundary ID,
then reconstructs the graph and exact selection from retained inputs. Recomputed
candidate hashes alone do not authenticate omitted inventory. Verification returns
its separately dated receipt without changing the original boundary. The source
adapter offers read primitives only and introduces no collector or archive write
entry point, transport, persistence service, scoring engine or publication stage.

The diff adds four files and changes no existing implementation, constructor,
serialization, identifier, Protocol or legacy validator. Source boundaries remain
derived Analysis without Evidence, Governance, Policy or operational authority.
No false-result, silent population-bias, concealed-failure, chronology, replay or
core offline-workflow blocker was found within this slice's accepted boundary.

## Validation evidence and limitations

The reviewer independently ran:

```text
/Users/tom/pops-edge/venv/bin/python -m unittest \
  tests.test_forecast_reporting_source tests.test_forecast_standalone_publication -q
Ran 26 tests in 6.629s — OK
```

These synthetic tests exercise late completion; legacy completion followed by
correction; complete-inventory omissions with recomputed hashes; independent
selection/dependency reconstruction; foreign mode/namespace/version; chronology;
missing/corrupt non-root inputs; concurrent append and later independent work;
source-file immutability; forbidden network/write/lock interfaces; canonical
input-order/Decimal replay; and legacy publication compatibility.

The reviewer also inspected the implementation-run full regression log,
`planning/SOURCE_SLICE_FULL_TESTS.log`: **856 tests passed in 47.490s**. That is
implementation validation evidence, not a second independently executed full suite.
The existing environment lacked pytest; no dependency installation was performed.

The reviewer's own remote-main read attempt failed on sandbox DNS resolution;
local HEAD and candidate hashes were verified. The primary implementer separately
reported a successful fresh remote-main check using permitted escalated
`git ls-remote`, resolving to the exact base above. That remote check is reported
integrator evidence, not the reviewer's independent observation. Recheck upstream
before integration.

Accepted preconditions remain explicit: the caller supplies a truthful trusted
clock, independently retains the original boundary ID, and retains source storage.
Supplying both a forged boundary and a forged alleged trust anchor does not prove
historical completeness. This offline library deliberately adds no signing service
or durable trust store. Namespace inconsistencies fail visibly; automatic recovery
and uninterrupted freeze availability are not requirements. Synthetic correctness
does not establish real-study completeness or empirical sufficiency.

## State changed and next authorized gate

Review changed only this local Markdown artifact and temporary test fixtures/cache
outputs. No research archive, provider, collector, index, checkpoint, scheduler,
operational state or external GitHub state was changed by the reviewer.

Under the Owner's already recorded authorization, the accepted slice may proceed
through commit, push, PR review resolution and merge with normal integration checks.
Then implement slice 2 against the accepted source API and obtain its separate
independent acceptance review. Slice 1 is not completion of the requested outcome.
Runtime activation is not justified by this unused offline library; the integrator
must record actual deployment applicability without repinning/restarting collection
or claiming a rollout that did not occur. No full-release tag or closure is accepted.
