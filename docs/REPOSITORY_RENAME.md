# Repository Rename Record: `kalshi` to `pops-edge`

## Status

The approved migration was completed on July 28, 2026.

- Product: Pops' Edge
- Prior GitHub repository: `tomsullivanuk/World-Cup-Value-Board`
- Current GitHub repository: `tomsullivanuk/pops-edge`
- Prior local directory: `/Users/tom/kalshi`
- Current local directory: `/Users/tom/pops-edge`

The old names are retained in this document as historical migration facts.
Kalshi-specific source, variable, fixture, and artifact names remain where they
identify the market provider rather than the product or repository.

## Repository-controlled changes

- `origin` was updated to
  `https://github.com/tomsullivanuk/pops-edge.git`.
- `config.py` now sets `PROJECT_DIR` to `~/pops-edge`.
- Current operating instructions use `~/pops-edge`.
- Architecture and backlog documentation describe the post-migration state.
- World Cup scripts, reports, workbooks, commands, and the iCloud World Cup
  destination were intentionally not renamed.

## Preserved GitHub state

The hosted rename preserved:

- private visibility;
- `main` as the default branch;
- the `main` and `feature/wager-log-archiving` branches;
- commit history; and
- issue support.

At the migration baseline there were no tags, releases, open pull requests, or
open issues. Authenticated requests using the prior repository identifier
resolved to `tomsullivanuk/pops-edge`.

## External dependency inventory

The migration audit covers:

- shell aliases, functions, and startup files;
- local scripts and scheduled `launchd`, cron, Shortcut, or Automator tasks;
- IDE workspaces and project settings;
- Codex workspace and task configuration;
- Git worktrees and downstream clones;
- GitHub Actions, secrets, webhooks, deploy keys, badges, and links;
- the macOS `open` and `osascript` commands;
- the iCloud destination
  `~/Library/Mobile Documents/com~apple~CloudDocs/WorldCup`;
- `~/Downloads` as the manual landing area for Silver forecasts and Kalshi
  activity exports;
- the public Kalshi trade API; and
- the local Python virtual environment.

External files are changed only when clearly owned by Pops' Edge and safe to
modify. Anything ambiguous or unavailable is reported for manual follow-up.

## Validation

The migration validation requires:

1. The complete deterministic test suite.
2. Python compilation and shell syntax checks.
3. Clean Git diff and status checks.
4. Successful fetch from the renamed origin.
5. Searches for executable `~/kalshi` paths and current references to the old
   repository URL.
6. Local documentation-link checks.
7. Verification from `/Users/tom/pops-edge` that the branch, history, virtual
   environment, and project commands remain available.

Live Kalshi updates, trading, iCloud copies, browser launches, and notifications
are excluded from deterministic migration validation.

## Rollback

If a local-path failure is discovered, restore the prior directory name,
temporarily restore the prior `PROJECT_DIR`, and re-run deterministic
validation. If the hosted rename must be reversed, rename the repository back
only during an authorized maintenance window, restore `origin`, and re-verify
all integrations. Do not delete the clone or generated data during rollback.

## Post-migration acceptance criteria

- The canonical hosted repository is `tomsullivanuk/pops-edge`.
- The local directory is `/Users/tom/pops-edge`.
- No executable code assumes `~/kalshi`.
- Current repository URLs use `tomsullivanuk/pops-edge`.
- Intentional Kalshi provider names remain functional.
- External dependencies are updated or documented.
- World Cup regression validation passes from the new directory.
- The rename-related commit is pushed and the worktree is clean.
