# MLB Performance — explicit manual update

September 17, 2026. Owner-adopted bounded update workflow, implemented as a candidate. Independent acceptance, integration, local deployment and real report generation remain separate gates.

## User workflow

Performance → MLB offers **Update report**, inside the MLB Performance panel beside its heading, outside Period/Team filters. One explicit local action calculates a report from already collected research evidence, validates it, prepares matching rows before selection, and reads existing collection records for an independently dated observation. No repeated confirmation is required. Opening, filtering, polling and reloading never start work. Table filters do not affect scientific populations.

Previous saved output remains readable while updating. A failed scientific calculation or match preparation retains the previous live selection, dates and rows. Success displays the cumulative date range ending on the evidence-cutoff Central date and actual generation time on one line; exact cutoff and generation timestamps remain separately labelled in Details. A newly calculated report can still have missing captures, unresolved outcomes or no additional scored results. New cutoff time never claims complete evidence coverage. Numeric metrics retain two-decimal presentation.

Collection observations are optional, separately dated and package-bound. Missing/malformed records or secondary observation failure do not invalidate selected science. The existing historical selection and its immutable content remain untouched; no historical report is needed for a valid live update. Existing original saved readers retain their rendering and observation dates. The new observation is shown in the current app reader and downloadable there.

## Deployment configuration

The web app may run from an exported source tree. Its reporting worker must run from a **separate clean Git checkout at an explicitly pinned accepted commit**, using an existing compatible Python interpreter. It checks the pinned revision before execution, before/after science and after match preparation. `-B` avoids dirtying that checkout with bytecode. A source deployment does not silently repin the collector or reporting worker.

Pass `--mlb-update-config /absolute/report-update.json` to `nfl_refresh.py`. Omission leaves the reader usable and displays a disabled update action with a configuration notice. Supply a trusted local JSON object with exactly these fields:

```json
{
  "checkout": "/absolute/clean-reporting-checkout",
  "revision": "FULL_40_CHARACTER_ACCEPTED_COMMIT",
  "python": "/absolute/existing-environment/bin/python",
  "archive_config": "/absolute/existing-archive-config.json",
  "operational_state": "/absolute/configured-log-root/operational-state",
  "reports": "/absolute/existing-report-output"
}
```

Use the same `reports` root as `--mlb-reports` (or its existing default). Operational records must be the configured archive deployment's log-root/operational-state directory. Output cannot overlap either evidence archive, the worker checkout, operational logs or a source checkout. Browser requests cannot choose paths, commands, revisions or date/scoring inputs. The action reuses localhost Host/Origin/token/JSON protections.

The worker subprocess has a fixed argument list and no provider calls. Configuration checks are repeated in the pinned worker. Existing CLI generation remains available and unchanged; the new delivery option `prepare_matches=True` is restricted to live updates. It creates the supplement from an explicitly referenced validated package under the existing delivery writer lock, before moving selection. The old selected-only match CLI retains its behavior.

## Attempts and concurrency

`REPORTS/updates/current.json` records the most recent workflow attempt; each `updates/<attempt-id>/` retains its config paths/pin, attempt outcome, worker log and optional collection observation. These are local operational/presentation artifacts, not Evidence. The observation hash and exact package reference bind its display/download. Attempt files are atomically replaced. Existing scientific attempts remain in delivery state; they are not overwritten with operational health outcomes.

One inherited OS lock spans worker startup, scientific generation, match preparation and optional collection observation. Duplicate clicks/other application instances receive an explicit busy error. Existing delivery locking excludes simultaneous scientific writers. A separate command may independently change report selection after this workflow; the reader will not attach an observation to a different package.

States: idle/unconfigured → running → succeeded or failed. A saved running attempt without its active worker lock is displayed as interrupted. Unreadable saved status is explicitly unavailable. The previous selected report remains usable. If publication of workflow status fails after scientific selection, the selected valid report remains authoritative; inspect the retained delivery state and log before retrying. No success is inferred from an unfinished workflow record.

Preflight errors before a safe attempt directory exists are returned directly to the click. Other failures retain attempt records; no automatic retry or cleanup occurs. A killed app does not necessarily kill its detached worker. Reload reads the worker lock and saved state without starting another calculation.

## Bounded manual recovery

For interrupted or unreadable attempt status, the UI disables new starts. An operator should:

1. Confirm no reporting worker remains active, using its process command and the updates writer lock. Do not remove a held lock file.
2. Read the retained `updates/<attempt-id>/worker.log`, attempt record and `entry.html` delivery state. Determine whether a validated report was selected before interruption. Retain all packages, anchors, receipts and match files.
3. Correct configuration/storage problems. Preserve the problematic `updates/current.json` by moving it to a uniquely named recovery record in the same updates directory. Do not alter per-attempt evidence or scientific selections to manufacture success.
4. Reload and initiate a new independent attempt. If an independent delivery writer remains active, wait for it. Do not modify collector records or replay unknown provider calls.

A missing/unavailable collection observation needs no scientific rollback. A later explicit update may reread status; existing separate manual status-display activation also remains available with its own unchanged prerequisites.

## Acceptance and limitations

Must hold: governed scientific validation/replay, complete failure-inclusive membership, matched rows before selection, preserved historical selection and old bytes, truthful failure and chronology, no GET writes/acquisition, exact pinned execution and safe local action boundaries. Tests cover added/no-added scored evidence, invalid source, match failure, optional status failure, interruption, competing starts, local request protections, configuration checks and immutable archive preservation.

Accepted: local machine dependency, manual updates/recovery, variable archive-validation runtime, incomplete archived evidence, and trusted local filesystem/configuration. No duration or latest-game coverage guarantee. No new service, queue, scheduler, provider acquisition, collector repair, model, settlement change, study closure or wagering authority. Full Administration and automatic refresh remain deferred.
