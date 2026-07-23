# Sync Post Localizations Skill

`sync-post-localizations` 用于在 Markdown 文章发生变化后，同步所有受支持语言的文章副本，并检查与文章耦合的路由、Metadata、导航、Sitemap 和 RSS/feed 行为。它安装在 Codex 的全局 Skills 目录后，可以作用于任意仓库，不绑定某个站点。

仓库地址：<https://github.com/Derekwang2002/skills>

## 何时触发

当一个仓库的 `content/posts` 或等价文章目录出现以下变化时，应使用这个 Skill：

- 新增 Markdown 文章。
- 修改现有文章内容或 Frontmatter。
- 重命名文章文件或公开 slug。
- 删除文章。
- 翻译文件缺失、过期，或与原文结构不一致。
- 用户要求同步或发布文章变更。

Skill 是由 Codex 在处理相关任务时触发的，不是后台文件监听器。仅在磁盘中写入 `.md` 文件不会自行执行；在 Codex 中提出“同步新文章”“检查文章翻译”或“发布文章变更”等请求即可触发。

## 跨仓库工作方式

Skill 以当前工作目录中的仓库为目标。它会先查找项目说明、Canonical 文章目录、翻译目录、Markdown loader、语言路由、Sitemap、RSS/feed 和部署检查，而不是硬编码 `derek-hub` 的实现。

默认识别以下常规布局：

```text
content/
├── posts/
│   └── YYYY-MM-DD-slug.md
└── translations/
    ├── en/posts/
    └── zh/posts/
```

其他布局可以通过仓库配置推断，也可以给审计脚本显式传入目录。

## 处理内容

对于每一篇发生变化的源文章，Skill 会：

1. 判断 Canonical 文章的主要语言，并修复标题或摘要的语言错配。
2. 为每个非源语言创建或更新完整翻译。
3. 保留 Markdown 结构、代码块、命令、URL、公式、锚点和技术专有名词。
4. 同步文件名与 slug，检查内部链接和语言路由。
5. 在已发布 slug 变化时保留永久重定向。
6. 验证 Sitemap、RSS/feed、Metadata、导航、排序以及 `selected`、`draft` 等展示行为。
7. 运行项目自身的 lint、typecheck、测试和生产构建。

## 审计脚本

Skill 附带一个确定性的预检查脚本：

```bash
python3 sync-post-localizations/scripts/audit_posts.py --repo /path/to/repository
```

自定义目录：

```bash
python3 sync-post-localizations/scripts/audit_posts.py \
  --repo /path/to/repository \
  --posts-dir articles \
  --translations-dir locales
```

脚本检查文件名、Frontmatter、翻译缺失和孤立翻译，并以非零退出码报告错误。它是工作流的预检查，不替代对应用路由和构建输出的验证。

## 发布边界

Skill 会保留无关的用户改动，只提交属于文章同步任务的文件。只有当用户要求完整发布流程时，才会提交并推送；翻译不完整或验证失败时不会发布。

## 源文件

- Skill 定义：`sync-post-localizations/SKILL.md`
- Codex UI 元数据：`sync-post-localizations/agents/openai.yaml`
- 文章审计脚本：`sync-post-localizations/scripts/audit_posts.py`
