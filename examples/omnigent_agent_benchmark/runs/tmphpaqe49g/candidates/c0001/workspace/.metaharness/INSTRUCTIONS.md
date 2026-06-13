# MetaHarness Candidate Instructions

## Objective
Improve a small Omnigent agent harness so its config, instructions, sandbox scope, policy, and reviewer skill are suitable for coding-agent use.

## Constraints
- Keep the agent declarative and file-backed.
- Focus edits on config.yaml, AGENTS.md, and skills.
- Do not add external service dependencies.
- Only modify files within the allowed write scope: config.yaml, AGENTS.md, skills

## Workspace Layout
The candidate workspace is the directory under optimization. The .metaharness directory contains run metadata, a compact environment bootstrap, and prior results.

## Allowed Actions
- Read and edit files inside the candidate workspace.
- Use the bootstrap snapshot under .metaharness/bootstrap to avoid redundant exploration.
- Inspect prior candidate artifacts under .metaharness.
- Use lightweight commands when needed to understand the workspace.

## Forbidden Actions
- Do not modify evaluation artifacts outside the current candidate workspace.
- Do not edit files outside the allowed write scope: config.yaml, AGENTS.md, skills
- Do not fabricate success. The external validator and evaluator decide outcomes.

## Evaluation Contract
Your job is to improve the harness so that external validation passes and the objective score increases relative to the parent candidate (c0000).

## Change Manifest
Before finishing, write `.metaharness/change_manifest.json`.

Use this JSON shape:

```json
{
  "schema_version": "metaharness.change_manifest.v1",
  "candidate_id": "<candidate id if known>",
  "parent_candidate_ids": ["<parent id>"],
  "changes": [
    {
      "id": "change-1",
      "component": "system_prompt | tool | tool_description | middleware | skill | memory | evaluator | orchestration | docs | other",
      "description": "What changed.",
      "files": ["relative/path.py"],
      "failure_pattern": "Observed failure pattern this addresses.",
      "evidence_refs": ["trace_evidence.md#section", "task-or-trace-id"],
      "root_cause": "Why the previous harness failed.",
      "targeted_fix": "Why this edit should fix it.",
      "predicted_fixes": ["task-id-expected-to-improve"],
      "risk_tasks": ["task-id-at-risk-of-regression"],
      "notes": "Optional implementation notes."
    }
  ]
}
```

Keep entries evidence-backed. Use empty arrays for `predicted_fixes` or `risk_tasks` when task-level ids are unavailable.
