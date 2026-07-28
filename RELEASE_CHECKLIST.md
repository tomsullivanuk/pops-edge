# Pops' Edge Release Checklist

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
