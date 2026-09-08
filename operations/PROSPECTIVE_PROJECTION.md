# Prospective projection operation

The collector requires `prospective-projection.json` in its existing primary
namespace. This is disposable Operations state; never treat it as Evidence or
copy it between namespaces. Initial activation initialization creates it. For an
existing installation, after separately approved deployment, build it explicitly:

```sh
python operate_forecast_standalone_activation.py --config /absolute/path/to/config.json rebuild-prospective-projection
```

This command is offline: it reads archived authority and replaces only the derived
projection. Configured `maintain` also rebuilds it. No provider or credential is
required. Building the projection does not install jobs, activate a Protocol, or
authorize deployment.

| State / diagnostic | Meaning and action |
| --- | --- |
| `projection-absent` | No projection exists. Run the explicit build. No call occurs. |
| current | Sources verify at a stable relevant boundary. Capture still performs fresh authorization. |
| stale | Relevant sources were appended. The next collector performs bounded verified refresh. If sources change again during preparation, it fails visibly and a later independent invocation may retry. |
| `projection-invalid`, source validation failure | Content, versions, dependency presence, or immutable sources do not verify. Inspect the archive and resolve the cause before rebuilding. Never edit Evidence or the projection to manufacture authority. |
| `projection-budget-exceeded` | Required verification exceeds the local work bound. Do not widen capture windows or remove dependencies. Retain the failure and return the measured growth for architectural review. Rebuilding cannot remove a genuine budget excess. |
| `prospective-collector-busy` | Another collector owns this invocation. No second collector request occurs. The OS releases ownership when that collector exits. |

Supporting refresh, supporting corrections, schedule reconciliation, successful
Outcome publication, and capture dispositions update the relevant immutable
source set. Refresh is detected from that set, so a missed mutable notification
cannot leave the projection falsely current. Unrelated retrospective candle
acquisition/publication and non-authoritative Outcome failures do not invalidate
it. Full archive maintenance and ordinary audit remain responsible for unrelated
archive health.

Previous misses remain misses. A failed rebuild changes no archive authority.
Keep failures visible; after fixing an operational issue, resume with later
independent valid collection. No automatic recovery or historical quote repair
is provided.

## Interrupted prospective capture

Builder version 2 requires an explicit offline rebuild of an older projection.
Rebuild now checks full archive integrity outside the mutation lock; it refuses
orphaned material or unresolved prospective transactions. It does not repair
Evidence or clear a request fence.

The collector durably writes a request fence before its final clock check and
provider request, and a publication intent before raw/normalized writes. The
canonical manifest completes publication. An exact completed retry is idempotent;
conflicting content is refused. The completed manifest and referenced objects
still undergo canonical scientific validation.

`prospective-publication-ambiguous` means a previous request or publication
cannot be proved complete. Its opportunity is blocked, including later no-call
records; independent opportunities can continue. Health reports invalid while
any ambiguity remains. Retain the marker files, orphaned objects, and logs for
manual audit. Do not delete markers, adopt partial objects, rerun the ambiguous
opportunity, or classify an unknown request as a miss. A completed manifest can
prove completion on restart; only a still-running owner that has not entered
transport can cancel its own unissued request. No automatic recovery command is
provided. Any resolution requiring archive changes needs separate review and
Product Owner authorization; later independent collection needs no such repair.

`prospective-requests/` and `prospective-publications/` are durable negative
Operations state, not scientific Evidence and not disposable projection cache.
Their check reads bounded marker metadata and selected source material, without
loading unrelated historical or publication payloads. The historical cutoff
exclusion specifically matches the actual supporting-tagged Kalshi writer with
no Protocol ID, for both successful and failed acquisitions.
