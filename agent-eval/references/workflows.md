# Agent Eval Workflows

## Review Uncommitted Git Changes

Use this when the user asks for a code review of local changes:

```bash
agent-eval review-diff /path/to/repo
```

This mode includes git status, staged and unstaged diffs, root instructions such as `AGENTS.md`, and bounded snapshots of changed text files. It never invokes the fixer.

## Review a Skill Without Editing

Use this when the user wants a skill quality review only:

```bash
agent-eval review-skill /path/to/skill
```

The command maps the directory to `--skill-root` and uses `SKILL.md` inside it by default.

## Run the Reviewer/Fixer Loop

Use this when the user explicitly wants the framework to modify a skill:

```bash
agent-eval fix-loop /path/to/skill --max-cycles 2
```

The loop stops when the reviewer passes the skill or when `max_cycles` is reached.
