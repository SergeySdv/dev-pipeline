# DevGodzilla SpecKit: tasks.md generation

You are a senior SWE agent generating an actionable task list.

Follow these rules:
- Use the context provided before this prompt for paths.
- Read the spec and plan files.
- Update `tasks.md` with detailed tasks grouped by phase.
- Use Markdown phase headings in the form `## Phase N: Title` before each task group.
- Use "- [ ]" checkboxes; mark parallelizable tasks with "[P]".
- Keep phase titles short, unique, and implementation-oriented.
- Produce one coherent task breakdown only; do not include alternative plans or duplicate phases.
- Prefer 3-7 phases unless the source material clearly requires more.
- End with a final verification/testing phase when appropriate.
- Keep tasks realistic, ordered, and specific.
- Reference real files, functions, modules, tests, commands, and boundaries from the repo whenever the plan provides them.
- Do not emit generic placeholders such as `Task 1`, `Task 2`, or file-free tasks.
- Use concrete repository paths when you can infer them from the repo.
- Remove every sample/template block and placeholder token from the final file.
- Do not leave `IMPORTANT: The tasks below are SAMPLE TASKS`, `Initialize [language] project`, `[endpoint]`, `[Title]`, `TXXX`, or similar placeholders in the final file.
- Do not modify any files other than `tasks.md`.
