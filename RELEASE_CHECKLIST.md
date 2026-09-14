# Pops' Edge Release Checklist

## MLB v1.2 approval status — September 14, 2026

The [reconciled release record](docs/MLB_RELEASE_RECORD_v1.2.0.md) governs the
narrowed MLB release. Reporting, collection-status correction and local activation
are complete; Owner layout acceptance is recorded. Existing independent reviews,
compatibility evidence and dated operational follow-up are reused.

This documentation candidate has not been committed or published. Final candidate
diff/inventory validation, explicit Owner publication approval, exact release commit,
tag and hosted-release verification remain publication steps. Generic checkboxes
below are a reusable checklist, not claims that every check was rerun. No new full
suite, present-health audit, deployment or study closure is asserted.

> Release allocation, September 8, 2026: v1.1.0 is the NFL comparison board;
> the previously planned v1.1.0 MLB programme now targets v1.2.0. Historical
> sections and PR numbers below remain unchanged. See
> [release allocation](docs/RELEASE_ALLOCATION_2026-09-08.md) and
> [NFL acceptance gates](docs/NFL_RELEASE_PLAN_v1.1.0.md).


Use this checklist during release hardening. Completing documentation does not
authorize a commit, tag, push, hosted release, or rename.

## Scope and documentation

- [ ] Release objective and acceptance criteria are satisfied.
- [ ] All planned PRs are reviewed and merged in order.
- [ ] `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `BACKLOG.md`,
      `CHANGELOG.md`, and relevant `docs/` files are current.
- [ ] Operator instructions, known limitations, migrations, and rollback are
      documented.
- [ ] World Cup compatibility impact is explicitly recorded.

## Validation

- [ ] Full automated test suite passes.
- [ ] All Python source and tests compile.
- [ ] All shell scripts pass syntax checks.
- [ ] `git diff --check` passes.
- [ ] Product-name, version, repository-path, secret, and generated-artifact
      searches are reviewed.
- [ ] Deterministic fixture-based end-to-end workflows pass.
- [ ] Separately authorized live/manual smoke checks are recorded.

## Repository review

- [ ] Worktree status is understood and unrelated changes are excluded.
- [ ] Staged diff contains only approved release files.
- [ ] No generated reports, raw downloads, archives, virtual environments,
      credentials, or secrets are staged.
- [ ] Release version and changelog agree.

## Authorization and publication

- [ ] User explicitly approves the release commit.
- [ ] User explicitly approves push and tag creation.
- [ ] Tag name and release notes are reviewed.
- [ ] Remote checks and hosted release succeed.
- [ ] Post-release verification is recorded.

## Optional rename

The repository rename is not a normal release step. If separately authorized,
complete `docs/REPOSITORY_RENAME.md` and its rollback/validation procedure.

## NFL v1.1.0 status before publication

Source implementation merged through PR #33 at `d94e171`; the exact candidate
passed independent review and 774 tests. The subsequent version/documentation
cleanup is a separate uncommitted change and must receive its own diff review.
The current app's VERSION label is not a release tag. Two P2 limitations are
recorded in BACKLOG and the NFL refresh guide. GitHub tag/release publication,
deployment and post-release checks remain pending; the generic checklist above
is intentionally not marked complete by this status note.
