---
name: agent-eval
description: Run reusable reviewer/fixer loops for agent skills or git diffs when asked to review a skill, inspect uncommitted changes, or use the local agent-eval CLI.
---

# Agent Eval

Use this skill when the task is to evaluate an agent skill, review local repository changes, or run the bounded reviewer/fixer loop packaged by this project.

## Quick Choice

- Review uncommitted changes only: `agent-eval review-diff /path/to/repo`
- Review a skill without editing: `agent-eval review-skill /path/to/skill`
- Let the framework review and fix a skill: `agent-eval fix-loop /path/to/skill --max-cycles 2`

Prefer review-only workflows unless the user explicitly asks to modify files.

## Review a Git Diff

Run this for code review of local staged or unstaged changes:

```bash
agent-eval review-diff /path/to/repo
```

This mode includes `git status`, diffs, root instruction files such as `AGENTS.md`, and bounded snapshots of changed text files. It does not invoke the fixer and does not append generated evals.

## Review or Fix a Skill

Use `review-skill` for a one-pass skill review:

```bash
agent-eval review-skill /path/to/my-skill
```

Use `fix-loop` only when edits are desired:

```bash
agent-eval fix-loop /path/to/my-skill --config config.json --max-cycles 3
```

The skill root defaults to the provided directory and the skill file defaults to `SKILL.md` inside that directory.

## Configuration

`config.json` controls backend commands, prompt transport, context include/exclude globs, timeout values, run output paths, and cycle limits. Keep generated artifacts, virtual environments, caches, and secrets excluded from context.

Backend commands may pass prompts through stdin, `{prompt_file}`, or `{prompt}`. Prefer stdin or `{prompt_file}` for large prompts.

## References

- `references/workflows.md`: detailed command selection and expected behavior.
- `references/configuration.md`: backend command placeholders and context guidance.
