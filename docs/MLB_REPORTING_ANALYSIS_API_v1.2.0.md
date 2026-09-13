# Offline MLB reporting Analysis API

Slice 2 of the [approved sequence](MLB_REPORTING_IMPLEMENTATION_SEQUENCE_v1.2.0.md),
built on the accepted [source boundary](MLB_REPORTING_SOURCE_API_v1.2.0.md).
Governing authority remains the [reporting contract](MLB_REPORTING_CONTRACT_v1.2.0.md).
This library creates/validates offline analytical values. There is no operational
report-generation command, package publication, current pointer, baseline calculation,
HTML reader, collector activation or study closure.

## Creation and validation

`forecast_reporting_analysis.create_standalone_report_analysis(...)` requires the
actual namespace archive, frozen source, independently retained expected source ID,
one canonical MLB Protocol ID, exact software revision, truthful trusted clock and
`in-progress` or `interim` status. It independently verifies source authority before
computing anything. It does not accept caller-authored opportunities, selected
successes, scores, Coverage categories or earlier report populations.

The result is `StandaloneAnalyticalReport`. `to_json()` is its canonical scientific
serialization. `deserialize_reporting_analysis(...)` dispatches successor types
explicitly; decoding alone is not scientific acceptance. The original V3 decoder
continues to reject successor roots and the successor decoder rejects legacy roots.

`verify_standalone_report_analysis(...)` requires the same independently retained
source ID, saved report and a current trusted clock. It rebuilds the context, complete
Coverage and every analytical reference from pinned original source authority and
compares the exact result and canonical bytes. Missing, extra, foreign, mixed,
rehashed-but-altered or incompatible inputs fail closed. The returned
`ReportVerificationReceipt` has its own actual time; saved report bytes, source
cutoff, computation times and seed never change during verification.

As with source freezing, the caller must supply an actual clock and accurate software
revision. Test clock injection is not permission to invent chronology. Validation
checks exact scientific reconstruction; it is not a signature proving that an
untrusted caller's claimed wall clock or software checkout was genuine. A later
operational adapter must retain the trusted source anchor and initial report bytes.

## Causal identity and actual times

One finalized `StandaloneReportContext` contains an immutable
`StandaloneComputationSpecification`, actual completion time and actual report time.
The specification binds source ID/K, canonical Protocol/design/source/role/domain,
complete cumulative scope, required bounded scope, exact rule references, software
revision and actual computation start. It exists before calculations. Result IDs
and the explicitly versioned bootstrap seed bind that specification. Final report
identity also binds completed context and its actual completion/report timestamps.
This avoids using a future completion clock to choose a bootstrap sample.

`ReportLocalDerivation` and `ReportLocalMeasurement` have successor identities and
exact specification/derivation references. They contain original-constructor
calculation records as **internal arithmetic/validation witnesses**. These are newly
reconstructed from pinned Evidence, never borrowed from earlier source Analysis.
Their `effective_at` and provenance `generated_at` identify **start-of-computation**
within the finalized context's actual computation interval. They do not claim
completion, independent V3 scientific authority or availability at K. Only complete
context-specific reconstruction admits the successor envelope as Analysis. Do not
extract these witnesses into the Evidence archive or submit them as earlier V3
Measurements. Initial computation and later exact verification are distinct actions.

The source verifier also checks availability recorded in source provenance, including
market-series mapping collection and Protocol/classification generation. A future
provenance time cannot enter earlier source authority merely because an enclosing
synthetic bundle claims an earlier acquisition timestamp. This is a reporting-gate
check; no legacy record or acquisition validator is changed.

## Populations, Coverage and statistics

Historical cumulative/bounded scopes retain March 25–September 5, 2026 Eastern,
14,169,600 seconds, open-left/closed-right event-window semantics and independent
strict pre-activation membership. A later K never moves those endpoints. Cumulative
and bounded artifacts have separate identities even when their populations agree.
Known dates outside the governed historical origin are not scored by this report.

Prospective cumulative accounting starts at activation and retains every known
Protocol schedule obligation, including future starts. Eligible denominator means
due and validly eligible; capture-not-yet-due and ineligible remain separate. The
required bounded interval is exactly `(K - 18,000 seconds, K]`, without clamping
at activation. Original eligibility/capture chronology remains independent of K.
No later candle/quote can repair a missed prospective capture.

A private shared Coverage calculation separates K, analytical effectiveness and
event-window end for the successor. The **public V3 signature and defaults remain
unchanged**, including its original effectiveness and window checks. Complete source
opportunities/eligibility are validated before any successful derivation is selected.
All original failure category precedence and source-domain validation are reused.

`ReportCoverage` exposes exact universe, due eligible and measured identities,
full reconciliation, exact Measurement references, rate and explicit calendar
limitations. Verified calendar dates come from independently validated frozen
MLB acquisition request pages, including valid-empty responses and receipts with no
new contracts. Incomplete or rejected supporting sessions remain excluded. Unverified dates
remain listed outside known-game counts; game rows never prove calendar completeness.
For cumulative prospective reporting, calendar detail also includes known future
scheduled dates. This library does not implement downstream offered-market rates,
captured-count display projections or the descriptive constant-0.5 baseline.

Exact 50-digit, half-even arithmetic covers successor construction, decoding and
replay. Original derivation/Measurement constructors supply domain validation and
scoring. Extracted private helpers share the existing aggregate/calibration and
bootstrap draw/quantile procedures; there is no second scoring engine. Brier, extended
real log loss, ten fixed calibration bins, WACE, 95% confidence and 200 resamples
are unchanged. `mlb-reporting-bootstrap-seed-1` binds the computation specification,
Protocol/domain/source/role, actual event scope, canonical successor Measurement IDs
and original uncertainty parameters. Original V3 seed material remains unchanged.

Empty scores/intervals are absent; singleton/constant scores retain explicit
zero-width limitations; impossible realized outcomes preserve infinite log loss.
No significance, Market Edge, policy, wagering or empirical sufficiency claim is made.

## Accepted limits and remaining work

This is an offline/manual library, not operational report delivery. Source retention
and a trusted initial freeze are required; inconsistent/missing authority fails
visibly and permits a later independent attempt. No automatic recovery or service
is introduced. Final/correction publication and closure are deliberately rejected
because this slice has no accepted closure-record input or operational publication
workflow. Original study final-report obligations remain downstream.

Synthetic fixtures validate chronology, failure-inclusive populations, endpoints,
old-report preservation, foreign/mixed references, statistics, source immutability,
legacy byte/ID/seed fingerprints and input-order/Decimal replay. They do not certify
live Evidence completeness, current collection health or report-release readiness.
