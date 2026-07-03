"""Console script entrypoint for agent-eval."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from . import runner


HELP = """usage: agent-eval <command> [options]

Commands:
  review-diff [repo]      Review staged and unstaged git changes without fixing
  review-skill [skill]    Review a skill directory without editing
  fix-loop [skill]        Run the bounded reviewer/fixer loop

Examples:
  agent-eval review-diff /path/to/repo
  agent-eval review-skill /path/to/skill
  agent-eval fix-loop /path/to/skill --max-cycles 2

Legacy runner flags are still accepted, for example:
  agent-eval --review-diff /path/to/repo
"""


def _skill_path_args(skill_root: str, rest: list[str]) -> list[str]:
    translated = ["--skill-root", skill_root]
    if "--skill" not in rest:
        translated.extend(["--skill", str(Path(skill_root) / "SKILL.md")])
    translated.extend(rest)
    return translated


def translate_args(argv: Sequence[str]) -> list[str]:
    args = list(argv)
    if not args:
        return []

    command, rest = args[0], args[1:]
    if command == "review-diff":
        return ["--review-diff", *rest]

    if command == "review-skill":
        translated = ["--review-only"]
        if rest and not rest[0].startswith("-"):
            return translated + _skill_path_args(rest[0], rest[1:])
        return translated + rest

    if command == "fix-loop":
        if rest and not rest[0].startswith("-"):
            return _skill_path_args(rest[0], rest[1:])
        return rest

    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["-h"], ["--help"]):
        print(HELP)
        return 0
    return runner.main(translate_args(args))


if __name__ == "__main__":
    raise SystemExit(main())
