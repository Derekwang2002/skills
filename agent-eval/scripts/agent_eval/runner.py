import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

try:
    from langgraph.graph import END, StateGraph
except ModuleNotFoundError:
    END = None
    StateGraph = None


ROOT = Path(__file__).resolve().parent


class LoopState(TypedDict):
    config: Dict[str, Any]
    config_path: str
    skill_root: str
    skill_path: str
    evals_path: str
    runs_dir: str
    cycle: int
    max_cycles: int
    review: Dict[str, Any]
    last_error: Optional[str]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return default
    return json.loads(content)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_template(name: str) -> str:
    return read_text(ROOT / "prompts" / name)


def is_binary_like(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:2048]
    except OSError:
        return True
    return b"\0" in chunk


def matches_any(path: str, patterns: List[str]) -> bool:
    normalized = path.replace(os.sep, "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern):
            return True
        if pattern.endswith("/**") and normalized.startswith(pattern[:-3].rstrip("/") + "/"):
            return True
    return False


def collect_skill_context(
    skill_root: Path,
    skill_path: Path,
    include_patterns: List[str],
    exclude_patterns: List[str],
    max_context_bytes: int,
) -> str:
    if not skill_root.exists():
        return f"[skill root does not exist: {skill_root}]"

    included: Dict[str, Path] = {}
    for pattern in include_patterns:
        for path in skill_root.glob(pattern):
            if path.is_dir():
                continue
            rel = path.relative_to(skill_root).as_posix()
            if matches_any(rel, exclude_patterns):
                continue
            if path.resolve() == skill_path.resolve():
                continue
            included[rel] = path

    if not included:
        return "[no additional context files matched]"

    parts: List[str] = []
    used = 0
    skipped: List[str] = []

    for rel in sorted(included):
        path = included[rel]
        if is_binary_like(path):
            skipped.append(f"{rel} (binary-like)")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append(f"{rel} (not utf-8 text)")
            continue
        except OSError as exc:
            skipped.append(f"{rel} ({exc})")
            continue

        block = f"\n--- FILE: {rel} ---\n{content}\n"
        block_bytes = len(block.encode("utf-8"))
        if used + block_bytes > max_context_bytes:
            skipped.append(f"{rel} (context byte limit reached)")
            continue
        parts.append(block)
        used += block_bytes

    if skipped:
        parts.append("\n--- SKIPPED CONTEXT FILES ---\n" + "\n".join(skipped) + "\n")

    return "".join(parts).strip() or "[no readable additional context files matched]"


def render_template(template: str, values: Dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()
    if stripped.endswith("```"):
        stripped = stripped[: -3].strip()
    return stripped


def extract_json_object(text: str) -> Dict[str, Any]:
    cleaned = strip_json_fences(text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in reviewer output")

    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("Reviewer output JSON is not an object")
    return parsed


def normalize_review(review: Dict[str, Any]) -> Dict[str, Any]:
    result = str(review.get("result", "")).upper()
    blockers = review.get("blockers", [])
    if result not in {"PASS", "FAIL"}:
        raise ValueError("Reviewer JSON must contain result PASS or FAIL")
    if not isinstance(blockers, list):
        raise ValueError("Reviewer JSON blockers must be a list")
    if result == "PASS":
        blockers = []
    return {"result": result, "blockers": blockers[:3]}


def get_reviewer_config(config: Dict[str, Any]) -> Dict[str, Any]:
    reviewer_backends = config.get("reviewer_backends")
    if reviewer_backends:
        reviewer_backend = config.get("reviewer_backend")
        if not reviewer_backend:
            reviewer_backend = config.get("reviewer", {}).get("backend")
        if not reviewer_backend:
            raise ValueError("Missing reviewer_backend")
        if reviewer_backend not in reviewer_backends:
            raise ValueError(f"Unknown reviewer backend: {reviewer_backend}")
        return {**reviewer_backends[reviewer_backend], "backend": reviewer_backend}

    if "reviewer" not in config:
        raise ValueError("Missing reviewer configuration")
    return config["reviewer"]


def apply_runtime_overrides(
    config: Dict[str, Any],
    max_cycles_arg: Optional[int],
    review_only: bool,
    review_diff: bool,
) -> tuple[Dict[str, Any], int]:
    runtime_config = dict(config)
    if review_only or review_diff:
        runtime_config["auto_append_review_evals"] = False
        return runtime_config, 0

    max_cycles = max_cycles_arg if max_cycles_arg is not None else int(config.get("max_cycles", 3))
    return runtime_config, max_cycles


def run_text_command(command: List[str], cwd: Path) -> str:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        cwd=str(cwd),
        check=False,
    )
    output = result.stdout.strip()
    error = result.stderr.strip()
    if result.returncode == 0:
        return output or "[no output]"
    return "\n".join(
        part
        for part in [
            f"[command failed with exit code {result.returncode}: {' '.join(command)}]",
            "STDOUT:",
            output,
            "STDERR:",
            error,
        ]
        if part
    )


def parse_status_paths(status_text: str) -> List[str]:
    paths: List[str] = []
    for line in status_text.splitlines():
        if len(line) < 4:
            continue
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if path_text:
            paths.append(path_text)
    return sorted(set(paths))


def read_bounded_text(path: Path, max_bytes: int) -> str:
    if not path.exists() or not path.is_file():
        return f"[missing file: {path}]"
    if is_binary_like(path):
        return f"[binary-like file skipped: {path}]"
    content = path.read_text(encoding="utf-8", errors="replace")
    encoded = content.encode("utf-8")
    if len(encoded) <= max_bytes:
        return content
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n[truncated]\n"


def build_git_diff_review_subject(repo_root: Path, max_bytes: int) -> str:
    repo_root = repo_root.resolve()
    status = run_text_command(["git", "status", "--short"], repo_root)
    diff_stat = run_text_command(["git", "diff", "--stat"], repo_root)
    staged_diff = run_text_command(["git", "diff", "--cached"], repo_root)
    unstaged_diff = run_text_command(["git", "diff"], repo_root)

    parts = [
        "# Git Diff Review",
        f"Repository: {repo_root}",
        "",
        "## Git Status",
        status,
        "",
        "## Git Diff Stat",
        diff_stat,
        "",
        "## Staged Diff",
        staged_diff,
        "",
        "## Unstaged Diff",
        unstaged_diff,
    ]

    for agent_name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        agent_path = repo_root / agent_name
        if agent_path.exists():
            parts.extend(["", f"## {agent_name}", read_bounded_text(agent_path, 20000)])

    changed_paths = parse_status_paths(status)
    if changed_paths:
        parts.extend(["", "## Changed File Snapshots"])
        remaining = max(max_bytes // 4, 10000)
        for rel_path in changed_paths:
            file_path = repo_root / rel_path
            snapshot = read_bounded_text(file_path, min(remaining, 20000))
            parts.extend(["", f"--- FILE: {rel_path} ---", snapshot])
            remaining -= len(snapshot.encode("utf-8"))
            if remaining <= 0:
                parts.append("[changed file snapshot byte budget reached]")
                break

    subject = "\n".join(parts)
    encoded = subject.encode("utf-8")
    if len(encoded) <= max_bytes:
        return subject
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n[review subject truncated]\n"


def summarize_for_retry(raw_output: str, raw_error: str, max_chars: int = 2000) -> str:
    combined = (raw_output + ("\n\nSTDERR:\n" + raw_error if raw_error else "")).strip()
    if len(combined) <= max_chars:
        return combined
    return combined[:max_chars] + "\n[truncated]\n"


def run_agent_command(
    command: List[str],
    prompt: str,
    cwd: Path,
    timeout_seconds: int,
    prompt_file_path: Path,
) -> subprocess.CompletedProcess[str]:
    write_text(prompt_file_path, prompt)

    uses_prompt_arg = any("{prompt}" in part for part in command)
    uses_prompt_file = any("{prompt_file}" in part for part in command)

    rendered_command = [
        part.replace("{prompt}", prompt)
        .replace("{prompt_file}", str(prompt_file_path))
        .replace("{cwd}", str(cwd))
        for part in command
    ]

    stdin = None if uses_prompt_arg or uses_prompt_file else prompt

    return subprocess.run(
        rendered_command,
        input=stdin,
        text=True,
        capture_output=True,
        cwd=str(cwd),
        timeout=timeout_seconds,
        check=False,
    )


def make_cycle_dir(runs_dir: Path, cycle: int) -> Path:
    cycle_dir = runs_dir / f"cycle-{cycle:03d}"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    return cycle_dir


def eval_identity(item: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "input": item.get("input", ""),
            "expected": item.get("expected", ""),
            "not_expected": item.get("not_expected", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def append_review_evals(evals_path: Path, blockers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evals = read_json(evals_path, [])
    if not isinstance(evals, list):
        raise ValueError(f"{evals_path} must contain a JSON array")

    existing = {eval_identity(item) for item in evals if isinstance(item, dict)}
    added: List[Dict[str, Any]] = []

    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        candidate = blocker.get("eval")
        if not isinstance(candidate, dict):
            continue
        eval_item = {
            "id": f"review-{blocker.get('id', 'blocker')}",
            "source": "reviewer-blocker",
            "blocker_title": blocker.get("title", ""),
            "input": candidate.get("input", blocker.get("repro_input", "")),
            "expected": candidate.get("expected", blocker.get("expected_behavior", "")),
            "not_expected": candidate.get("not_expected", blocker.get("bad_behavior", "")),
            "pass_criteria": candidate.get("pass_criteria", ""),
        }
        identity = eval_identity(eval_item)
        if identity in existing:
            continue
        evals.append(eval_item)
        existing.add(identity)
        added.append(eval_item)

    if added:
        write_json(evals_path, evals)
    return added


def reviewer_node(state: LoopState) -> LoopState:
    config = state["config"]
    skill_root = Path(state["skill_root"]).resolve()
    skill_path = Path(state["skill_path"]).resolve()
    evals_path = Path(state["evals_path"]).resolve()
    runs_dir = Path(state["runs_dir"]).resolve()
    cycle_dir = make_cycle_dir(runs_dir, state["cycle"])

    skill = str(config.get("review_subject_text") or read_text(skill_path))
    evals = read_json(evals_path, [])
    reviewer_config = get_reviewer_config(config)
    skill_context = collect_skill_context(
        skill_root=skill_root,
        skill_path=skill_path,
        include_patterns=config.get("context_includes", ["SKILL.md"]),
        exclude_patterns=config.get("context_excludes", []),
        max_context_bytes=int(config.get("max_context_bytes", 120000)),
    )

    prompt = render_template(
        load_template("reviewer.md"),
        {
            "skill_root": str(skill_root),
            "skill_path": str(skill_path),
            "evals_path": str(evals_path),
            "skill": skill,
            "skill_context": skill_context,
            "evals_json": json.dumps(evals, ensure_ascii=False, indent=2),
            "cycle": state["cycle"],
            "max_cycles": state["max_cycles"],
        },
    )
    slash_command = reviewer_config.get("slash_command")
    if slash_command:
        prompt = f"{slash_command}\n\n{prompt}"

    parse_retries = int(reviewer_config.get("parse_retries", 0))
    prompt_for_attempt = prompt
    last_parse_error: Optional[Exception] = None

    for attempt in range(parse_retries + 1):
        prompt_file_name = "review.prompt.md" if attempt == 0 else f"review.retry-{attempt:03d}.prompt.md"
        raw_file_name = "review.raw.txt" if attempt == 0 else f"review.retry-{attempt:03d}.raw.txt"
        result = run_agent_command(
            command=reviewer_config["command"],
            prompt=prompt_for_attempt,
            cwd=skill_root,
            timeout_seconds=int(reviewer_config.get("timeout_seconds", 900)),
            prompt_file_path=cycle_dir / prompt_file_name,
        )

        raw_output = result.stdout.strip()
        raw_error = result.stderr.strip()
        write_text(cycle_dir / raw_file_name, raw_output + ("\n\nSTDERR:\n" + raw_error if raw_error else ""))

        if result.returncode != 0:
            return {**state, "last_error": f"Reviewer command failed with exit code {result.returncode}"}

        try:
            review = normalize_review(extract_json_object(raw_output))
        except (ValueError, json.JSONDecodeError) as exc:
            last_parse_error = exc
            if attempt >= parse_retries:
                write_text(cycle_dir / "review.parse_error.txt", str(exc))
                return {
                    **state,
                    "last_error": (
                        "Reviewer output was not valid JSON: "
                        f"{exc}. Raw output saved under {cycle_dir}"
                    ),
                }
            prompt_for_attempt = (
                prompt
                + "\n\nPrevious reviewer output was not valid JSON. "
                + "Return only the required JSON object on this retry.\n\n"
                + "Previous output summary:\n"
                + summarize_for_retry(raw_output, raw_error)
            )
            continue

        write_json(cycle_dir / "review.json", review)
        return {**state, "review": review, "last_error": None}

    return {
        **state,
        "last_error": f"Reviewer output was not valid JSON: {last_parse_error}",
    }


def fixer_node(state: LoopState) -> LoopState:
    config = state["config"]
    skill_root = Path(state["skill_root"]).resolve()
    skill_path = Path(state["skill_path"]).resolve()
    evals_path = Path(state["evals_path"]).resolve()
    runs_dir = Path(state["runs_dir"]).resolve()
    cycle_dir = make_cycle_dir(runs_dir, state["cycle"])

    review = state["review"]
    blockers = review.get("blockers", [])
    write_json(cycle_dir / "blockers.json", blockers)

    if config.get("auto_append_review_evals", True):
        added = append_review_evals(evals_path, blockers)
        write_json(cycle_dir / "added_evals.json", added)

    fixer_backend_name = config["fixer_backend"]
    fixer_config = config["fixer_backends"][fixer_backend_name]
    skill = read_text(skill_path)
    evals = read_json(evals_path, [])
    skill_context = collect_skill_context(
        skill_root=skill_root,
        skill_path=skill_path,
        include_patterns=config.get("context_includes", ["SKILL.md"]),
        exclude_patterns=config.get("context_excludes", []),
        max_context_bytes=int(config.get("max_context_bytes", 120000)),
    )

    prompt = render_template(
        load_template("fixer.md"),
        {
            "skill_root": str(skill_root),
            "skill_path": str(skill_path),
            "evals_path": str(evals_path),
            "skill": skill,
            "skill_context": skill_context,
            "evals_json": json.dumps(evals, ensure_ascii=False, indent=2),
            "blockers_json": json.dumps(blockers, ensure_ascii=False, indent=2),
        },
    )

    result = run_agent_command(
        command=fixer_config["command"],
        prompt=prompt,
        cwd=skill_root,
        timeout_seconds=int(fixer_config.get("timeout_seconds", 1200)),
        prompt_file_path=cycle_dir / "fixer.prompt.md",
    )

    raw_output = result.stdout.strip()
    raw_error = result.stderr.strip()
    write_text(cycle_dir / "fixer.raw.txt", raw_output + ("\n\nSTDERR:\n" + raw_error if raw_error else ""))

    if result.returncode != 0:
        return {
            **state,
            "cycle": state["cycle"] + 1,
            "last_error": f"Fixer backend {fixer_backend_name} failed with exit code {result.returncode}",
        }

    eval_command = config.get("eval_command")
    if eval_command:
        eval_result = subprocess.run(
            eval_command,
            text=True,
            capture_output=True,
            cwd=str(ROOT),
            shell=isinstance(eval_command, str),
            check=False,
        )
        write_text(
            cycle_dir / "eval.raw.txt",
            eval_result.stdout + ("\n\nSTDERR:\n" + eval_result.stderr if eval_result.stderr else ""),
        )
        if eval_result.returncode != 0:
            return {
                **state,
                "cycle": state["cycle"] + 1,
                "last_error": f"Eval command failed with exit code {eval_result.returncode}",
            }

    return {**state, "cycle": state["cycle"] + 1, "last_error": None}


def route_after_review(state: LoopState) -> str:
    if state.get("last_error"):
        return "done"
    if state["review"].get("result") == "PASS":
        return "done"
    if state["cycle"] >= state["max_cycles"]:
        return "done"
    return "fix"


def build_graph():
    if StateGraph is None or END is None:
        raise RuntimeError("Missing dependency: run `pip install -r requirements.txt` first")

    graph = StateGraph(LoopState)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("fixer", fixer_node)
    graph.set_entry_point("reviewer")
    graph.add_conditional_edges("reviewer", route_after_review, {"fix": "fixer", "done": END})
    graph.add_edge("fixer", "reviewer")
    return graph.compile()


def resolve_path(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (config_path.parent / path).resolve()


def find_review_anchor_path(repo_root: Path) -> Optional[Path]:
    for name in ("AGENTS.md", "README.md", ".gitignore"):
        candidate = repo_root / name
        if candidate.exists() and candidate.is_file():
            return candidate
    for candidate in sorted(repo_root.iterdir()):
        if candidate.is_file():
            return candidate
    return None


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded reviewer/fixer loop for a skill file.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument("--skill-root", default=None, help="Override skill root directory from config")
    parser.add_argument("--skill", default=None, help="Override skill path from config")
    parser.add_argument("--max-cycles", type=int, default=None, help="Override max_cycles from config")
    parser.add_argument("--review-only", action="store_true", help="Run reviewer once and never invoke fixer")
    parser.add_argument(
        "--review-diff",
        nargs="?",
        const=".",
        default=None,
        help="Review uncommitted git changes in the given repository path",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config).expanduser().resolve()
    config = read_json(config_path, {})
    if not config:
        print(f"Missing or empty config: {config_path}", file=sys.stderr)
        return 2

    review_diff_root = Path(args.review_diff).expanduser().resolve() if args.review_diff else None
    config, max_cycles = apply_runtime_overrides(
        config,
        max_cycles_arg=args.max_cycles,
        review_only=args.review_only,
        review_diff=review_diff_root is not None,
    )

    if review_diff_root is not None:
        skill_root = review_diff_root
        skill_path = (
            Path(args.skill).expanduser().resolve()
            if args.skill
            else find_review_anchor_path(review_diff_root)
        )
        config["review_subject_text"] = build_git_diff_review_subject(
            review_diff_root,
            int(config.get("max_context_bytes", 120000)),
        )
    else:
        skill_root = resolve_path(config_path, args.skill_root or config.get("skill_root", "."))
        skill_path = resolve_path(config_path, args.skill or config["skill_path"])

    evals_path = resolve_path(config_path, config["evals_path"])
    runs_dir = resolve_path(config_path, config["runs_dir"])

    if not skill_root.exists() or not skill_root.is_dir():
        print(f"Skill root directory does not exist: {skill_root}", file=sys.stderr)
        return 2
    if skill_path is None or not skill_path.exists():
        print(f"Skill file does not exist: {skill_path}", file=sys.stderr)
        return 2
    try:
        skill_path.resolve().relative_to(skill_root.resolve())
    except ValueError:
        print(f"Skill file must be inside skill root: {skill_path} not under {skill_root}", file=sys.stderr)
        return 2
    if not evals_path.exists():
        write_json(evals_path, [])

    app = build_graph()

    final_state = app.invoke(
        {
            "config": config,
            "config_path": str(config_path),
            "skill_root": str(skill_root),
            "skill_path": str(skill_path),
            "evals_path": str(evals_path),
            "runs_dir": str(runs_dir),
            "cycle": 0,
            "max_cycles": max_cycles,
            "review": {},
            "last_error": None,
        }
    )

    print(json.dumps({
        "final_result": final_state.get("review", {}).get("result"),
        "cycles_used": final_state.get("cycle"),
        "last_error": final_state.get("last_error"),
        "skill_root": final_state.get("skill_root"),
        "runs_dir": str(runs_dir),
    }, ensure_ascii=False, indent=2))

    return 1 if final_state.get("last_error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
