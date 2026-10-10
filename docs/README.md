# PHOENIX documentation

## Start here

1. `DESIGN.md` — what PHOENIX should do and what is deliberately deferred.
2. `ARCHITECTURE.md` — the scan flow and runtime approach.
3. `COMPONENTS.md` — responsibility and boundary of each component.
4. `DATA_CONTRACTS.md` — the shared records exchanged between components.
5. `IMPLEMENTATION_GUIDE.md` — proposed small file structure and build order.
6. `TESTING_AND_ACCEPTANCE.md` — critical tests and demo acceptance criteria.
7. `REUSE_AUDIT.md` — internal audit of source code that may be adapted.
8. `MVP_SIMPLIFICATION_REVIEW.md` — deliberate scope cuts and features to defer.
9. `DEPENDENCIES.md` — minimal dependencies, what to defer, and environment/secret rules.
10. `BUILD_WORKFLOW.md` — one task → tests → diff review → passing commit → next task.
11. `PREBUILD_READINESS.md` — what is settled and what must be checked before code changes.

## Source-of-truth order

- Root `DECISIONS.md` is the live record of decisions actually made during implementation.
- `DESIGN.md` defines product scope.
- `DATA_CONTRACTS.md` defines data meaning and names.
- Other docs explain architecture, implementation and verification.

These documents describe intended behaviour; they do not claim a component is already implemented. The repository and executed test results determine implementation status. If a conflict appears, call it out instead of silently changing a contract.

## Implementation cadence

Follow `BUILD_WORKFLOW.md`: finish one cohesive task, test it, inspect its diff, commit the passing checkpoint, and only then begin the next task. Do not write implementation code until the actual PHOENIX repository has been inspected and its baseline commands have been run.
