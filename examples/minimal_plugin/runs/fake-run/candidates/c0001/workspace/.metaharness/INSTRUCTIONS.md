# MetaHarness Candidate Instructions

## Objective
Test the metaharness plugin system

## Constraints
- None

## Workspace Layout
The candidate workspace is the directory under optimization. The .metaharness directory contains run metadata, a compact environment bootstrap, and prior results.

## Allowed Actions
- Read and edit files inside the candidate workspace.
- Use the bootstrap snapshot under .metaharness/bootstrap to avoid redundant exploration.
- Inspect prior candidate artifacts under .metaharness.
- Use lightweight commands when needed to understand the workspace.

## Forbidden Actions
- Do not modify evaluation artifacts outside the current candidate workspace.
- Do not fabricate success. The external validator and evaluator decide outcomes.

## Evaluation Contract
Your job is to improve the harness so that external validation passes and the objective score increases relative to the parent candidate (c0000).
