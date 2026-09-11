# NFL integration handoff

> Historical pre-merge transfer record. PR #33 subsequently received
> [independent approval](NFL_PR33_INDEPENDENT_REVIEW.md) and merged at `d94e171`.
> The original authorization and next-step wording below records that earlier stage.

Repository: https://github.com/tomsullivanuk/pops-edge
Candidate branch: nfl/game-matching-board-v1.1
Base: e8d7469c7decabe52fa1eac444783837fd1b4e23
Review: [GitHub transfer review](NFL_GITHUB_REVIEW.md)
Workflow: [NFL refresh guide](NFL_REFRESH_GUIDE.md)

The owner authorized committing and pushing the approved local NFL work. After
that transfer, prepare a pull request/code review when authorized. Read current
main AGENTS.md and review the complete candidate diff, not only the latest UI
refinements. Check source replay, chronology, activity semantics, missing dates,
price eligibility, input bounds, packaged HTML and the all-week refresh behavior.
Run the offline unittest suite and check threshold/filter behavior. Do not widen
accepted operational limitations into new requirements. Preserve raw local data.
No merge, deployment, release, scheduled acquisition or order execution is
requested by this handoff.
