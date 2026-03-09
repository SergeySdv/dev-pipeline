# DevGodzilla SpecKit: tasks.md generation

You are a senior SWE agent generating an actionable task list.

Follow these rules:
- Use the context provided before this prompt for paths.
- Read the spec and plan files.
- Update `tasks.md` with detailed tasks grouped by phase.
- Use "- [ ]" checkboxes; mark parallelizable tasks with "[P]".
- Keep tasks realistic, ordered, and specific.
- Use concrete repository paths when you can infer them from the repo.
- Remove every sample/template block and placeholder token from the final file.
- Do not leave `IMPORTANT: The tasks below are SAMPLE TASKS`, `Initialize [language] project`, `[endpoint]`, `[Title]`, `TXXX`, or similar placeholders in the final file.
- Do not modify any files other than `tasks.md`.
