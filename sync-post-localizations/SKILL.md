---
name: sync-post-localizations
description: Use when Markdown posts under content/posts or an equivalent canonical post directory are added, edited, renamed, or deleted; when localized copies may be missing or stale; or when the user asks to synchronize or publish post changes across locales and coupled routing, metadata, navigation, sitemap, or feed behavior.
---

# Sync Post Localizations

Keep changed posts, localized copies, and derived site behavior consistent. Complete the whole workflow; do not stop after reporting mismatches.

## 1. Establish scope

1. Inspect repository instructions and `git status -sb` before editing.
2. Locate the canonical post directory, translation directories, Markdown loader, locale routing helpers, sitemap, RSS/feed code, and deployment checks. Do not assume one repository's paths in another project.
3. Use `git diff --name-status`, including staged and untracked files, to identify added, edited, renamed, and deleted posts.
4. Preserve unrelated user changes. Stage only post changes and coupled files belonging to this task.

Run the bundled audit when the repository uses the conventional layout:

```bash
python3 <skill-dir>/scripts/audit_posts.py --repo <repo-root>
```

Pass `--posts-dir` and `--translations-dir` for other layouts. Treat audit errors as work to fix, not as a substitute for inspecting the application.

## 2. Determine the canonical language

Treat the file in the canonical post directory as the source of truth. Infer its main language from prose in the body, excluding frontmatter, fenced code, URLs, identifiers, and proper nouns. Prefer an explicit locale field or repository mapping when one exists and agrees with the content.

Ensure `title` and `summary` use the source language. Translate mismatched natural-language wording into the source language while preserving names such as GitHub, Docker, Skills, API names, code identifiers, and external brands. A mixed title is valid only when the non-source-language tokens are proper nouns or technical terms.

Never change `date`, `tags`, `selected`, `draft`, or other semantic frontmatter merely to localize text.

## 3. Synchronize every locale

Discover supported content locales from the application configuration and translation directories. For every changed source post:

1. Create or update the corresponding document for every non-source locale using the exact basename and repository frontmatter format.
2. Translate the complete title, summary, headings, paragraphs, lists, blockquotes, and table prose. Do not omit sections, summarize, use placeholders, or claim a translation is complete when source-language prose remains unintentionally.
3. Preserve Markdown structure, heading levels, code fences, code, commands, file paths, URLs, HTML, formulas, anchors, and link targets.
4. Keep approved proper nouns and external site names untranslated. Translate explanatory text around them.
5. When a translation already exists, retain good human wording but synchronize every changed source section. Remove content deleted from the source.
6. Keep source and translations structurally aligned. Compare heading and fence counts, then scan each translation for unexpected source-language prose.

If the application requires a same-language sidecar, maintain it. Otherwise prefer the canonical post itself for its source locale and avoid redundant copies.

## 4. Repair coupled behavior

Inspect and update only what the post change affects:

- Normalize filenames to the loader's date/slug rules.
- Rename every translation to the same basename.
- Update hardcoded slug or source-locale maps, internal links, navigation entries, tests, fixtures, metadata, and content registries.
- Preserve old public URLs with permanent redirects when a published slug changes; cover every locale route.
- Confirm canonical and alternate-language URLs resolve.
- Confirm sitemap and RSS/feed output include only valid localized pages and use the new slug.
- Confirm `selected`, `draft`, tags, dates, and sorting flow from canonical frontmatter without duplicating edits unnecessarily.

Do not hand-edit generated build artifacts.

## 5. Validate

Run the audit again, then run the repository's lint, typecheck, tests, and production build in proportion to the change. Inspect generated output for:

- each locale route and localized title;
- redirects for renamed slugs;
- sitemap and feed URLs;
- selected/draft visibility;
- real rendered Markdown elements needed by the changed content.

Run `git diff --check`. Revert unrelated generated-file churn with a targeted patch. Review the final diff and confirm no translation or source file is orphaned.

## 6. Commit and push

Treat invocation of this Skill as authorization to publish the completed post synchronization only when the user requested the full workflow.

1. Confirm the final worktree contains no unrelated changes. If it does, stage explicit in-scope paths only.
2. Commit with a terse message describing the content synchronization.
3. Push the current branch to its configured origin. When the user explicitly requested direct publication from `main`, push `main`; do not create an unsolicited PR.
4. Verify local `HEAD` equals the remote-tracking branch and report the commit, validation, routes, and any intentionally unsupported locale.

Never commit or push while translations are incomplete or validation is failing.
