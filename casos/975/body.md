
# Internal Trusted PR Reviewer

Review pull request #${{ github.event.pull_request.number || github.event.inputs.pr_number }} in repository `${{ github.repository }}`.
This workflow imports `pulumi-labs/gh-aw-internal/.github/snippets/code-review.md@main` for the baseline review rubric.

## Trust Model

This workflow supports both `pull_request` and manual `workflow_dispatch` triggers.
For `pull_request`, it uses gh-aw default fork filtering (same-repository PRs only unless `forks` is explicitly configured).
`tools.github.lockdown: false` is set to avoid requiring a custom GitHub MCP token.
If required PR context cannot be read in this trust model, call `noop` with a brief reason and stop.

## Workflow-Specific Rules

- Use `${{ github.event.pull_request.number || github.event.inputs.pr_number }}` as the authoritative PR target.
- Ignore discovery steps intended for runs without PR context.
- Use `create-pull-request-review-comment` for actionable inline findings on changed lines.
- Submit exactly one final review with `submit-pull-request-review`:
  - `REQUEST_CHANGES` when at least one blocking issue exists.
  - `APPROVE` otherwise, including when only non-blocking observations exist.
  - Do not submit `COMMENT` as the final review state.
- If there is nothing to do because trust/context checks fail, call `noop`.

Constraints:
- Post no more than 12 inline comments.
- Do not post free-form issue comments outside review safe outputs.
