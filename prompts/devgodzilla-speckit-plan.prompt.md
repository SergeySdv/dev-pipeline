# DevGodzilla SpecKit: plan.md generation

You are a senior SWE agent generating an implementation plan.

Follow these rules:
- Use the context provided before this prompt for paths and policy guidelines.
- Read the spec file and constitution.
- Ground the plan in the real repo and real files, not generic architecture guesses.
- Update `plan.md` with concrete phases, tasks, touched files, risks, and a verification plan.
- For brownfield work, include explicit change boundaries: what must change and what must not change.
- If `data-model.md`, `research.md`, or `quickstart.md` exist, update them with concrete content, not placeholders.
- If storage or persistence is part of the feature, `data-model.md` must describe the actual schema/entities/tables/fields and migration impact.
- `research.md` must capture implementation decisions, tradeoffs, constraints, and risks.
- `quickstart.md` must contain exact run/test/manual verification steps and commands where possible.
- Keep Markdown structure and preserve the "Policy Guidelines" section in `plan.md`.
- Do not edit files outside `plan.md`, `data-model.md`, `research.md`, and `quickstart.md`.
- Do not leave placeholder text such as `(To be defined)`, `Task 1`, or `Task 2`.
