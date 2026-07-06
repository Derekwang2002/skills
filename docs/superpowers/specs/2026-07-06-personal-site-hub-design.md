# Personal Site Hub Design

## Goal

Build a unified entry point in the existing `Derekwang2002/vercel-site` Next.js personal site so notes, skills, and temporary HTML demos can be discovered from one place.

The site should use a mixed content model:

- Long-term notes live in the personal site repository.
- Skills stay in the `Derekwang2002/skills` repository.
- Temporary HTML demos stay where they are already published, such as GitHub Pages.
- The personal site owns the index and navigation layer.

## Current Context

The personal site is a Next.js App Router project deployed on Vercel. It already has:

- `/` home page.
- `/blog` and `/blog/[slug]` for Markdown posts.
- `/tags` and `/tags/[tag]`.
- Markdown content under `content/posts`.
- A minimal design direction documented in `ARCHITECTURE.md`.

The `skills` repository currently contains:

- `agent-eval` skill documentation.
- A GitHub Pages workflow.
- A `leetcode-cookbook` static HTML demo containing the Skip List explainer.

## Information Architecture

Use nested hub routes:

```text
/
├─ /blog          Long-term articles and blog posts
├─ /tags          Site-wide tag index
└─ /hub           All resources
   ├─ /notes      Long-term notes
   ├─ /skills     Skills index
   └─ /demos      Temporary HTML demos and visual pages
```

Top-level navigation should stay compact:

```text
Home / Blog / Hub / Tags
```

Inside `/hub`, show secondary navigation:

```text
All / Notes / Skills / Demos
```

## Resource Manifest

Use a manually maintained TypeScript manifest as the first version:

```text
content/resources.ts
```

TypeScript is preferred over JSON because it gives type checking, editor autocomplete, comments, and direct imports from Next.js pages.

The initial schema should be:

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
```

Example entries:

```ts
export const resources: Resource[] = [
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
  }
];
```

Status behavior:

- `public`: visible in hub pages and eligible for featured sections.
- `unlisted`: visible in hub lists when explicitly included, but not promoted as featured.
- `draft`: excluded from all public hub pages.

## Page Behavior

`/hub` reads the manifest and shows all non-draft resources. It should prioritize finding and scanning:

- Title and short description.
- Search box.
- Secondary navigation for All, Notes, Skills, Demos.
- Featured section for `featured: true` public resources.
- Full resource list with type, source, tags, and optional date.

`/hub/notes`, `/hub/skills`, and `/hub/demos` reuse the same list component and filter by resource type:

- `/hub/notes`: `type === "note"`.
- `/hub/skills`: `type === "skill"`.
- `/hub/demos`: `type === "demo"`.

Resource title links open the resource:

- Internal links open in the same tab.
- External links open in a new tab with `rel="noreferrer"`.

## Visual Direction

Follow the existing personal site's minimal style:

- No heavy card layout.
- No complex animation.
- Use a readable list with strong titles, short descriptions, and compact metadata.
- Keep the page useful for repeated scanning rather than making it a marketing landing page.

Resource item shape:

```text
Title
Description
type · source · tags · date
```

## Data Flow

1. Add resources to `content/resources.ts`.
2. Hub pages import helper functions that filter and sort resources.
3. `/hub` renders all non-draft resources.
4. Section pages render filtered lists by type.
5. `/tags` can later include resource tags in addition to blog tags, but that is not required for the first implementation.

## Sorting

Use a predictable first version:

1. Featured resources first on `/hub`.
2. Then resources with `date`, newest first.
3. Then resources without `date`, sorted by title.

Section pages can use the same sort without separate rules.

## Error Handling

Because the manifest is local TypeScript, most errors should be caught by type checking.

Additional safeguards:

- Exclude `draft` resources from all public pages.
- Treat empty `tags` as valid but render no tag metadata.
- Treat missing `date` as valid.
- Keep external URLs as explicit manifest values instead of deriving them at runtime.

## Testing And Verification

Every implementation change in `vercel-site` should pass:

```bash
npm run lint
npm run typecheck
npm run build
```

Manual checks:

- `/hub` shows all non-draft resources.
- `/hub/notes`, `/hub/skills`, and `/hub/demos` filter correctly.
- Featured resources appear only where expected.
- External resources open in a new tab.
- Internal note links open in the same tab.
- Empty result states are readable if a section has no entries.

## Future Extensions

Keep these out of the first implementation unless needed:

- A script to scan the `skills` repository and generate candidate manifest entries.
- Full-text search across note bodies.
- Combining blog tags and resource tags into one site-wide tag system.
- Authentication or private resources.
- Automatic GitHub API fetching at build time.

The first version should remain static, explicit, and reliable on Vercel.
