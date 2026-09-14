# Archive-to-report implementation receipt

> Historical delivery receipt: the Owner subsequently required a simple principal
> report and authorized acquired-data reads/local generation. The current candidate
> and disposition are in [the correction receipt](MLB_SIMPLE_REPORT_IMPLEMENTATION_v1.2.0.md)
> and [PM self-review](MLB_SIMPLE_REPORT_REVIEW_v1.2.0.md). Earlier evidence below
> remains historical; it does not override the later usability correction.

September 13, 2026. **Local implementation, automated self-validation and the
representative basic-export visual check are complete; independent implementation
acceptance is the next gate.** This is
implementation-author evidence, not an independent acceptance review. See the
separate [PM/Chief Architect self-review](MLB_REPORTING_DELIVERY_REVIEW_v1.2.0.md)
and [remaining validation handoff](../planning/DELIVERY_VALIDATION_HANDOFF.md).

## Exact base and authorization

Repository: https://github.com/tomsullivanuk/pops-edge. Freshly fetched GitHub main,
local HEAD and origin/main were all
`3001ee9cd4d95519567e0e4567ff71be0465a6a0` (PR #50); first parent
`a658233dd218638025232630540c8044afb65a35`. There were no subsequent changes or
unrelated working-tree edits at initiation. Read the complete root AGENTS.md at
that revision, the handed-off review and scope, governing reporting amendments,
reporting contract, prior source/Analysis APIs and acceptance records, release
sequence and pinned-deployment boundary.

The Product Owner authorized local implementation, tests, focused documentation
and review artifacts through the delegated initiation. Local handoff and review
references were read unchanged. No commit, branch switch, push, PR, merge,
deployment, production report publication, provider acquisition, collector change,
archive/index/checkpoint mutation, tag or closure was authorized or performed.
Git fetch refreshed local repository tracking metadata only.

## Implementation inventory

| File | Change and purpose |
| --- | --- |
| `forecast_standalone_research.py` | Extract two original private capture-validation stages for reuse, leaving public constructors, selection rules, arithmetic and identity unchanged. |
| `forecast_reporting_projections.py` | Exact-population descriptive 50% reference; independently validated capture and probability sets; full reconciliation; offered-market membership/rates; ten-bin detail and versioned references. |
| `forecast_reporting_delivery.py` | Typed delivery envelope, independent anchor retention, exact replay, immutable package construction, separate dated receipts, atomic entry, independent historical selection, live update and offline viewing. |
| `operate_forecast_reporting.py` | Explicit manual generation, update, verify, historical selection, open and status commands. No acquisition path or synthetic CLI bypass. |
| `tests/test_forecast_reporting_delivery.py` | Twenty observable delivery/projection acceptance tests with disposable synthetic archives and output roots. |
| `docs/MLB_REPORTING_DELIVERY_API_v1.2.0.md` | API/operator guide, trust model, package identity definition, projections, failure behavior and proportionate manual recovery. |
| `docs/RELEASE_PLAN_v1.2.0.md` | Factual progress update preserving original baseline, incomplete release and remaining gates. |

This implementation receipt and its separate review are additional documentation.
The [exact candidate patch](../planning/DELIVERY_CANDIDATE.patch) includes the seven
files above, both receipts and the validation handoff. The
[file inventory and SHA-256 receipt](../planning/DELIVERY_FILE_INVENTORY.json) identifies
all changed files and local validation artifacts. No candidate commit exists.
Planning artifacts are local evidence, not an instruction to include them in a PR.

Source freeze, independently retained expected boundary ID, original source graph
replay and accepted Analysis verification precede package acceptance. Captured
membership is derived through the original capture stages, not inferred from
scores. The original root remains unchanged inside the package, with its original
limitations explicitly distinguished from added package capabilities. All delivery
work has later actual provenance. Operational generation requires a clean explicit
revision and actual wall clock; synthetic examples are conspicuously labelled and
identify the base revision, with this diff identifying the uncommitted code.

The local entry uses one atomic HTML replacement containing inert JSON for both
references and the last attempt. Interrupted work cannot become current through
directory enumeration. Output-local serialization uses no collector lock. A failed
update preserves both prior references and old package bytes; status-persistence
failure is raised directly. Missing historical files preserve selection and do not
block live updates. No production health is inferred.

## Validation receipts

Existing Python environment used read-only: `/Users/tom/pops-edge/venv/bin/python`,
Python 3.14.5, macOS Darwin 25.6.0 arm64. Repository-pinned pandas 3.0.3,
openpyxl 3.1.5, requests 2.34.2 and urllib3 2.7.0 were present. No dependencies
were installed or upgraded, and the collector environment/configuration was not
modified. Full environment details are in the
[environment receipt](../planning/DELIVERY_ENVIRONMENT.txt).

```text
/Users/tom/pops-edge/venv/bin/python -m unittest \
  tests.test_forecast_reporting_delivery tests.test_forecast_reporting_analysis \
  tests.test_forecast_reporting_source tests.test_forecast_standalone_research \
  tests.test_forecast_standalone_publication -q
117 tests, 22.590s — OK

/Users/tom/pops-edge/venv/bin/python -m unittest discover -s tests -q
893 tests, 61.768s — OK
```

[Focused log](../planning/DELIVERY_FOCUSED_TESTS.log),
[full regression log](../planning/DELIVERY_FULL_TESTS.log).
The full suite includes the original 53-record V3 byte/identity/seed fingerprint,
NFL and World Cup workflows and earlier source/Analysis/publication regressions.
Expected diagnostic messages from negative tests are retained in the full log.

New tests cover both studies, retained source inventories and byte equality,
no provider/network/write/collector-lock interfaces during delivery, fixed history,
future due and not-yet-due captures, unresolved outcomes and missed quotes; capture
without successful derivation/scoring; empty/singleton/constant/infinite results;
fixed-bin endpoints and empty bins; independent fresh-process verification;
missing/substituted anchors; rehashed capture/reference/calibration/HTML changes,
source substitution, mixed-study Analysis and omitted/extra payloads; ambient
Decimal precision and archive ordering; later outcome corrections and supporting
session completion; valid-empty calendar receipts and unknown dates; independently
preserved historical selection, missing historical files, package collisions,
write/verification/receipt/reference failures, no-prior-report failures, failed
attempt-status storage and output/path-alias rejection. Original legacy tests
supply further exclusion/lineage/chronology coverage; no scientific rule is replaced.

Two implementation defects found during the first new tests were corrected before
these final receipts: rendered provenance JSON depended on insertion order; and
macOS directory rename failed when candidate write permission was removed before
moving it. Rendering now has canonical order, and directory write permission is
removed after publication. Subsequent fixture corrections modeled immutable-directory
relocation and supplied correct canonical mapping/calendar authority. Final focused
and full receipts cover the corrected code.

## Retained synthetic examples and HTML validation limit

Examples are outside checkout and archives under
`/private/tmp/pops-delivery-validation-20260913/`. They remain disposable local
validation data and may be removed by temporary-storage cleanup. No real provider
Evidence was inspected, acquired or changed.

- [Saved entry with visible failed-update notice](</private/tmp/pops-delivery-validation-20260913/reports/entry.html>)
- [Historical interim HTML](</private/tmp/pops-delivery-validation-20260913/reports/packages/4837c279034b3fefc25589072e2e617c159a4f636656cca05df704cc762a045a/report.html>)
- [Live in-progress HTML](</private/tmp/pops-delivery-validation-20260913/reports/packages/47671396e9504938aec734d1ee7e8335f41c81784b2e83c3663e567126c1b2ff/report.html>)
- [Exact example references and retained anchor keys](</private/tmp/pops-delivery-validation-20260913/examples.json>)
- [Reproduction generator](../planning/GENERATE_DELIVERY_EXAMPLES.py),
  [static HTML check](../planning/CHECK_DELIVERY_HTML.py),
  [static HTML receipt](../planning/DELIVERY_STATIC_HTML_QA.json).

Static checks found exact report IDs/dates and canonical reference/calibration
values, resolving local links, language/main landmarks, table captions and header
scopes, no executable scripts or external resource URLs, honest unavailable/empty
and infinite-loss states, and retained prior links alongside the failed update.
Generation/verification/open tests compare archive and saved output bytes. These
checks are **not browser rendering, visual layout or assistive-technology validation**.

The required browser attempt used the Codex in-app browser with the saved local
entry. Browser security policy rejected the `file://` URL and explicitly prohibited
alternate browser surfaces, servers or indirect workarounds for the same action.
No workaround was attempted. The combined PDF evidence below satisfies the representative basic-export visual
requirement. Personally executed browser interactions remain a documented sampling
limit; no prohibited workaround was attempted.

## User-supplied PDF evidence amendment — September 13, 2026

The separate [PDF visual-evidence review](</Users/tom/.codex/.chatgpt-projects/g-p-6a6cba0d8b288191820b710ce15a39e4/V1_2_DELIVERY_PDF_VISUAL_REVIEW.md>) records the coordinating task's inspection of every rendered
PDF page, text and link annotations, with representative comparisons to the saved
projections. This implementation task read and incorporated that evidence artifact;
it did not independently inspect the PDFs or repeat scientific package verification.
The original PDFs and supplied evidence artifact remain read-only references.

| Source PDF | SHA-256 recorded by visual assessor |
| --- | --- |
| `/Users/tom/Downloads/Saved MLB reports.pdf` | `268c4daca8432543213f271f1e08ef6241d6a122c98768df0c3ccee0758f5d54` |
| `/Users/tom/Downloads/Historical candle report.pdf` | `52fb64945222a92dcdbfdc8101cd11b0b008bef5d0c3b91ba0907a3cd2eb61d2` |
| `/Users/tom/Downloads/Performance Report.pdf` | `323561cbbd0ba27b0edac320242d10675c24d1b9cf0d426dece5108268ea1992` |

Limited default-layout inspection passes: no visible clipping, overlap or missing
glyphs; headings, tables and long values remain readable; visible study/status/time
and sample values agree. Historical output preserves four scored observations,
Brier 0.4625, infinite log loss and unknown offered membership. Live output preserves
four known/three eligible/two captured/one scored, unresolved/missed/not-yet-due
states, Brier 0.2025, the singleton reference and valid-empty bounded results.
The entry preserves both package identities/dates with the failed update. PDF
annotations target the expected local files, but no browser clicks were performed.

The first batch had every disclosure collapsed. The subsequent batch resolves the
representative expanded-layout evidence: Performance Report_2.pdf shows readable
live cumulative calendar/identity/limitations and scientific provenance, including
the original root limitation explanation, without clipping or overlap. Original.pdf,
projections.pdf, source.pdf and REPRODUCE.pdf show the matching retained live-package
supporting content. The assessor compared all four exported texts with payloads
ignoring export whitespace, not as a replacement for byte verification or replay.

| Second-batch source PDF (under `/Users/tom/Downloads/`) | SHA-256 recorded by visual assessor |
| --- | --- |
| `Performance Report_2.pdf` | `3ebcc6723f13fb74a5b920bf56b1e32934e87739ff29e339ec70f3e9f11ca6b0` |
| `Original.pdf` | `368c349bb08b3eb4643fd253da6be05a7a0277267cb21e9b00efda19c61ad3f2` |
| `projections.pdf` | `c0fec3637345073a18c4fcc6d0d8326bef0a2739d035ae5ca3865c2c7e70fae2` |
| `source.pdf` | `b88c612b7576cb8c51cef2ac0ca73db4a40730c7875c9cba645bb15651308f31` |
| `REPRODUCE.pdf` | `3fa1729434202b0be068303f0e9ba6596d822ca057932d6713a71c105ec2fe4c` |

**Combined disposition: representative visual requirement satisfied for the basic
export.** No concrete visual correction is indicated. Expanded bounded/historical
instances remain unsampled; the assessor did not personally execute browser
navigation or disclosure toggling. The supporting views are consistent with intended
link targets, not proof of every browser interaction. Narrow viewport, paper
pagination and assistive-technology behavior remain outside this sampled evidence.
These proportionate limits do not require repeated screenshots without a concrete
defect or expand the original basic-export gate. This disposition supersedes the
earlier request for further screenshots/navigation confirmation. No independent
implementation acceptance is claimed.

The five implementation/test file hashes were checked against the preceding
validation inventory and remain unchanged. No code correction was justified by
this evidence, and no tests were rerun. The 117-focused/893-full-suite receipts
remain applicable. This is limited visual evidence, not independent implementation
acceptance. Only these local validation documents, handoff and derived patch/hash
receipts were updated; code, PDFs, package bytes, source archives and external or
operational state were not changed.

## Remaining gates

Next is independent implementation acceptance of this exact uncommitted candidate.
A reviewer independent of the author must inspect the code/diff, governing authority,
approved acceptance boundaries and tests, perform proportionate independent
validation, and issue a separate scoped acceptance/rejection artifact with concrete
findings and limitations. The visual sampling limits above remain acknowledged;
do not reopen them solely for exhaustive coverage absent a concrete defect.
See the [independent acceptance handoff](../planning/DELIVERY_VALIDATION_HANDOFF.md).

No independent implementation review was performed in this task. Production
commissioning/publication and integration remain separately authorized. The polished
Performance Report reader, local collection/status presentation, release-readiness
review, original study closure/final obligations and later shared shell remain
outside this candidate. No deployment or release handoff is issued before
independent implementation acceptance, and that acceptance itself will not authorize
commit, push, PR, merge, deployment or production publication.
