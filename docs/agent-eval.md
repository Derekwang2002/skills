# Agent Eval 介绍

`agent-eval` 是一个用于评审 agent skill 和本地 git diff 的辅助 skill。它把常见的“审查变更”“评审 skill 质量”“按评审意见自动修复 skill”封装成可复用命令，适合在提交前做质量检查，或者对某个 skill 做有边界的 review/fix 循环。

仓库地址：<https://github.com/Derekwang2002/skills>

## 适用场景

当你需要做下面这些事情时，可以使用 `agent-eval`：

- 审查某个仓库当前 staged 或 unstaged 的本地变更。
- 只评审某个 skill 目录，不修改文件。
- 对某个 skill 运行 reviewer/fixer 循环，让工具在限定轮次内评审并尝试修复。

默认应优先使用只读评审命令；只有在明确希望工具修改 skill 时，才使用自动修复循环。

## 常用命令

审查仓库中的本地未提交变更：

```bash
agent-eval review-diff /path/to/repo
```

评审某个 skill，不修改文件：

```bash
agent-eval review-skill /path/to/skill
```

运行 reviewer/fixer 自动修复循环：

```bash
agent-eval fix-loop /path/to/skill --max-cycles 2
```

## 工作方式

`review-diff` 会收集 git status、staged/unstaged diff、仓库根目录的指令文件（例如 `AGENTS.md`），以及变更文本文件的有界快照。这个模式只做 review，不会调用 fixer。

`review-skill` 会把传入目录视为 skill root，并默认读取该目录下的 `SKILL.md` 进行评审。

`fix-loop` 会运行“评审 -> 修复”的循环，直到 reviewer 通过该 skill，或达到配置的最大循环轮次。

## 配置说明

可选的 `config.json` 用于控制后端命令、prompt 传递方式、上下文 include/exclude glob、超时时间、输出路径和循环轮次。

后端命令可以通过 stdin、`{prompt_file}` 或 `{prompt}` 接收 prompt。对于较大的 prompt，优先使用 stdin 或 `{prompt_file}`，避免把完整 prompt 暴露在命令参数中。

配置上下文时，应排除生成物、虚拟环境、缓存、运行输出和敏感信息。

## 源文件

- Skill 定义：`agent-eval/SKILL.md`
- 工作流说明：`agent-eval/references/workflows.md`
- 配置说明：`agent-eval/references/configuration.md`
