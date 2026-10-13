# Final bounded lineup observation: two games

October 12, 2026 local date; completed October 13 00:07:59 UTC.
The original private `FINAL_SUMMARY.md` and `FINAL_OBSERVATION_RECEIPT.json` were
read from the coordinating observer's finite-run directory before this record.
The observer is stopped and its process absence verified. No duplicate launched.

| Team | Last absent (Oct 12 UTC) | First complete observed (Oct 12 UTC) | Approximate lead to scheduled start |
| --- | --- | --- | --- |
| Milwaukee | 17:05:28 | 17:20:28 | 3h40 |
| Los Angeles | 17:20:28 | 17:35:28 | 3h25 |
| Cleveland | 19:50:30 | 20:05:30 | 3h54 |
| Tampa Bay | 19:50:30 | 20:05:30 | 3h54 |

All complete orders had nine unique IDs with agreeing starting-slot codes.
Earlier incomplete snapshots bound each transition; these are first-observed
feed times, not exact team announcements. No order or probable-pitcher changes
appeared in saved snapshots; between-poll changes cannot be excluded. Scheduled
starts remained October 12 21:00 UTC and October 13 00:00 UTC. Explicit pregame
pitcher confirmation and actual first-pitch timestamps remain unknown.

Preserve operational limitations: the process-loss gap is 13:00:57–13:50:24 UTC.
The first game stopped prematurely at 20:40:35 because Warmup was treated as Live,
leaving its late pregame and actual start unobserved; it was not reopened. A
controlled correction occurred 21:05:31–21:07:49 with no planned five-minute poll
skipped. The second game stopped at explicit In Progress at October 13 00:07:59,
after Warmup at 00:02:59; no actual pitch timestamp was retained. The feed's early
gameInfo.firstPitch field is not promoted to actual-start evidence.

118 observer requests returned HTTP 200; the parent verified all 118 raw hashes.
Three separate baseline requests make 121 task-wide source calls. Zero HTTP
failures does not erase the process-loss and premature-stop failures. Original
240-request / 00:30 UTC limits were respected. No paid call, credentials,
production changes or observer extension. Raw payloads/receipts stay private.

This supports practical pregame order availability for these two postseason
games, well before the proposed nearer-start checks. It does not establish
regular-season reliability, source announcement latency, confirmed pitchers,
Kalshi executability or model edge. Prospective lineup timing need not block
model development. Earlier interim documentation is superseded by this final
qualified record; existing T−6h protocols remain intact.
