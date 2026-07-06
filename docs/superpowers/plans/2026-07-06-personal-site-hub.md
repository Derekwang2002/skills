# Personal Site Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a nested `/hub` resource center to `Derekwang2002/vercel-site` so long-term notes, skills, and demos are discoverable through one Vercel-hosted personal site.

**Architecture:** Keep resources in a local TypeScript manifest, put filtering and sorting helpers in `lib/resources.ts`, and render `/hub` plus `/hub/[section]` from shared list/navigation components. Search is a small client component over static data, with no backend and no build-time GitHub API calls.

**Tech Stack:** Next.js App Router, React 19, TypeScript, CSS Modules, existing Markdown blog routes.

---

## File Structure

Work in the `Derekwang2002/vercel-site` repository, not the `skills` repository.

- Create `content/resources.ts`: typed manifest and seed resource entries.
- Create `lib/resources.ts`: resource filtering, sorting, section resolution, and link helpers.
- Create `src/components/hub-nav.tsx`: hub secondary navigation.
- Create `src/components/hub-nav.module.css`: styles for hub secondary navigation.
- Create `src/components/resource-list.tsx`: client-side searchable resource list.
- Create `src/components/resource-list.module.css`: styles for resource search and rows.
- Create `src/app/hub/page.tsx`: all-resources hub page.
- Create `src/app/hub/page.module.css`: shared hub page layout styles.
- Create `src/app/hub/[section]/page.tsx`: nested section pages for notes, skills, and demos.
- Modify `src/app/layout.tsx`: add `Hub` to top-level navigation.

Do not add dependencies.

---

### Task 1: Add The Resource Manifest

**Files:**
- Create: `content/resources.ts`

- [ ] **Step 1: Create the manifest file**

Create `content/resources.ts` with this content:

```ts
export type ResourceType = "note" | "skill" | "demo";

export type ResourceStatus = "public" | "unlisted" | "draft";

export type ResourceSource = "vercel-site" | "skills" | "github-pages" | "external";

export type Resource = {
  title: string;
  description: string;
  type: ResourceType;
  href: string;
  source: ResourceSource;
  tags: string[];
  date?: string;
  status: ResourceStatus;
  featured?: boolean;
};

export const resources = [
  {
    title: "Skip List 跳表讲解",
    description: "交互式解释跳表的搜索、插入、层高和复杂度。",
    type: "demo",
    href: "https://derekwang2002.github.io/skills/leetcode-cookbook/",
    source: "github-pages",
    tags: ["algorithm", "data-structure", "visualization"],
    status: "public",
    featured: true
  },
  {
    title: "Agent Eval Skill",
    description: "用于 reviewer/fixer 循环的 Codex skill。",
    type: "skill",
    href: "https://github.com/Derekwang2002/skills/tree/main/agent-eval",
    source: "skills",
    tags: ["codex", "skill", "automation"],
    status: "public"
  },
  {
    title: "MySQL 八股",
    description: "MySQL 执行流程、存储、索引和事务学习记录。",
    type: "note",
    href: "/blog/mysql-notes",
    source: "vercel-site",
    tags: ["mysql", "database"],
    date: "2026-05-01",
    status: "public"
  }
] satisfies Resource[];
```

- [ ] **Step 2: Verify the manifest type-checks**

Run:

```bash
npm run typecheck
```

Expected: TypeScript completes with exit code 0.

- [ ] **Step 3: Commit**

```bash
git add content/resources.ts
git commit -m "Add resource manifest"
```

---

### Task 2: Add Resource Helpers

**Files:**
- Create: `lib/resources.ts`

- [ ] **Step 1: Create helper functions**

Create `lib/resources.ts` with this content:

```ts
import {
  resources,
  type Resource,
  type ResourceSource,
  type ResourceType
} from "../content/resources";

export type ResourceSection = "notes" | "skills" | "demos";

export type ResourceSectionDefinition = {
  slug: ResourceSection;
  label: string;
  type: ResourceType;
  description: string;
};

export const RESOURCE_SECTIONS: ResourceSectionDefinition[] = [
  {
    slug: "notes",
    label: "Notes",
    type: "note",
    description: "Long-term notes that live in the personal site repository."
  },
  {
    slug: "skills",
    label: "Skills",
    type: "skill",
    description: "Reusable skills and workflows maintained in external repositories."
  },
  {
    slug: "demos",
    label: "Demos",
    type: "demo",
    description: "Temporary HTML demos, explainers, and visual pages."
  }
];

const SOURCE_LABELS: Record<ResourceSource, string> = {
  "vercel-site": "Vercel site",
  skills: "Skills repo",
  "github-pages": "GitHub Pages",
  external: "External"
};

const TYPE_LABELS: Record<ResourceType, string> = {
  note: "Note",
  skill: "Skill",
  demo: "Demo"
};

export function getPublicResources(): Resource[] {
  return sortResources(resources.filter((resource) => resource.status !== "draft"));
}

export function getFeaturedResources(): Resource[] {
  return getPublicResources().filter(
    (resource) => resource.status === "public" && resource.featured === true
  );
}

export function getResourcesBySection(section: ResourceSection): Resource[] {
  const definition = getResourceSection(section);

  if (!definition) {
    return [];
  }

  return getPublicResources().filter((resource) => resource.type === definition.type);
}

export function getResourceSection(slug: string): ResourceSectionDefinition | undefined {
  return RESOURCE_SECTIONS.find((section) => section.slug === slug);
}

export function getResourceTypeLabel(type: ResourceType): string {
  return TYPE_LABELS[type];
}

export function getResourceSourceLabel(source: ResourceSource): string {
  return SOURCE_LABELS[source];
}

export function isExternalResourceHref(href: string): boolean {
  return /^https?:\/\//.test(href) || href.startsWith("mailto:");
}

function sortResources(items: readonly Resource[]): Resource[] {
  return [...items].sort((a, b) => {
    const aDate = a.date ?? "";
    const bDate = b.date ?? "";

    if (aDate && bDate && aDate !== bDate) {
      return bDate.localeCompare(aDate);
    }

    if (aDate !== bDate) {
      return aDate ? -1 : 1;
    }

    return a.title.localeCompare(b.title, "en", { sensitivity: "base" });
  });
}
```

- [ ] **Step 2: Verify helper types**

Run:

```bash
npm run typecheck
```

Expected: TypeScript completes with exit code 0.

- [ ] **Step 3: Commit**

```bash
git add lib/resources.ts
git commit -m "Add resource helpers"
```

---

### Task 3: Add Shared Hub Navigation

**Files:**
- Create: `src/components/hub-nav.tsx`
- Create: `src/components/hub-nav.module.css`

- [ ] **Step 1: Create the component**

Create `src/components/hub-nav.tsx` with this content:

```tsx
import Link from "next/link";
import { RESOURCE_SECTIONS, type ResourceSection } from "../../lib/resources";
import styles from "./hub-nav.module.css";

type HubNavProps = {
  active: "all" | ResourceSection;
};

export function HubNav({ active }: HubNavProps) {
  const items = [
    { slug: "all", label: "All", href: "/hub" },
    ...RESOURCE_SECTIONS.map((section) => ({
      slug: section.slug,
      label: section.label,
      href: `/hub/${section.slug}`
    }))
  ];

  return (
    <nav aria-label="Hub sections" className={styles.nav}>
      {items.map((item) => (
        <Link
          aria-current={active === item.slug ? "page" : undefined}
          className={active === item.slug ? `${styles.link} ${styles.active}` : styles.link}
          href={item.href}
          key={item.slug}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: Create the styles**

Create `src/components/hub-nav.module.css` with this content:

```css
.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin: 1rem 0 1.6rem;
}

.link {
  border: 1px solid #d8d8d8;
  color: #222222;
  padding: 0.28rem 0.6rem;
  text-decoration: none;
}

.link:hover,
.link:focus-visible {
  text-decoration: underline;
}

.active {
  border-color: #111111;
  color: #111111;
  font-weight: 700;
}
```

- [ ] **Step 3: Verify**

Run:

```bash
npm run typecheck
```

Expected: TypeScript completes with exit code 0.

- [ ] **Step 4: Commit**

```bash
git add src/components/hub-nav.tsx src/components/hub-nav.module.css
git commit -m "Add hub section navigation"
```

---

### Task 4: Add Searchable Resource List

**Files:**
- Create: `src/components/resource-list.tsx`
- Create: `src/components/resource-list.module.css`

- [ ] **Step 1: Create the client component**

Create `src/components/resource-list.tsx` with this content:

```tsx
"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  getResourceSourceLabel,
  getResourceTypeLabel,
  isExternalResourceHref
} from "../../lib/resources";
import type { Resource } from "../../content/resources";
import styles from "./resource-list.module.css";

type ResourceListProps = {
  resources: Resource[];
  title: string;
  emptyMessage: string;
  searchable?: boolean;
};

export function ResourceList({
  resources,
  title,
  emptyMessage,
  searchable = true
}: ResourceListProps) {
  const [query, setQuery] = useState("");

  const visibleResources = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    if (!normalizedQuery) {
      return resources;
    }

    return resources.filter((resource) => {
      const haystack = [
        resource.title,
        resource.description,
        resource.type,
        resource.source,
        resource.date ?? "",
        ...resource.tags
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalizedQuery);
    });
  }, [query, resources]);

  return (
    <section className={styles.section} aria-labelledby={`${toId(title)}-title`}>
      <div className={styles.header}>
        <h2 className={styles.title} id={`${toId(title)}-title`}>
          {title}
        </h2>
        <span className={styles.count}>{visibleResources.length}</span>
      </div>

      {searchable ? (
        <label className={styles.searchLabel}>
          <span>Search resources</span>
          <input
            aria-label="Search by title, tag, source, type, or date"
            className={styles.searchInput}
            onChange={(event) => setQuery(event.target.value)}
            type="search"
            value={query}
          />
        </label>
      ) : null}

      {visibleResources.length === 0 ? (
        <p className={styles.emptyState}>{emptyMessage}</p>
      ) : (
        <ul className={styles.list}>
          {visibleResources.map((resource) => (
            <li className={styles.item} key={`${resource.type}-${resource.href}`}>
              <ResourceLink resource={resource} />
              <p className={styles.description}>{resource.description}</p>
              <ResourceMeta resource={resource} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ResourceLink({ resource }: { resource: Resource }) {
  const external = isExternalResourceHref(resource.href);

  if (external) {
    return (
      <a className={styles.resourceLink} href={resource.href} rel="noreferrer" target="_blank">
        {resource.title}
      </a>
    );
  }

  return (
    <Link className={styles.resourceLink} href={resource.href}>
      {resource.title}
    </Link>
  );
}

function ResourceMeta({ resource }: { resource: Resource }) {
  const parts = [
    getResourceTypeLabel(resource.type),
    getResourceSourceLabel(resource.source),
    ...resource.tags,
    resource.date ?? ""
  ].filter(Boolean);

  return <p className={styles.meta}>{parts.join(" · ")}</p>;
}

function toId(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
```

- [ ] **Step 2: Create the styles**

Create `src/components/resource-list.module.css` with this content:

```css
.section {
  margin: 2rem 0 0;
}

.header {
  align-items: baseline;
  display: flex;
  gap: 0.65rem;
  justify-content: space-between;
}

.title {
  font-size: 1.25rem;
  line-height: 1.2;
  margin: 0;
}

.count {
  color: #666666;
  font-size: 0.92rem;
}

.searchLabel {
  display: grid;
  gap: 0.35rem;
  margin: 0.95rem 0 1.25rem;
}

.searchLabel span {
  color: #555555;
  font-size: 0.92rem;
}

.searchInput {
  border: 1px solid #d8d8d8;
  border-radius: 0;
  color: #111111;
  font: inherit;
  min-height: 2.35rem;
  padding: 0.35rem 0.55rem;
  width: 100%;
}

.list {
  display: grid;
  gap: 1.05rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.item {
  border-top: 1px solid #e5e5e5;
  padding-top: 0.9rem;
}

.resourceLink {
  color: #111111;
  font-size: 1.05rem;
  font-weight: 700;
  text-decoration: none;
}

.resourceLink:hover,
.resourceLink:focus-visible {
  text-decoration: underline;
}

.description {
  color: #333333;
  margin: 0.25rem 0 0;
}

.meta {
  color: #666666;
  font-size: 0.92rem;
  margin: 0.25rem 0 0;
}

.emptyState {
  color: #666666;
  margin: 0.95rem 0 0;
}
```

- [ ] **Step 3: Verify**

Run:

```bash
npm run typecheck
```

Expected: TypeScript completes with exit code 0.

- [ ] **Step 4: Commit**

```bash
git add src/components/resource-list.tsx src/components/resource-list.module.css
git commit -m "Add searchable resource list"
```

---

### Task 5: Add `/hub` Page

**Files:**
- Create: `src/app/hub/page.tsx`
- Create: `src/app/hub/page.module.css`

- [ ] **Step 1: Create the all-resources page**

Create `src/app/hub/page.tsx` with this content:

```tsx
import type { Metadata } from "next";
import { HubNav } from "@/components/hub-nav";
import { ResourceList } from "@/components/resource-list";
import { getFeaturedResources, getPublicResources } from "../../../lib/resources";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Hub",
  description: "Unified entry point for notes, skills, and demos.",
  openGraph: {
    title: "Hub | Personal Website",
    description: "Unified entry point for notes, skills, and demos.",
    url: "/hub",
    images: [
      {
        url: "/og-default.svg",
        width: 1200,
        height: 630,
        alt: "Hub Open Graph Image"
      }
    ]
  }
};

export default function HubPage() {
  const resources = getPublicResources();
  const featuredResources = getFeaturedResources();

  return (
    <main className={styles.hubPage}>
      <header className={styles.hero}>
        <h1 className={styles.title}>Hub</h1>
        <p className={styles.description}>
          One entry point for long-term notes, reusable skills, and temporary demos.
        </p>
      </header>

      <HubNav active="all" />

      {featuredResources.length > 0 ? (
        <ResourceList
          emptyMessage="No featured resources yet."
          resources={featuredResources}
          searchable={false}
          title="Featured"
        />
      ) : null}

      <ResourceList
        emptyMessage="No public resources yet."
        resources={resources}
        title="All Resources"
      />
    </main>
  );
}
```

- [ ] **Step 2: Create shared hub page styles**

Create `src/app/hub/page.module.css` with this content:

```css
.hubPage {
  max-width: 720px;
  margin: 0 auto;
  padding: 2.8rem 1rem 3.5rem;
}

.hero {
  margin: 0 0 0.5rem;
}

.title {
  font-size: clamp(1.9rem, 6vw, 2.8rem);
  line-height: 1.1;
  margin: 0 0 0.5rem;
}

.description {
  color: #555555;
  margin: 0;
}
```

- [ ] **Step 3: Verify**

Run:

```bash
npm run typecheck
npm run build
```

Expected: TypeScript completes with exit code 0, then Next.js builds successfully.

- [ ] **Step 4: Commit**

```bash
git add src/app/hub/page.tsx src/app/hub/page.module.css
git commit -m "Add hub index page"
```

---

### Task 6: Add Nested Hub Section Pages

**Files:**
- Create: `src/app/hub/[section]/page.tsx`

- [ ] **Step 1: Create the dynamic section route**

Create `src/app/hub/[section]/page.tsx` with this content:

```tsx
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { HubNav } from "@/components/hub-nav";
import { ResourceList } from "@/components/resource-list";
import {
  RESOURCE_SECTIONS,
  getResourceSection,
  getResourcesBySection,
  type ResourceSection
} from "../../../../lib/resources";
import styles from "../page.module.css";

type HubSectionPageProps = {
  params: Promise<{
    section: string;
  }>;
};

export function generateStaticParams() {
  return RESOURCE_SECTIONS.map((section) => ({
    section: section.slug
  }));
}

export async function generateMetadata({
  params
}: HubSectionPageProps): Promise<Metadata> {
  const { section: rawSection } = await params;
  const section = getResourceSection(rawSection);

  if (!section) {
    return {
      title: "Hub Section"
    };
  }

  return {
    title: section.label,
    description: section.description,
    openGraph: {
      title: `${section.label} | Personal Website`,
      description: section.description,
      url: `/hub/${section.slug}`,
      images: [
        {
          url: "/og-default.svg",
          width: 1200,
          height: 630,
          alt: `${section.label} Open Graph Image`
        }
      ]
    }
  };
}

export default async function HubSectionPage({ params }: HubSectionPageProps) {
  const { section: rawSection } = await params;
  const section = getResourceSection(rawSection);

  if (!section) {
    notFound();
  }

  const resources = getResourcesBySection(section.slug);

  return (
    <main className={styles.hubPage}>
      <header className={styles.hero}>
        <h1 className={styles.title}>{section.label}</h1>
        <p className={styles.description}>{section.description}</p>
      </header>

      <HubNav active={section.slug as ResourceSection} />

      <ResourceList
        emptyMessage={`No ${section.label.toLowerCase()} resources yet.`}
        resources={resources}
        title={section.label}
      />
    </main>
  );
}
```

- [ ] **Step 2: Verify valid routes build**

Run:

```bash
npm run typecheck
npm run build
```

Expected: TypeScript completes with exit code 0, then Next.js builds `/hub/notes`, `/hub/skills`, and `/hub/demos` without route errors.

- [ ] **Step 3: Commit**

```bash
git add src/app/hub/[section]/page.tsx
git commit -m "Add hub section pages"
```

---

### Task 7: Add Hub To Global Navigation

**Files:**
- Modify: `src/app/layout.tsx`

- [ ] **Step 1: Update nav links**

In `src/app/layout.tsx`, replace the primary navigation block with:

```tsx
<nav aria-label="Primary navigation" className="site-nav">
  <Link href="/">Home</Link>
  <Link href="/blog">Blog</Link>
  <Link href="/hub">Hub</Link>
  <Link href="/tags">Tags</Link>
</nav>
```

- [ ] **Step 2: Verify**

Run:

```bash
npm run typecheck
npm run build
```

Expected: TypeScript completes with exit code 0, then Next.js builds successfully.

- [ ] **Step 3: Commit**

```bash
git add src/app/layout.tsx
git commit -m "Add hub to primary navigation"
```

---

### Task 8: Final Quality Gate And Manual Review

**Files:**
- Review all files changed in previous tasks.

- [ ] **Step 1: Run full quality gate**

Run:

```bash
npm run lint
npm run typecheck
npm run build
```

Expected: all three commands exit 0.

- [ ] **Step 2: Start the site locally**

Run:

```bash
npm run dev:host
```

Expected: local Next.js dev server starts and prints a localhost URL.

- [ ] **Step 3: Manual route checks**

Open the local site and verify:

```text
/hub
/hub/notes
/hub/skills
/hub/demos
```

Expected:

- `/hub` shows Featured and All Resources.
- `/hub/notes` shows only note resources.
- `/hub/skills` shows only skill resources.
- `/hub/demos` shows only demo resources.
- Search filters by title, description, tag, type, source, and date.
- External resource links open in a new tab.
- Internal note links open in the same tab.
- Top navigation includes Home, Blog, Hub, Tags.
- Hub secondary navigation includes All, Notes, Skills, Demos.

- [ ] **Step 4: Stop the dev server**

Stop the running dev server with `Ctrl+C`.

- [ ] **Step 5: Commit final adjustments if any were needed**

If manual review required edits, stage only those edits and commit:

```bash
git add content/resources.ts lib/resources.ts src/app src/components
git commit -m "Polish hub resource pages"
```

If no edits were needed, skip this commit.

---

## Self-Review

Spec coverage:

- Nested `/hub`, `/hub/notes`, `/hub/skills`, and `/hub/demos`: Task 5 and Task 6.
- Manual TypeScript manifest: Task 1.
- Shared filtering and sorting helpers: Task 2.
- Minimal list-based visual style: Task 4 and Task 5.
- Top-level navigation `Home / Blog / Hub / Tags`: Task 7.
- Hub secondary navigation `All / Notes / Skills / Demos`: Task 3.
- Static Vercel-friendly implementation with no external API dependency: all tasks avoid runtime fetching and new dependencies.
- Verification commands: Task 8.

No new dependencies are required.
