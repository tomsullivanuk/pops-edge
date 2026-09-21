# Clean pinned deployment gate

Startup recovery amendment (September 21, 2026): the two scheduled CLI commands
now pass a boot-session verification gate before provider work. Commissioning
must run `verify-startup` using the pinned interpreter/checkout and activated
configuration before reactivating jobs. This rebuilds offline on first use/new
boot, with zero provider calls. Inspect any blocked/interrupted startup before
explicit `verify-startup --retry-startup`; never add that retry flag to launchd.
See [startup states and recovery limits](PROSPECTIVE_PROJECTION.md#bounded-startup-verification-september-21-2026).
Offline fixture validation is not permission to reboot the host, deploy, or
change operational state. Test restart behavior in isolation before commissioning.

Commission only after independent amendment review, accepted integration, and
explicit Product Owner deployment authorization. The current implementation does
not create a deployment checkout or modify any scheduler state.

Use a dedicated clean checkout detached at the exact accepted merge revision.
Do not reuse `/Users/tom/pops-edge`, and keep configuration, logs, archives,
secondary data, rendered jobs and Python environment outside the checkout. Retain
all prior Evidence, failures and request/publication markers unchanged. Choose the
dedicated checkout path at the separately authorized commissioning gate.

The renderer requires `--expected-revision` for live configurations. It checks
HEAD, detached state, tracked changes and untracked files without modifying Git.
The generated job repeats this check before loading configuration or doing work,
so later checkout drift fails closed. Generated jobs direct stdout/stderr to
the configured log root, including failures before configuration loading. The log
directory must exist and be writable at commissioning. A fixture configuration may render from a
development checkout solely for offline rehearsal.

After separate authorization, render inert plists from the clean pinned checkout:

```sh
/absolute/python /absolute/pinned/operate_forecast_standalone_activation.py \
  --expected-revision <accepted-40-character-commit> \
  --config /absolute/activated-config.json render-launchd --output /absolute/rendered-jobs
```

Install exactly these two generated jobs during commissioning:

- `com.popsedge.pr17c1.prospective`: every 30 seconds.
- `com.popsedge.pr17c1.lifecycle`: hourly at minute 7, with daily phases due after
  04:00 in the Mac's local timezone.

The old five independently scheduled supporting, outcomes, maintenance, secondary
and health jobs must remain absent from the commissioned topology. Legacy PR17B2
examples are historical dry-run material, not additional activated jobs. Rendering
is inert: it does not install, load, enable, bootstrap, or start any job.

The `rebuild-prospective-projection` command permits three total full preparation
attempts when concurrent relevant publication causes `projection-stale`. Each
attempt recaptures sources with a fresh trusted timestamp. Successful output
includes `rebuild_attempts`; exhaustion retains the `projection-stale` failure
and zero provider-call count. Other failures are not retried. Full and cached
replays are compared only at matching source boundaries, and all publication and
rejected-lineage guards remain active. The collector remains independent; this
does not guarantee rebuild progress under continuous publication. Exhaustion
continues to block dependent maintenance and remains visible for operator review.

Before authorizing acquisition, independently verify archive integrity, rebuild
and compare the checkpoint, rebuild the index, synchronize the secondary copy,
and inspect all unresolved markers and current health conditions. Then perform
only the separately authorized collector/cycle commissioning observations. Do not
infer permission for provider calls from a successful renderer, checkpoint build,
review, or health result. Preserve missing prospective windows and failure history.
A later revision requires a fresh accepted pinned checkout and explicit deployment
authorization; do not update a running checkout in place.
