# NFL file-creation-time fallback

Owner-approved September 18, 2026. Rule: `nfl-file-creation-proxy-v1`.
This narrowly amends the publication-time requirement for new ELWAY workbook
imports. The original weekly protocol remains immutable for historical replay.

When the source explicitly says `Updated time unavailable`, use the original
selected file's filesystem birth time as a publication-time proxy, not as an
asserted publisher timestamp. A valid published timestamp always takes precedence.
Missing, malformed or conflicting timestamp text is not silently repaired.
Never substitute modification time, Unix ctime, import time or today's time.
If filesystem birth time is unavailable or future-dated, reject visibly.

Archive the birth time, observation time, source-byte digest and this rule's
digest with the new validation/import. Display “File creation time —
publication-time proxy”. Actual publication time and model age remain unknown.
File metadata can change or survive edits; it is an owner-accepted local proxy,
not independent proof that the current contents existed at birth time. Actual
archival import and market request timestamps remain the eligibility evidence.

For proxy imports, semantic identity uses source, season, target week, canonical
validated rows and time basis/rule. Metadata-only resaves, copies, renames and
reimports of identical rows cannot create a new research capture or move the
first accepted candidate's effective time. Changed rows are a distinct version;
different versions with the same effective time remain ambiguous. Order distinct
versions by their effective timestamp (published or proxy) with basis visible.
This cannot prove publisher-version ordering; stale copies are an accepted local
limitation, never evidence of model freshness.

The weekly cutoff, actual import time, activation time, preserved pre-cutoff
schedule and each market request's completion time still apply. No retrospective
enrollment, quote reconstruction, history rewriting or reopening a frozen week.
An older rejected import does not become valid merely because this amendment
is installed. Old reports replay using only their original event prefix.

Applies to the Bet Sheet and prospective performance workflow. Research records
pin the amendment digest individually; existing activation and baseline protocol
digests are not overwritten. MLB, accounting, scoring and provider acquisition
rules are unchanged. No migration or live capture is implied by implementation.
