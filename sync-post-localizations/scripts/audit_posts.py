#!/usr/bin/env python3
"""Audit canonical Markdown posts and locale sidecars for structural drift."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


POST_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
FRONTMATTER = re.compile(r"^---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)$", re.DOTALL)
FIELD = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*):\s*(?P<value>.*)$")
FENCE = re.compile(r"^```.*?^```\s*$", re.MULTILINE | re.DOTALL)
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
LATIN_WORD = re.compile(r"[A-Za-z]{2,}")
REQUIRED_SOURCE_FIELDS = {"title", "date", "summary", "tags", "draft"}
REQUIRED_TRANSLATION_FIELDS = {"title", "summary"}


@dataclass
class Document:
    path: Path
    fields: dict[str, str]
    body: str


def parse_document(path: Path) -> tuple[Document | None, list[str]]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    match = FRONTMATTER.match(text)
    if not match:
        return None, [f"{path}: missing or invalid frontmatter"]

    fields: dict[str, str] = {}
    for line in match.group("meta").splitlines():
        field = FIELD.match(line)
        if field:
            fields[field.group("key")] = field.group("value").strip().strip('"\'')

    return Document(path, fields, match.group("body")), errors


def prose_language(body: str) -> str:
    prose = FENCE.sub("", body)
    prose = re.sub(r"https?://\S+|`[^`]*`", "", prose)
    cjk_count = len(CJK.findall(prose))
    latin_count = len(LATIN_WORD.findall(prose))
    return "zh" if cjk_count >= max(20, latin_count * 2) else "en"


def title_language(title: str) -> str:
    cjk_count = len(CJK.findall(title))
    latin_count = len(LATIN_WORD.findall(title))
    if cjk_count and latin_count:
        return "mixed"
    if cjk_count:
        return "zh"
    return "en"


def audit(repo: Path, posts_dir: Path, translations_dir: Path) -> dict[str, object]:
    posts_root = repo / posts_dir
    translations_root = repo / translations_dir
    errors: list[str] = []
    warnings: list[str] = []
    post_records: list[dict[str, object]] = []

    if not posts_root.is_dir():
        return {"errors": [f"post directory not found: {posts_root}"], "warnings": [], "posts": []}

    locale_dirs = sorted(path for path in translations_root.iterdir() if path.is_dir()) if translations_root.is_dir() else []
    locales = [path.name for path in locale_dirs]
    sources = {path.name: path for path in posts_root.glob("*.md")}

    for name, path in sorted(sources.items()):
        if not POST_NAME.fullmatch(name):
            errors.append(f"{path}: expected YYYY-MM-DD-lowercase-kebab-slug.md")

        document, parse_errors = parse_document(path)
        errors.extend(parse_errors)
        if not document:
            continue

        missing_fields = sorted(REQUIRED_SOURCE_FIELDS - document.fields.keys())
        if missing_fields:
            errors.append(f"{path}: missing fields: {', '.join(missing_fields)}")

        source_locale = prose_language(document.body)
        title_locale = title_language(document.fields.get("title", ""))
        if title_locale not in {source_locale, "mixed"}:
            warnings.append(
                f"{path}: title appears {title_locale}, but body appears {source_locale}; translate the title"
            )

        missing_locales: list[str] = []
        for locale in locales:
            translation = translations_root / locale / "posts" / name
            if locale == source_locale and not translation.exists():
                continue
            if not translation.exists():
                missing_locales.append(locale)
                errors.append(f"{translation}: missing {locale} translation for {name}")
                continue

            translated_document, translation_errors = parse_document(translation)
            errors.extend(translation_errors)
            if translated_document:
                missing = sorted(REQUIRED_TRANSLATION_FIELDS - translated_document.fields.keys())
                if missing:
                    errors.append(f"{translation}: missing fields: {', '.join(missing)}")

        post_records.append(
            {
                "file": str(path.relative_to(repo)),
                "source_locale": source_locale,
                "title_locale": title_locale,
                "missing_locales": missing_locales,
            }
        )

    for locale_dir in locale_dirs:
        posts = locale_dir / "posts"
        if not posts.is_dir():
            continue
        for translation in sorted(posts.glob("*.md")):
            if translation.name not in sources:
                errors.append(f"{translation}: orphan translation without canonical post")

    return {"errors": errors, "warnings": warnings, "locales": locales, "posts": post_records}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--posts-dir", type=Path, default=Path("content/posts"))
    parser.add_argument("--translations-dir", type=Path, default=Path("content/translations"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = audit(args.repo.resolve(), args.posts_dir, args.translations_dir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for warning in report.get("warnings", []):
            print(f"WARNING: {warning}")
        for error in report.get("errors", []):
            print(f"ERROR: {error}")
        print(
            f"Audited {len(report.get('posts', []))} posts across "
            f"{len(report.get('locales', []))} locales: "
            f"{len(report.get('errors', []))} errors, {len(report.get('warnings', []))} warnings"
        )

    return 1 if report.get("errors") else 0


if __name__ == "__main__":
    sys.exit(main())
