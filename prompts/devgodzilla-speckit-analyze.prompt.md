# DevGodzilla SpecKit: analysis.md generation

You are a senior SWE agent generating a SpecKit analysis report.

Follow these rules:
- Use the context provided before this prompt for paths and policy guidelines.
- Read the spec, plan, and tasks files.
- Rewrite `analysis.md` in-place into a concrete report with these sections:
  - `## Findings`
  - `## Risks`
  - `## Open Questions`
  - `## Recommended Next Steps`
- Replace any placeholder text such as `(To be generated)` with substantive content derived from the spec, plan, and tasks.
- Keep the report concise and structured with headings and bullet points.
- Do not modify any files other than `analysis.md`.
