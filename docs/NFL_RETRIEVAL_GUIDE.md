# Retrieve NFL market quotes

From a checkout containing NFL-2A, use the project's Python environment:

```bash
python retrieve_kalshi_nfl.py capture --start-date 2026-09-09 --end-date 2026-09-14
```

Choose the dates each time; no NFL week calendar is inferred. The inclusive
window can cover one to eight days. The command uses Kalshi's public API without
an account, key, login or orders. It retrieves the full open KXNFLGAME catalog,
then books for games whose rules give an original scheduled date in your window.
This may include an in-progress game. Postponements can change the actual date.

The command prints its status and the saved run directory under
`~/PopsEdgeData/NFL/kalshi`. An optional `--store /absolute/path` changes storage.
Keep this data outside the source checkout and include it in manual backups.

Each uniquely named run contains:

- `started.json`: requested date window and actual run start.
- `response-NNN.body` and `.json`: original response body and request receipt,
  including actual request start/completion, status and body digest.
- `summary.json`: derived offers, provider labels/dates, source references,
  timestamps, available quantities, diagnostics and series fee metadata.
- `complete.json`: terminal receipt binding saved responses and summary.

`complete` means the bounded acquisition finished; it does not prove that all
scheduled games have markets. An empty catalog or empty book can be successfully
captured. Missing depth is explicit. `partial` means unsupported rules or a failed
selected book; `failed` means the acquisition could not establish the catalog or
other required validity. Those two statuses exit with code 2. A directory without
`complete.json` is interrupted. Inspect its existing receipts; start a new capture
to try again. Never repair a past observation using a later quote.

To verify the saved output without network access:

```bash
python retrieve_kalshi_nfl.py replay /absolute/path/to/run-directory
```

Replay verifies response digests and re-derives the output. Do not edit saved
files. The digest checks detect inconsistency, not malicious replacement of an
entire archive. Backups and local file security remain the owner's responsibility.

Prices are dollars per contract, stored as decimal strings. A YES offer is
`1 − highest NO bid`; a NO offer is `1 − highest YES bid`. Quantity comes from
that opposing bid. These are observed offers, not guaranteed later fills.
Metadata and books have separate timestamps and are collected sequentially.
The provider's `no_sub_title` is retained verbatim; it is not assumed to name the
opposing team. Fee metadata and rule URLs are retained, but fees and valuations
are not calculated. Full rule text remains in the catalog response.

NFL tie settlement differs from a simple win/loss contract: inspected rules
provide a $0.50 payout on a tie. This capture recognizes that rule text but does
not infer exact tie probabilities from rounded ELWAY percentages. Forecast
linking, authoritative kickoff data, comparisons, rankings and the board follow
in NFL-2B. This command does not run existing World Cup or MLB workflows.

See [acceptance boundary](NFL_RETRIEVAL_SLICE.md) for bounds and deferred work.
