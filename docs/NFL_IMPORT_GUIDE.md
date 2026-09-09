# Import a weekly ELWAY screenshot

Use a Mac with Python 3 and Xcode Command Line Tools (`swift`). All image
recognition stays on the Mac. No API keys, remote OCR service or paid dependency
is used. The importer supports PNG/JPEG, regular-season weeks 1–18.

1. Save the full forecast table, including its update timestamp and week, in
   `~/Downloads/PopsEdge/NFL/`. Keep the original image intact.
2. From the source directory, run:

   ```bash
   python3 nfl_forecast_import.py prepare --season 2026
   ```

   If there are several images, supply the specific path after `prepare`.
   The command prints a local review-page path. Open that HTML file.
3. Check the original beside the extracted rows. Correct blank/misread team
   codes or percentages, check the neutral-site marker, add/remove rows as
   necessary, and check each row. Verify the season, week, complete game count,
   and published timestamp (e.g. `2026-09-07T12:02:00-04:00`). Saving the file or
   importing it today does not establish when it was originally captured.
4. Click **Save checked review**, then validate/archive the downloaded review:

   ```bash
   python3 nfl_forecast_import.py verify ~/Downloads/elway-checked-review.json --reviewer 'Tom'
   ```

Only this command produces a verified JSON record. The review-page save cannot
activate a forecast. Invalid values or missing verification produce a clear
error and no verified record. Check the printed filename if your browser adds
a suffix to the download.

Both commands accept `--store PATH` for an isolated local data directory.
Originals, import receipts, raw OCR, candidate reviews and verified records are
separate. Preparation does not alter/move Downloads files. Verification uses
actual current time; it cannot backdate collection. Raw original file times are
not treated as provider timestamps. Do not put the data store into source control.

For a correction, edit/recheck a review and run verify with
`--supersedes PREVIOUS_VERIFICATION_ID`. The old record remains available. New
images get separate source identities. This slice deliberately does not select
a current forecast automatically or link a source matchup to an official game.

OCR misses are expected, especially coloured team badges; never infer the
missing home code by shifting the away team left. Every row needs visual review,
even when OCR confidence is high. If recognition fails, the source is retained;
check local Swift/Vision availability and retry. In restricted agent sandboxes,
Apple Vision may require a normally permitted local execution environment.

The output is verified transcription ready for the later schedule/market
comparison slice. It contains no odds, fee estimates, tie probability, wagers,
or empirical accuracy claims.
