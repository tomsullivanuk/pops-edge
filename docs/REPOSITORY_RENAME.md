# Repository Rename Plan: `kalshi` to `pops-edge`

## Status

The durable product name is Pops' Edge. The GitHub repository and local
directory are still named `kalshi`. Renaming them is deliberately deferred and
must not be performed as part of PR1.

## Dependency inventory

### Confirmed in this repository

- `config.py` sets `PROJECT_DIR` to `~/kalshi`. This is the executable
  hard-coded local repository path.
- Existing documentation has used `~/kalshi`, `kalshi/`, and an alias that
  changes into `~/kalshi`.
- Processors and wager import use `PROJECT_DIR` when discovering local inputs
  and creating archive paths.
- The repository contains Kalshi-specific module, variable, fixture, and
  artifact names. These identify a market provider and are not automatically
  candidates for the product/repository rename.
- Shell workflows rely on relative paths after resolving their script
  directory, but `update_worldcup.sh` assumes it is launched from a directory
  where its relative Python/script paths resolve. This should be verified
  during migration.

### External and operator dependencies to verify

- GitHub repository URL, default branch protection, actions, secrets,
  environments, webhooks, deploy keys, badges, and issue/PR links.
- Local clone path, additional worktrees, IDE workspaces, terminal profiles,
  shell aliases/functions (including `wcup` and any `cd ~/kalshi` alias), and
  scripts outside this repository.
- Cron, `launchd`, Shortcuts, Automator, or other scheduled workflows.
- Codex workspace/task configuration and any tools that identify the repo by
  absolute path.
- Documentation, bookmarks, shared links, and downstream clones.
- macOS `open` and `osascript` availability.
- The iCloud destination
  `~/Library/Mobile Documents/com~apple~CloudDocs/WorldCup`.
- `~/Downloads` as the manual landing area for Silver forecasts and Kalshi
  activity exports.
- Network access to the public Kalshi trade API and its current endpoint,
  schema, availability, and rate behavior.
- Python virtual environment location and installed dependencies.

## Proposed procedure

Execute only in a separately authorized maintenance window:

1. Ensure the worktree is clean and all intended work is committed and backed
   up. Record the current remote URL and clone/worktree locations.
2. Search the repository and relevant operator configuration for `kalshi`,
   `~/kalshi`, absolute clone paths, and the old GitHub URL. Classify product
   references separately from legitimate provider-specific Kalshi references.
3. Make `PROJECT_DIR` derive from the repository/configuration rather than a
   fixed directory, with focused tests. Update documented aliases and any
   verified external automation.
4. Rename the GitHub repository from `kalshi` to `pops-edge`; preserve redirects
   if the host supports them and verify branch protection, actions, secrets,
   webhooks, and links.
5. Update the local remote URL and verify fetch access.
6. Rename the local directory to `pops-edge`, then recreate or repair virtual
   environments, IDE workspaces, worktrees, Codex configuration, aliases, and
   scheduled jobs that contain the old absolute path.
7. Run the complete deterministic test, Python compilation, and shell syntax
   suite from the new path.
8. Run separately authorized smoke tests for live Kalshi access, Downloads
   discovery, archive creation, iCloud copies, notifications, and report
   opening.
9. Repeat path and old-URL searches. Document any intentional remaining
   provider-specific `kalshi` references.

## Rollback

If local validation fails, restore the prior directory name and remote URL,
then revert only the migration-specific configuration changes. If the hosted
rename fails, restore the old repository name when possible and re-verify
external integrations. Do not delete either clone or generated data as part of
rollback.

## Rename acceptance criteria

- The canonical hosted repository and local directory are named `pops-edge`.
- No executable code assumes `~/kalshi` or another machine-specific clone path.
- Intentional Kalshi provider names remain clear and functional.
- GitHub integrations and external automation are verified.
- World Cup regression validation passes from the renamed path.
- Live/manual smoke checks are recorded without overwriting or losing local
  artifacts.
