# Configuration Notes

`config.json` controls context collection, agent backend commands, timeouts, output paths, and the maximum number of cycles.

Backend commands may use these placeholders:

- `{cwd}`: target skill root or reviewed repository path.
- `{prompt_file}`: temporary file containing the full prompt.
- `{prompt}`: full prompt passed as a command argument.

Prefer `{prompt_file}` or stdin for large prompts so command lines do not expose full prompt content. Keep `runs/**`, virtual environments, caches, generated files, and secrets out of context with `context_excludes`.
