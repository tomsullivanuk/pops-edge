# Codex Pull Request Workflow

This is the standard Pops' Edge workflow, adapted from the established Library
Valuation PR process. The unit of work is one narrowly scoped, reviewable PR.

## Standard PR prompt

Every PR prompt should define:

1. **Title and version** — release and PR number.
2. **Context** — baseline state and reason for the work.
3. **Objective** — one outcome stated plainly.
4. **In scope** — required inspection, implementation, documentation, and
   validation.
5. **Out of scope** — prohibited or deferred work.
6. **Acceptance criteria** — observable completion conditions.
7. **Validation** — exact required checks and forbidden side effects.
8. **Completion report** — required handoff format.
9. **Authorization boundary** — whether staging, commit, push, tag, release, or
   external mutations are allowed.

## 1. Confirm the contract

Before editing, restate the objective, in-scope work, exclusions, acceptance
criteria, validation, and authorization boundaries. Treat the current worktree
as user-owned: inspect existing changes and do not overwrite, discard, stage,
or commit unrelated work.

## 2. Inspect before changing

- Read current-facing and developer documentation.
- Inspect relevant source, tests, configuration, scripts, and git status.
- Search for existing conventions and external dependencies.
- Establish the behavioral baseline and identify files expected to change.

If the requested scope conflicts with existing uncommitted work, preserve that
work and report the overlap.

## 3. Implement the smallest coherent change

- Keep the PR aligned to its stated objective.
- Prefer durable documentation and explicit contracts over speculative
  abstraction.
- Preserve backward compatibility unless the PR explicitly changes it.
- Do not edit generated outputs, local data, archives, virtual environments, or
  credentials.
- Do not perform excluded release operations such as commits, pushes, tags, or
  repository/directory renames.

## 4. Validate

Run validation in proportion to risk. Unless a PR specifies stronger checks,
the Pops' Edge baseline is:

```bash
./venv/bin/python -m unittest discover -s tests
./venv/bin/python -m py_compile *.py tests/*.py
bash -n update_all.sh update_wagers.sh update_worldcup.sh
```

Also:

- search for hard-coded repository paths when changing product structure;
- inspect `git diff --check`;
- inspect the complete diff and diff summary;
- report skipped or environment-dependent checks explicitly; and
- confirm generated artifacts and user-owned changes were not accidentally
  added.

Validation commands must not invoke live update workflows unless the PR
explicitly requires and authorizes their external side effects.

## 5. Review handoff

Do not commit until the user reviews the completion report when the task
requires review-first handoff. After approval, stage only the intended files,
inspect the staged diff, and commit with a focused message. Push, tag, release,
and rename operations require explicit authorization.

## Documentation expectations

- Update durable documentation in the same PR as the decision or behavior it
  describes.
- Keep `README.md` current-facing and concise.
- Use `ARCHITECTURE.md` for present system boundaries, `ROADMAP.md` for ordered
  direction, `BACKLOG.md` for uncommitted work, and `CHANGELOG.md` for shipped
  or planned version history.
- Put release-specific scope in a release plan and operational release gates in
  `RELEASE_CHECKLIST.md`.
- Preserve historical and provider-specific names when renaming them would
  misrepresent compatibility or scope.
- Do not edit generated reports as documentation.

## Release workflow

1. Confirm every release-plan PR is reviewed and its acceptance criteria are
   traceable.
2. Run the complete deterministic validation suite from a clean, supported
   environment.
3. Complete `RELEASE_CHECKLIST.md`, documentation, migration notes, known
   limitations, and rollback guidance.
4. Inspect status and staged content; keep local/generated artifacts out.
5. Obtain explicit approval before the release commit, tag, push, hosted
   release, repository rename, or other external mutation.
6. Create the approved release artifacts and verify the resulting tag/remote.
7. Record the release in `CHANGELOG.md` and report any post-release follow-up.

## Completion report

Use these exact sections:

### 1. Summary

State the outcome and scope in a few sentences, including preserved behavior.

### 2. Repository State Before PR

Describe the branch/worktree state observed before editing. Clearly distinguish
pre-existing modifications and untracked files from work performed in the PR.

### 3. Files Changed

Separate `Modified` and `Created`. List each intended file and its purpose.

### 4. Key Decisions

Record naming, compatibility, sequencing, architectural, or operational
decisions and why they were made.

### 5. Acceptance Criteria

Report each criterion with `✓` or `✗` and evidence.

### 6. Tests and Validation

List exact commands and results. Include path searches, syntax checks, and
diff checks where applicable. Explain anything not run.

### 7. Risks and Open Questions

Identify unresolved dependencies, assumptions, follow-up work, or `None`.

### 8. Git Diff Summary

Summarize only changes made by the current PR. If worktree-wide Git output
includes pre-existing work, say so and do not attribute it to the PR.

### 9. Git Status

Separate pre-existing repository changes from current-PR changes. State
explicitly whether anything was staged, committed, pushed, tagged, or renamed.

### 10. Suggested Next PR

Name the next PR in the release plan and summarize its bounded objective.
