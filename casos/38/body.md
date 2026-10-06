
# Sync - Issue Triage

Triage issue **#${{ needs.pre_activation.outputs.issue_number }}** using the issue-triage skill, then apply labels and update the SkiaSharp Backlog project board.

## Step 1 — Run the issue-triage skill

Read and follow the instructions in `.agents/skills/issue-triage/SKILL.md` to triage issue #${{ needs.pre_activation.outputs.issue_number }}.

Complete all phases (Setup → Investigate → Analyze → Workarounds → Validate → Persist).

After Phase 6 completes, the triage JSON will be at `issue-triage-workspace/${{ needs.pre_activation.outputs.issue_number }}.json`.

## Step 2 — Apply labels from classification

Read the triage JSON file and extract the classification labels. Apply each label to the issue:

- `classification.type.value` — the issue type label (e.g. `type/bug`)
- `classification.area.value` — the component area label (e.g. `area/SkiaSharp`)
- Each entry in `classification.platforms[]` — platform labels (e.g. `os/Android`)
- Each entry in `classification.backends[]` — backend labels (e.g. `backend/Metal`)
- Each entry in `classification.tenets[]` — quality tenet labels (e.g. `tenet/compatibility`)
- `classification.partner` — partner label if present (e.g. `partner/maui`)

After applying classification labels, also add the `triage/triaged` label to mark the issue as processed.

Only apply labels that are non-null and non-empty. Skip any classification field that is absent or null.

## Step 3 — Update project board fields

Read the triage JSON and update the issue in the **SkiaSharp Backlog** project (https://github.com/orgs/mono/projects/1) with these custom fields:

| Project Field | JSON Path | Notes |
|--------------|-----------|-------|
| Severity | `evidence.bugSignals.severity` | SINGLE_SELECT: critical, high, medium, low. Skip if null. |
| Suggested Action | `output.actionability.suggestedAction` | SINGLE_SELECT: needs-investigation, close-as-fixed, etc. |
| Confidence | `output.actionability.confidence` | NUMBER: 0.0–1.0. |
| Repro Quality | `evidence.bugSignals.reproQuality` | SINGLE_SELECT: complete, partial, none. Skip if null. |
| Error Type | `evidence.bugSignals.errorType` | SINGLE_SELECT: crash, exception, wrong-output, etc. Skip if null. |
| Triage Summary | `analysis.summary` | TEXT: root cause hypothesis. Truncate to 1024 chars. |
| Suggested Repro Platform | `output.actionability.suggestedReproPlatform` | SINGLE_SELECT: linux, macos, windows. Skip if null. |

The `update-project` safe output auto-creates missing SINGLE_SELECT options — no need to pre-create values.

Use `content_type: "issue"` and issue number `${{ needs.pre_activation.outputs.issue_number }}` to identify the item.

Only include fields that have non-null values in the triage JSON. Omit any field where the source value is null or absent.

## Step 4 — Upload triage reports and write step summary

Copy the triage output files into `/tmp/gh-aw/agent/ai-triage/{number}/` so they are included in the workflow's `agent` artifact and can be persisted to the `aw-data` branch. Then write the Markdown report to the step summary so it's visible on the Actions run page without downloading artifacts.

```bash
NUM=${{ needs.pre_activation.outputs.issue_number }}
mkdir -p /tmp/gh-aw/agent/ai-triage/$NUM
cp output/ai-triage/$NUM/triage.json /tmp/gh-aw/agent/ai-triage/$NUM/
cp output/ai-triage/$NUM/triage.md /tmp/gh-aw/agent/ai-triage/$NUM/
cp output/ai-triage/$NUM/triage.html /tmp/gh-aw/agent/ai-triage/$NUM/
cat output/ai-triage/$NUM/triage.md >> /tmp/gh-aw/agent/step-summary.md
```

**IMPORTANT:** Write to the literal path `/tmp/gh-aw/agent/step-summary.md` — this file is symlinked to the step summary. Do NOT use `$GITHUB_STEP_SUMMARY` as it resolves to an inaccessible path.

All three files MUST be copied into `/tmp/gh-aw/agent/ai-triage/{number}/` and the markdown MUST be appended to `/tmp/gh-aw/agent/step-summary.md`. Verify they exist before finishing.
